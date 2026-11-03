from __future__ import annotations

from repody.settings import Settings


def test_llamacpp_base_url():
    settings = Settings(llamacpp_base_url="http://127.0.0.1:8081/v1")
    from repody.inference.runtime import llamacpp_base_url

    assert llamacpp_base_url(settings) == "http://127.0.0.1:8081/v1"


def test_top_k_is_sent_as_openai_extra_body():
    from repody.inference.openai_compat import split_chat_payload

    standard, extra = split_chat_payload(
        {
            "model": "nuextract",
            "messages": [],
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 40,
            "chat_template_kwargs": {"enable_thinking": True},
        }
    )

    assert standard == {
        "model": "nuextract",
        "messages": [],
        "temperature": 0.6,
        "top_p": 0.95,
    }
    assert extra == {
        "top_k": 40,
        "chat_template_kwargs": {"enable_thinking": True},
    }
