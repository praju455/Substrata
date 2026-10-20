"""Tabular upload, drift, idempotency, tenant boundaries and safe rollback."""

import base64
import io

import pytest
from openpyxl import Workbook
from test_platform_store import graph, source

from substrata.platform.domain import Entity, GraphData, Measure
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


def test_entity_mapping_carries_identifiers_revenue_and_independent_units(platform):
    content = (
        "ID,Name,Type,DUNS,TaxID,Revenue,RequalDays\n"
        "product,Control Unit,Product,123456789,IN-TAX-7,50000,90\n"
    )
    body = upload(content).model_copy(
        update={
            "mapping": {
                "id": "ID",
                "name": "Name",
                "kind": "Type",
                "identifiers.duns": "DUNS",
                "identifiers.tax_id": "TaxID",
                "measures.daily_revenue": "Revenue",
                "measures.requalification_days": "RequalDays",
            },
            "units": {
                "measures.daily_revenue": "USD/day",
                "measures.requalification_days": "day",
            },
        }
    )
    staged = stage(platform, "alpha", body, "analyst")
    assert staged["status"] == "staged"
    apply_import(platform, "alpha", staged["id"], "analyst")
    entity = platform.snapshot("alpha").data.entities[0]
    assert entity.identifiers == {"duns": "123456789", "tax_id": "IN-TAX-7"}
    assert entity.measures["daily_revenue"].unit == "USD/day"
    assert entity.measures["daily_revenue"].value == 50000
    assert entity.measures["requalification_days"].unit == "day"


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


@pytest.mark.parametrize("incoming_id", ["supplier", "alias"])
def test_entity_updates_preserve_unmapped_facts_and_replace_supplied_facts(platform, incoming_id):
    original_source = source().model_copy(update={"uri": "synthetic://original"})
    original = GraphData(
        entities=[
            Entity(
                id="supplier",
                name="Acme Pharma",
                kind="Supplier",
                identifiers={"vat": "GB-original", "erp": "old"},
                attributes={"country": "UK", "currency": "GBP"},
                measures={
                    "lead_days": Measure(value=12, unit="day", provenance=original_source),
                    "requalification_days": Measure(
                        value=30, unit="day", provenance=original_source
                    ),
                },
                provenance=original_source,
            )
        ]
    )
    first = platform.save("alpha", original, "analyst", expected_version=0)
    body = upload(
        f"ID,Name,Type,Country,LeadDays,ERP\n{incoming_id},ACME PHARMA,Supplier,DE,20,new\n",
        version=1,
    ).model_copy(
        update={
            "mapping": {
                "id": "ID",
                "name": "Name",
                "kind": "Type",
                "attributes.country": "Country",
                "measures.lead_days": "LeadDays",
                "identifiers.erp": "ERP",
            },
            "units": {"measures.lead_days": "day"},
        }
    )
    staged = stage(platform, "alpha", body, "analyst")
    if incoming_id == "alias":
        assert staged["status"] == "needs_review"
        resolve_import(
            platform, "alpha", staged["id"], {"alias": "supplier"}, "analyst", "Verified alias"
        )
    else:
        assert staged["status"] == "staged"
    apply_import(platform, "alpha", staged["id"], "analyst")
    supplier = platform.snapshot("alpha").data.entities[0]
    assert supplier.id == "supplier"
    assert supplier.name == "ACME PHARMA"
    assert supplier.identifiers == {"vat": "GB-original", "erp": "new"}
    assert supplier.attributes == {"country": "DE", "currency": "GBP"}
    assert supplier.measures["lead_days"].value == 20
    assert supplier.measures["lead_days"].provenance == body.provenance
    assert (
        supplier.measures["requalification_days"]
        == original.entities[0].measures["requalification_days"]
    )
    assert platform.snapshot("alpha", version=first.version).sha256 == first.sha256
    assert platform.audit("alpha")["verification"]["valid"]


def test_new_upload_aliases_need_review_and_chained_matches_have_a_stable_survivor(platform):
    rows = ["c,Acme Pharma,Supplier", "b,ACME PHARMA,Supplier", "a,Acme Pharma,Supplier"]
    body = upload("ID,Name,Type\n" + "\n".join(rows))
    staged = stage(platform, "alpha", body, "analyst")
    reordered = stage(
        platform,
        "beta",
        upload("ID,Name,Type\n" + "\n".join(reversed(rows))).model_copy(
            update={"provenance": body.provenance}
        ),
        "analyst",
    )
    assert staged["status"] == reordered["status"] == "needs_review"
    assert staged["payload"]["reviews"] == reordered["payload"]["reviews"]
    assert [review["incoming_id"] for review in staged["payload"]["reviews"]] == ["b", "c"]
    assert {item["id"] for item in staged["payload"]["reviews"][0]["candidates"]} == {"a"}
    with pytest.raises(Conflict, match="reviewed"):
        apply_import(platform, "alpha", staged["id"], "analyst")
    with pytest.raises(ValueError, match="reviewed candidate"):
        resolve_import(
            platform, "alpha", staged["id"], {"b": "c", "c": None}, "analyst", "Invalid target"
        )
    # The decisions deliberately refer to an alias that is itself being merged.
    resolve_import(
        platform, "alpha", staged["id"], {"c": "b", "b": "a"}, "analyst", "Same supplier"
    )
    apply_import(platform, "alpha", staged["id"], "analyst")
    assert [entity.id for entity in platform.snapshot("alpha").data.entities] == ["a"]
    resolve_import(
        platform,
        "beta",
        reordered["id"],
        {"b": None, "c": "b"},
        "analyst",
        "Source identifiers distinguish the first supplier",
    )
    apply_import(platform, "beta", reordered["id"], "analyst")
    assert {entity.id for entity in platform.snapshot("beta").data.entities} == {"a", "b"}
    assert platform.audit("alpha")["verification"]["valid"]
    assert platform.audit("beta")["verification"]["valid"]


def test_identical_duplicate_rows_do_not_create_an_identity_review(platform):
    staged = stage(
        platform,
        "alpha",
        upload("ID,Name,Type\na,Acme Pharma,Supplier\na,Acme Pharma,Supplier\n"),
        "analyst",
    )
    assert staged["status"] == "staged"
    assert staged["payload"]["reviews"] == []
    assert staged["payload"]["deduped_count"] == 1


@pytest.mark.parametrize(
    "mapping",
    [
        {"name": "Name", "name.foo.bar": "ID"},
        {"name.foo.bar": "ID", "name": "Name"},
        {"measures.lead_days.value": "ID", "measures.lead_days": "Name"},
    ],
)
def test_overlapping_mapping_paths_fail_cleanly_before_creating_an_import(platform, mapping):
    before = platform.audit("alpha")["verification"]["head"]
    body = upload().model_copy(update={"mapping": mapping})
    with pytest.raises(ValueError, match="Mapping paths must not overlap"):
        stage(platform, "alpha", body, "analyst")
    assert platform.audit("alpha")["verification"]["head"] == before
    with pytest.raises(ValueError, match="No graph"):
        platform.snapshot("alpha")
