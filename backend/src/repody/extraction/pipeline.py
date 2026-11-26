"""Extract one document: page images -> the model -> one value per field, or Markdown.

Everything goes to NuExtract3, all pages in one request: documents with fields in structured
mode, documents without fields in its Markdown mode.

A document with fields is read twice (AUDIT_SECOND_READ), at once: as the model gets it
(``render.model_size``) and at half those pixels. The model's misreads depend on the size of the
page it sees and repeat at that size, so two reads at different sizes rarely make the same one: a
field they disagree on is reported as unconfirmed (flagged, the run needs review) instead of
passing on a value the model may have misread.
"""

import asyncio
import collections
import contextlib
import io
import json
import math
import time
from collections.abc import AsyncIterator, Sequence
from functools import cache
from typing import Any

import openai
import structlog
from pydantic import BaseModel

from repody.extraction import client, nuextract, render
from repody.extraction.fields import FieldValue, disagreements, leaf_values, parse_answer
from repody.schemas.run import ExtractionMeta, SecondRead
from repody.schemas.workflow import DocumentDef
from repody.settings import get_settings

log = structlog.get_logger(__name__)

MAX_TEXT_CHARS = 80_000
TRUNCATED = "The model's answer was cut off at its token limit, so its fields are not used."


class ModelRequestError(Exception):
    """The model request failed; ``pages_sent`` is how many of its pages reached the server (a
    timeout or a server error: all of them, the GPU may have worked on them; a refusal or no
    connection at all: none)."""

    def __init__(self, pages_sent: int) -> None:
        super().__init__(f"The model request failed ({pages_sent} pages sent).")
        self.pages_sent = pages_sent


def _pages_reached(error: Exception, pages: int) -> int:
    if isinstance(error, openai.APIStatusError):  # the server answered: 4xx refused the request
        return 0 if error.status_code < 500 else pages
    if isinstance(error, openai.APIConnectionError) and not isinstance(
        error, openai.APITimeoutError
    ):
        return 0  # never connected
    return pages  # a timeout, or anything after the request went out


class _Answer(BaseModel):
    answer: str | None = None  # structured JSON
    markdown: str | None = None
    truncated: bool = False
    pages_rendered: int = 0
    pages_sent: int = 0
    check: str | None = None  # the second read's JSON, when it answered in full
    check_failed: bool = False  # a second read was asked and gave no usable answer


# The second read sees each page at this share of the first read's pixels (render.model_size).
SECOND_READ_AREA = 0.5


def _reads_twice(doc: DocumentDef, mime: str) -> bool:
    mode = get_settings().second_read
    return bool(doc.schema_fields) and (mode == "all" or (mode == "images" and mime != render.PDF))


def _request(doc: DocumentDef) -> dict[str, Any]:
    """The request that decides the answer, without the page images."""
    settings = get_settings()
    model, max_tokens = settings.inference_model, settings.max_output_tokens
    if doc.schema_fields:
        return nuextract.structured_request(doc, model, max_tokens=max_tokens)
    return nuextract.markdown_request(model, max_tokens=max_tokens)


# NuExtract3's image processor as it is served (Qwen2-VL's; deploy/modal/nuextract.py): one token
# per 32 x 32 pixels (16-pixel patches, merged 2 x 2), each image first scaled into
# [IMAGE_MIN_PIXELS, IMAGE_MAX_PIXELS]. Measured against vLLM's usage.prompt_tokens on staging
# (18 November): a 170 DPI A4 page is 2,778 tokens with the prompt, this count 2,728 without.
TOKEN_PIXELS = 32 * 32
IMAGE_MIN_PIXELS = 1024 * 1024
IMAGE_MAX_PIXELS = 16_777_216
CHARS_PER_TOKEN = 3  # text, counted on the high side


def request_tokens(doc: DocumentDef, page_pixels: Sequence[int]) -> int:
    """About how much of the model's context one document's request takes: its page images, its
    text (template, instructions, in-context examples) and the longest answer it may get."""
    request = _request(doc)
    images = sum(
        math.ceil(min(max(pixels, IMAGE_MIN_PIXELS), IMAGE_MAX_PIXELS) / TOKEN_PIXELS)
        for pixels in page_pixels
    )
    text = len(json.dumps([request["messages"], request["extra_body"]])) // CHARS_PER_TOKEN
    return images + text + request["max_tokens"]


def _with_pages(request: dict[str, Any], parts: list[dict[str, Any]]) -> dict[str, Any]:
    """A copy of ``request`` whose last (user) message holds the page images."""
    return {**request, "messages": [*request["messages"][:-1], {"role": "user", "content": parts}]}


# Pages rendered and waiting for the model at once in this process, all documents together. A
# page is held three times while its request is in flight (the image parts, the JSON body and
# its bytes), and a scanned A4 page at 170 DPI is up to ~5 MB as base64 PNG: four documents of
# 30 such pages measured 1.5 GB, the worker's whole memory. 40 pages stay under ~600 MB; a
# longer document waits until it can have them all.
PAGES_IN_FLIGHT = 40


class _PageBudget:
    """A semaphore counted in pages, first come first served: a long document waiting for its
    pages is not overtaken by a stream of short ones (its run's time limit is running)."""

    def __init__(self, pages: int) -> None:
        self.size = self.free = pages
        self._waiting: collections.deque[tuple[int, asyncio.Future[None]]] = collections.deque()

    def _wake(self) -> None:
        while self._waiting and self._waiting[0][0] <= self.free:
            pages, waiter = self._waiting.popleft()
            if not waiter.done():
                self.free -= pages
                waiter.set_result(None)

    @contextlib.asynccontextmanager
    async def hold(self, pages: int) -> AsyncIterator[None]:
        pages = min(max(pages, 1), self.size)
        if not self._waiting and pages <= self.free:
            self.free -= pages
        else:
            waiter = asyncio.get_running_loop().create_future()
            self._waiting.append((pages, waiter))
            try:
                await waiter
            except asyncio.CancelledError:
                if waiter.done() and not waiter.cancelled():
                    self.free += pages  # granted just as it was cancelled: give them back
                    self._wake()
                else:
                    self._waiting.remove((pages, waiter))
                    self._wake()
                raise
        try:
            yield
        finally:
            self.free += pages
            self._wake()


@cache
def _page_budget() -> _PageBudget:
    """The process's page budget (one event loop: the API's or the worker's)."""
    return _PageBudget(PAGES_IN_FLIGHT)


def _pages_to_send(data: bytes, mime: str, max_pages: int | None) -> int:
    if mime != render.PDF:
        return 1
    info = render.inspect(io.BytesIO(data))
    pages = info.pages if info else 1
    return min(pages, max_pages or pages)


async def _ask_model(doc: DocumentDef, data: bytes, mime: str, request: dict[str, Any]) -> _Answer:
    max_pages = get_settings().max_pages_per_document
    pages = await asyncio.to_thread(_pages_to_send, data, mime, max_pages)
    twice = _reads_twice(doc, mime)
    async with _page_budget().hold(pages * (2 if twice else 1)):
        return await _render_and_ask(doc, data, mime, request, max_pages, twice=twice)


async def _check_read(
    request: dict[str, Any], data: bytes, mime: str, max_pages: int | None
) -> client.Reply | None:
    """The second read's reply, or None when it failed (the first read stands, unconfirmed)."""
    parts, _ = await asyncio.to_thread(
        nuextract.page_parts, data, mime, max_pages=max_pages, area=SECOND_READ_AREA
    )
    try:
        return await client.chat(_with_pages(request, parts))
    except Exception:
        log.warning("second_read_failed", exc_info=True)
        return None


async def _render_and_ask(
    doc: DocumentDef,
    data: bytes,
    mime: str,
    request: dict[str, Any],
    max_pages: int | None,
    *,
    twice: bool = False,
) -> _Answer:
    parts, total = await asyncio.to_thread(nuextract.page_parts, data, mime, max_pages=max_pages)
    check_task = asyncio.create_task(_check_read(request, data, mime, max_pages)) if twice else None
    try:
        reply = await client.chat(_with_pages(request, parts))
    except Exception as error:
        if check_task:
            check_task.cancel()
        raise ModelRequestError(_pages_reached(error, len(parts))) from error
    except BaseException:  # cancelled (the run's time limit): the check read goes too
        if check_task:
            check_task.cancel()
        raise
    pages = {"pages_rendered": total, "pages_sent": len(parts), "truncated": reply.truncated}
    if doc.schema_fields:
        check = await check_task if check_task else None
        usable = check is not None and not check.truncated
        return _Answer(
            answer=reply.text,
            check=check.text if check is not None and usable else None,
            check_failed=twice and not usable,
            **pages,
        )
    if not reply.text:
        raise RuntimeError("The model returned no Markdown for the document.")
    return _Answer(markdown=reply.text[:MAX_TEXT_CHARS], **pages)


async def extract(
    doc: DocumentDef, data: bytes, mime: str
) -> tuple[list[FieldValue], ExtractionMeta]:
    started = time.perf_counter()
    answer = await _ask_model(doc, data, mime, _request(doc))
    elapsed = int((time.perf_counter() - started) * 1000)

    fields: list[FieldValue] = []
    error = TRUNCATED if answer.truncated else None
    if doc.schema_fields:
        # A cut-off answer can still parse as JSON (json-repair closes it), so it is not read.
        parsed, parse_error = ({}, None) if answer.truncated else parse_answer(answer.answer)
        error = error or parse_error
        fields = leaf_values(doc.schema_fields, parsed)
    second_read, unconfirmed = _compare(doc, fields, answer) if error is None else (None, {})
    meta = ExtractionMeta(
        extraction_ms=elapsed,
        fields_extracted=sum(f.extracted for f in fields),
        pages_rendered=answer.pages_rendered,
        pages_sent=answer.pages_sent,
        raw_text=answer.answer[:MAX_TEXT_CHARS] if answer.answer else None,
        markdown_text=answer.markdown,
        error=error,
        second_read=second_read,
        unconfirmed=unconfirmed,
    )
    log.info(
        "document_extracted",
        document_type=doc.document_type,
        ms=elapsed,
        fields=meta.fields_extracted,
        pages=answer.pages_sent,
        error=error,
        second_read=second_read,
        unconfirmed=len(unconfirmed),
    )
    return fields, meta


def _compare(
    doc: DocumentDef, fields: list[FieldValue], answer: _Answer
) -> tuple[SecondRead | None, dict[str, Any]]:
    """``(second_read, unconfirmed)`` for ExtractionMeta: what the second read says of the first."""
    if answer.check_failed:
        return "failed", {}
    if answer.check is None:
        return None, {}  # no second read
    checked, check_error = parse_answer(answer.check)
    if check_error:
        return "failed", {}
    unconfirmed = disagreements(fields, leaf_values(doc.schema_fields, checked))
    return ("disagreed" if unconfirmed else "agreed"), unconfirmed
