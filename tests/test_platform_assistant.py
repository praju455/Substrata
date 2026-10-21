"""Grounded assistant routing, citation validation and read-only boundaries."""

from substrata.platform.assistant import (
    AssistantRequest,
    DraftClaim,
    DraftVerdict,
    GoogleAssistantModel,
    GroqAssistantModel,
    MockAssistantModel,
    ask,
    configured_assistant_model,
)
from substrata.platform.seeds import generate


class WebFixture:
    provider = "test-web"

    def __init__(self):
        self.queries = []

    def search(self, query, *, max_results):
        self.queries.append((query, max_results))
        return [
            {
                "title": "Public disruption bulletin",
                "url": "https://example.test/disruption",
                "content": "A port disruption may delay regional component shipments.",
                "score": 0.91,
                "published_date": "2026-10-20",
            }
        ]


class HallucinatingModel:
    provider = "test-model"
    model = "unsafe-output"

    def generate(self, prompt):
        return DraftVerdict(
            verdict="likely_dependency",
            claims=[
                DraftClaim(
                    statement="Production will stop in 999 days.",
                    status="known",
                    source_ids=["invented-source"],
                )
            ],
            next_step="run_deterministic_assessment",
        )


class FailingModel:
    provider = "failed-provider"
    model = "failed-model"

    def generate(self, prompt):
        raise TimeoutError("private provider diagnostic")


def seeded(platform):
    platform.save("alpha", generate("automotive"), "test-admin", expected_version=0)
    return platform


def test_assistant_uses_graph_without_documents_or_vector_database(platform):
    seeded(platform)
    before = platform.snapshot("alpha")
    response = ask(
        platform,
        "alpha",
        AssistantRequest(
            question="Which supplier dependency could affect the automotive production plant?",
            web_search="off",
        ),
        model=MockAssistantModel(),
        search=WebFixture(),
    )
    assert response.graph_version == before.version
    assert response.sources
    assert response.retrieval["vector_database_used"] is False
    assert response.retrieval["web_attempted"] is False
    assert {claim.status for claim in response.claims} <= {"known", "inferred", "unknown"}
    assert platform.snapshot("alpha").sha256 == before.sha256


def test_current_question_uses_tavily_style_web_evidence_as_inferred(platform):
    seeded(platform)
    web = WebFixture()
    response = ask(
        platform,
        "alpha",
        AssistantRequest(
            question="What is the latest public port disruption risk for this supply chain?"
        ),
        model=MockAssistantModel(),
        search=web,
    )
    assert web.queries and web.queries[0][1] == 5
    assert response.retrieval["web_attempted"] is True
    web_sources = [source for source in response.sources if source.source_type == "public_web"]
    assert all(source.status == "inferred" for source in web_sources)
    assert all(source.uri.startswith("https://") for source in web_sources)


def test_invalid_model_citations_fail_closed(platform):
    seeded(platform)
    response = ask(
        platform,
        "alpha",
        AssistantRequest(question="What supplier risk affects the plant?", web_search="off"),
        model=HallucinatingModel(),
        search=WebFixture(),
    )
    assert response.verdict == "insufficient_evidence"
    assert response.claims[0].status == "unknown"
    assert response.claims[0].source_ids == []
    assert response.sources == []


def test_path_focus_and_provider_failure_return_no_unsupported_answer(platform):
    seeded(platform)
    relationship = platform.snapshot("alpha").data.links[0]
    response = ask(
        platform,
        "alpha",
        AssistantRequest(
            question="What evidence supports this supplier relationship?",
            focus_relationship_ids=[relationship.id],
            web_search="off",
        ),
        model=FailingModel(),
        search=WebFixture(),
    )
    assert response.verdict == "insufficient_evidence"
    assert response.claims == []
    assert "unsupported answer" in response.uncertainties[0]


def test_out_of_domain_question_does_not_call_web_or_model(platform):
    seeded(platform)

    class NeverModel(HallucinatingModel):
        def generate(self, prompt):
            raise AssertionError("Out-of-domain request reached the model")

    web = WebFixture()
    response = ask(
        platform,
        "alpha",
        AssistantRequest(question="Write a poem about the moon.", web_search="required"),
        model=NeverModel(),
        search=web,
    )
    assert response.verdict == "insufficient_evidence"
    assert response.next_step == "none"
    assert web.queries == []


def test_single_provider_modes_do_not_require_the_other_key(monkeypatch):
    monkeypatch.setenv("SUBSTRATA_ASSISTANT_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "google-test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert isinstance(configured_assistant_model(), GoogleAssistantModel)

    monkeypatch.setenv("SUBSTRATA_ASSISTANT_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(configured_assistant_model(), GroqAssistantModel)


def test_auto_mode_uses_any_available_provider(monkeypatch):
    monkeypatch.setenv("SUBSTRATA_ASSISTANT_PROVIDER", "auto")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(configured_assistant_model(), GroqAssistantModel)
