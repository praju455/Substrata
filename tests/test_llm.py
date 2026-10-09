"""Real provider contracts and failover, with every HTTP request intercepted."""

import io
import json
import urllib.error

import pytest

from substrata import llm

REQUEST = {"task": llm.PROMPT_VERSION, "schema": llm.Extraction.model_json_schema(), "evidence": []}


def gemini_response(text='{"links": []}'):
    return {
        "status": "completed",
        "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}],
    }


def groq_response(text='{"links": []}'):
    return {"choices": [{"finish_reason": "stop", "message": {"content": text}}]}


def transport(monkeypatch, responses):
    calls = []
    iterator = iter(responses)

    def urlopen(request, timeout):
        calls.append((request, timeout))
        response = next(iterator)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(json.dumps(response).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    return calls


def providers():
    return llm.PrimaryFallbackClient(
        llm.GeminiClient("gemini-test-secret"), llm.GroqClient("groq-test-secret")
    )


def test_gemini_native_request_and_primary_success(monkeypatch):
    calls = transport(monkeypatch, [gemini_response()])
    client = providers()
    assert client.generate_structured(**REQUEST) == {"links": []}
    request, timeout = calls[0]
    assert len(calls) == 1
    assert request.full_url == "https://generativelanguage.googleapis.com/v1beta/interactions"
    assert request.get_header("X-goog-api-key") == "gemini-test-secret"
    payload = json.loads(request.data)
    assert payload["model"] == llm.GEMINI_MODEL
    assert payload["response_format"]["schema"] == REQUEST["schema"]
    assert payload["store"] is False
    assert "untrusted data" in payload["system_instruction"]
    assert timeout == 20
    assert client.provider == "gemini"
    assert client.attempts[0]["status"] == "completed"


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("https://provider.invalid", 429, "secret upstream body", {}, None),
        urllib.error.URLError("secret upstream detail"),
        TimeoutError("secret upstream detail"),
        gemini_response('{"invented": true}'),
        {"status": "completed", "steps": [None]},
        {"status": "incomplete", "steps": []},
    ],
)
def test_fallback_then_returns_to_primary_next_call(monkeypatch, failure):
    calls = transport(monkeypatch, [failure, groq_response(), gemini_response()])
    client = providers()
    assert client.generate_structured(**REQUEST) == {"links": []}
    assert client.provider == "groq"
    assert [a["status"] for a in client.attempts] == ["failed", "completed"]
    request, _ = calls[1]
    assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer groq-test-secret"
    payload = json.loads(request.data)
    assert payload["model"] == llm.GROQ_MODEL
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["response_format"]["json_schema"]["schema"] == REQUEST["schema"]
    assert client.generate_structured(**REQUEST) == {"links": []}
    assert client.provider == "gemini"
    assert len(client.attempts) == 1


@pytest.mark.parametrize(
    "response",
    [
        groq_response("not JSON"),
        {"choices": []},
        {"choices": [None]},
        groq_response(None),
        {"choices": [{"finish_reason": "length", "message": {"content": '{"links": []}'}}]},
    ],
)
def test_invalid_backup_fails_closed_without_mock(monkeypatch, response):
    transport(monkeypatch, [gemini_response("not JSON"), response])
    client = providers()
    with pytest.raises(llm.ProviderError, match="Gemini and Groq") as error:
        client.generate_structured(**REQUEST)
    assert error.value.code == "all_failed"
    assert [a["status"] for a in client.attempts] == ["failed", "failed"]
    assert "test-secret" not in str(error.value)
    assert "not JSON" not in str(error.value)
    assert "test-secret" not in json.dumps(llm.client_status(client))


def test_missing_keys_make_no_requests(monkeypatch):
    calls = transport(monkeypatch, [])
    client = llm.PrimaryFallbackClient(llm.GeminiClient(""), llm.GroqClient(""))
    assert not llm.client_status(client)["primary"]["credential_configured"]
    with pytest.raises(llm.ProviderError, match="GEMINI_API_KEY and GROQ_API_KEY"):
        client.generate_structured(**REQUEST)
    assert calls == []
    assert [a["error_code"] for a in client.attempts] == ["missing_key", "missing_key"]


def test_explicit_refusal_does_not_trigger_backup(monkeypatch):
    response = {
        "status": "completed",
        "steps": [{"type": "model_output", "content": [{"type": "refusal"}]}],
    }
    calls = transport(monkeypatch, [response])
    client = providers()
    with pytest.raises(llm.ProviderError, match="declined"):
        client.generate_structured(**REQUEST)
    assert len(calls) == 1
    assert len(client.attempts) == 1


@pytest.mark.parametrize(
    "body", [b"not JSON", b"[]", b"x" * 1_048_577], ids=["invalid-json", "non-object", "oversized"]
)
def test_invalid_or_oversized_transport_body(monkeypatch, body):
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(body))
    with pytest.raises(llm.ProviderError):
        llm.GeminiClient("test").generate_structured(**REQUEST)


def test_provider_configuration(monkeypatch):
    monkeypatch.delenv("SUBSTRATA_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SUBSTRATA_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setenv("SUBSTRATA_GEMINI_MODEL", "custom-gemini")
    monkeypatch.setenv("SUBSTRATA_GROQ_MODEL", "custom-groq")
    client = llm.configured_client()
    assert isinstance(client, llm.PrimaryFallbackClient)
    assert client.primary.model == "custom-gemini"
    assert client.backup.model == "custom-groq"
    monkeypatch.setenv("SUBSTRATA_LLM_PROVIDER", "mock")
    assert isinstance(llm.configured_client(), llm.MockLLMClient)
    monkeypatch.setenv("SUBSTRATA_LLM_PROVIDER", "http")
    with pytest.raises(ValueError, match="gemini or mock"):
        llm.configured_client()


@pytest.mark.parametrize("timeout", [0, -1, 121, float("nan"), float("inf")])
def test_timeout_is_bounded(timeout):
    with pytest.raises(ValueError, match="timeout"):
        llm.GeminiClient("test", timeout=timeout)
