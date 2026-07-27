from __future__ import annotations

import json

import httpx
import pytest
import respx

from audit_workbench.inference.nuextract_cloud import (
    NuExtractCloudClient,
    NuExtractCloudConfig,
    NuExtractCloudError,
    parse_sse_string,
)


def test_parse_sse_string_result_event():
    raw = (
        "event: progress\n"
        'data: {"status":"running"}\n'
        "\n"
        "event: result\n"
        'data: {"outputData":"{\\"result\\":{\\"full_name\\":\\"ACHRAF MAHIR\\"},'
        '\\"raw_model_output\\":\\"{}\\",\\"input_tokens\\":1,\\"output_tokens\\":2,'
        '\\"total_tokens\\":3}"}\n'
        "\n"
    )
    messages = parse_sse_string(raw)
    assert messages[-1]["event"] == "result"
    payload = json.loads(messages[-1]["data"])
    assert "outputData" in payload


@pytest.mark.asyncio
@respx.mock
async def test_extract_structured_creates_temp_project_and_streams():
    base = "https://nuextract.ai"
    config = NuExtractCloudConfig(api_key="token_test", base_url=base, timeout_seconds=30)
    client = NuExtractCloudClient(config)

    create = respx.post(f"{base}/api/structured-extraction").mock(
        return_value=httpx.Response(200, json={"id": "sprj_tmp"})
    )
    job = respx.post(f"{base}/api/structured-extraction/sprj_tmp/jobs").mock(
        return_value=httpx.Response(200, json={"jobId": "job_1"})
    )
    stream_body = (
        "event: result\n"
        "data: "
        + json.dumps(
            {
                "outputData": json.dumps(
                    {
                        "result": {"full_name": "ACHRAF MAHIR"},
                        "raw_model_output": '{"full_name":"ACHRAF MAHIR"}',
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                    }
                )
            }
        )
        + "\n\n"
    )
    stream = respx.get(f"{base}/api/jobs/job_1/stream").mock(
        return_value=httpx.Response(200, text=stream_body)
    )
    delete = respx.delete(f"{base}/api/structured-extraction/sprj_tmp").mock(
        return_value=httpx.Response(200)
    )

    out = await client.extract_structured(
        template={"full_name": "string"},
        file_bytes=b"\xff\xd8\xff",
        mime_type="image/jpeg",
        instructions="",
    )

    assert out.result["full_name"] == "ACHRAF MAHIR"
    assert out.job_id == "job_1"
    assert out.project_id == "sprj_tmp"
    assert create.called
    assert job.called
    assert stream.called
    assert delete.called


@pytest.mark.asyncio
@respx.mock
async def test_extract_structured_reuses_configured_project():
    base = "https://nuextract.ai"
    config = NuExtractCloudConfig(
        api_key="token_test",
        base_url=base,
        project_id="sprj_fixed",
        timeout_seconds=30,
    )
    client = NuExtractCloudClient(config)

    patch = respx.patch(f"{base}/api/structured-extraction/sprj_fixed").mock(
        return_value=httpx.Response(200, json={"id": "sprj_fixed"})
    )
    respx.post(f"{base}/api/structured-extraction/sprj_fixed/jobs").mock(
        return_value=httpx.Response(200, json={"jobId": "job_2"})
    )
    stream_body = (
        "event: result\n"
        "data: "
        + json.dumps(
            {
                "outputData": json.dumps(
                    {
                        "result": {"x": 1},
                        "raw_model_output": "",
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                    }
                )
            }
        )
        + "\n\n"
    )
    respx.get(f"{base}/api/jobs/job_2/stream").mock(
        return_value=httpx.Response(200, text=stream_body)
    )
    delete = respx.delete(url__regex=r".*/api/structured-extraction/.*").mock(
        return_value=httpx.Response(200)
    )

    out = await client.extract_structured(
        template={"x": "number"},
        text="hello",
    )
    assert out.result == {"x": 1}
    assert patch.called
    assert not delete.called


@pytest.mark.asyncio
@respx.mock
async def test_quota_error_surfaces():
    base = "https://nuextract.ai"
    client = NuExtractCloudClient(
        NuExtractCloudConfig(api_key="token_test", base_url=base)
    )
    respx.post(f"{base}/api/structured-extraction").mock(
        return_value=httpx.Response(
            403,
            json={"code": "QuotaExceeded", "message": "Quota exceeded, please upgrade your plan"},
        )
    )
    with pytest.raises(NuExtractCloudError, match="Quota exceeded"):
        await client.create_project(template={"a": "string"})


@pytest.mark.asyncio
@respx.mock
async def test_failed_job_stream_surfaces_error_message():
    base = "https://nuextract.ai"
    client = NuExtractCloudClient(
        NuExtractCloudConfig(api_key="token_test", base_url=base, timeout_seconds=30)
    )
    respx.post(f"{base}/api/structured-extraction").mock(
        return_value=httpx.Response(200, json={"id": "sprj_tmp"})
    )
    respx.post(f"{base}/api/structured-extraction/sprj_tmp/jobs").mock(
        return_value=httpx.Response(200, json={"jobId": "job_fail"})
    )
    stream_body = (
        "event: result\n"
        "data: "
        + json.dumps(
            {
                "status": "failed",
                "errorCode": "QuotaExceeded",
                "errorMessage": "Quota exceeded, please upgrade your plan",
            }
        )
        + "\n\n"
    )
    respx.get(f"{base}/api/jobs/job_fail/stream").mock(
        return_value=httpx.Response(200, text=stream_body)
    )
    respx.delete(f"{base}/api/structured-extraction/sprj_tmp").mock(
        return_value=httpx.Response(200)
    )
    with pytest.raises(NuExtractCloudError, match="QuotaExceeded"):
        await client.extract_structured(
            template={"a": "string"},
            text="hello",
        )
