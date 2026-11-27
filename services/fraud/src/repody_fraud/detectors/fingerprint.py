"""Perceptual image/page fingerprinting (64-bit pHash & dHash for pgvector BIT(64))."""

import imagehash
from PIL import Image

from repody_fraud.detectors.render import render_pages_rgb
from repody_fraud.schemas.analyses import PageFingerprint


def _hash_to_bitstring(value: imagehash.ImageHash) -> str:
    bits = value.hash.flatten()
    bitstring = "".join("1" if bool(bit) else "0" for bit in bits)
    return bitstring.ljust(64, "0")[:64]


def hamming_distance(bits_a: str, bits_b: str) -> int:
    """Compute bitwise Hamming distance between equal-length ``0``/``1`` bitstrings."""
    if len(bits_a) != len(bits_b):
        raise ValueError("Bitstrings must have equal length.")
    return sum(a != b for a, b in zip(bits_a, bits_b, strict=True))


def compute_document_fingerprints(
    data: bytes,
    mime_type: str,
    *,
    max_pages: int = 10,
) -> list[PageFingerprint]:
    """Render document pages and compute 64-bit pHash and dHash bitstrings."""
    pages = render_pages_rgb(data, mime_type, max_pages=max_pages, dpi=100)
    results: list[PageFingerprint] = []
    for page_num, rgb in enumerate(pages, start=1):
        img = Image.fromarray(rgb)
        results.append(
            PageFingerprint(
                page=page_num,
                phash_bits=_hash_to_bitstring(imagehash.phash(img)),
                dhash_bits=_hash_to_bitstring(imagehash.dhash(img)),
            )
        )
    return results
