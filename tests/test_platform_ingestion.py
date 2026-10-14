"""Tabular upload, drift, idempotency, tenant boundaries and safe rollback."""

import base64
import io

import pytest
from openpyxl import Workbook
from test_platform_store import graph, source

from substrata.platform.ingestion import (
    TabularImport,
    apply_import,
    parse_table,
    resolve_import,
    rollback,
    stage,
)
from substrata.platform.store import Conflict


def upload(content="ID,Name,Type\nsupplier,Example,Supplier\n", version=0):
    return TabularImport(
        filename="vendors.csv",
        content_base64=base64.b64encode(content.encode()).decode(),
        target="entities",
        mapping={"id": "ID", "name": "Name", "kind": "Type"},
        expected_version=version,
        provenance=source(),
    )


def test_import_is_idempotent_atomic_and_rollback_retains_history(platform):
    body = upload()
    staged = stage(platform, "alpha", body, "analyst")
    assert staged["status"] == "staged"
    assert stage(platform, "alpha", body, "analyst")["id"] == staged["id"]
    applied = apply_import(platform, "alpha", staged["id"], "analyst")
    assert applied["status"] == "applied"
    assert (
        apply_import(platform, "alpha", staged["id"], "analyst")["payload"]["applied_version"] == 1
    )
    assert platform.snapshot("alpha").version == 1
    with pytest.raises(ValueError):
        apply_import(platform, "beta", staged["id"], "analyst")
    rollback(platform, "alpha", staged["id"], "admin", "Incorrect source")
    assert platform.snapshot("alpha").data.entities == []
    assert platform.snapshot("alpha", version=1).data.entities[0].id == "supplier"
    assert platform.audit("alpha")["verification"]["valid"]


def test_invalid_rows_cannot_apply_and_schema_drift_needs_remapping(platform):
    body = upload("ID,Name,Type\nsupplier,Example,Unknown\n")
    invalid = stage(platform, "alpha", body, "analyst")
    assert invalid["status"] == "invalid"
    assert invalid["payload"]["errors"][0]["row"] == 2
    with pytest.raises(Conflict):
        apply_import(platform, "alpha", invalid["id"], "analyst")
    with pytest.raises(Conflict, match="drift"):
        stage(platform, "alpha", upload().model_copy(update={"schema_sha256": "wrong"}), "analyst")


def test_ambiguous_entity_is_reviewed_instead_of_implicitly_merged(platform):
    platform.save("alpha", graph("Acme Pharma"), "analyst", expected_version=0)
    body = upload("ID,Name,Type\nnew,ACME PHARMA,Supplier\n", version=1)
    staged = stage(platform, "alpha", body, "analyst")
    assert staged["status"] == "needs_review"
    with pytest.raises(Conflict):
        apply_import(platform, "alpha", staged["id"], "analyst")
    resolve_import(
        platform, "alpha", staged["id"], {"new": "supplier"}, "analyst", "Same verified supplier"
    )
    apply_import(platform, "alpha", staged["id"], "analyst")
    assert [e.id for e in platform.snapshot("alpha").data.entities] == ["supplier"]


def test_semantic_entity_resolution_adds_candidates_without_auto_merging(platform):
    platform.save("alpha", graph("Acme Pharma"), "analyst", expected_version=0)

    class Embedder:
        model = "test-semantic"

        def embed(self, texts):
            return [[1.0, 0.0] for _ in texts]

    body = upload("ID,Name,Type\nnew,Acme Pharma Holdings,Supplier\n", version=1)
    staged = stage(platform, "alpha", body, "analyst", embedder=Embedder())
    assert staged["status"] == "needs_review"
    candidate = staged["payload"]["reviews"][0]["candidates"][0]
    assert candidate["id"] == "supplier"
    assert candidate["embedding_score"] == 1.0
    assert candidate["name_rule_score"] < 0.8
    assert {e.id for e in platform.snapshot("alpha").data.entities} == {"supplier"}
    assert "new" in {e["id"] for e in staged["payload"]["candidate"]["entities"]}


def test_entity_resolution_rechecks_graph_version_after_embedding(platform):
    platform.save("alpha", graph("Acme Pharma"), "analyst", expected_version=0)

    class UpdatingEmbedder:
        model = "test-semantic"

        def embed(self, texts):
            platform.save("alpha", graph("Changed while resolving"), "analyst", expected_version=1)
            return [[1.0, 0.0] for _ in texts]

    body = upload("ID,Name,Type\nnew,Acme Pharma Holdings,Supplier\n", version=1)
    with pytest.raises(Conflict, match="during entity resolution"):
        stage(platform, "alpha", body, "analyst", embedder=UpdatingEmbedder())


def test_rollback_does_not_erase_later_work(platform):
    staged = stage(platform, "alpha", upload(), "analyst")
    apply_import(platform, "alpha", staged["id"], "analyst")
    platform.save("alpha", graph("Later update"), "analyst", expected_version=1)
    with pytest.raises(Conflict, match="later"):
        rollback(platform, "alpha", staged["id"], "admin", "Requested rollback")


def test_xlsx_preview_and_duplicate_headers():
    book = Workbook()
    book.active.append(["ID", "Name", "Type"])
    book.active.append(["s", "Example", "Supplier"])
    buffer = io.BytesIO()
    book.save(buffer)
    columns, rows = parse_table("vendors.xlsx", buffer.getvalue())
    assert columns == ["ID", "Name", "Type"]
    assert rows[0]["ID"] == "s"
    with pytest.raises(ValueError, match="unique"):
        parse_table("bad.csv", b"ID,ID\nfirst,second")


def test_conflicting_duplicate_ids_and_stale_stage(platform):
    staged = stage(
        platform, "alpha", upload("ID,Name,Type\ns,First,Supplier\ns,Second,Supplier"), "analyst"
    )
    assert staged["status"] == "invalid"
    platform.save("alpha", graph(), "analyst", expected_version=0)
    with pytest.raises(Conflict, match="changed"):
        stage(platform, "alpha", upload(), "analyst")
