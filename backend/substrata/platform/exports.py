"""Tenant exports with explicit provenance and spreadsheet-formula escaping."""

import csv
import io


def safe_cell(value):
    text = str(value if value is not None else "")
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def graph_csv(snapshot):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "version",
            "recorded_at",
            "id",
            "source",
            "target",
            "type",
            "status",
            "confidence",
            "source_kind",
            "source_uri",
            "evidence_documents",
        ]
    )
    for link in snapshot.data.links:
        writer.writerow(
            [
                safe_cell(v)
                for v in [
                    snapshot.version,
                    snapshot.recorded_at.isoformat(),
                    link.id,
                    link.source,
                    link.target,
                    link.type,
                    link.status,
                    link.confidence,
                    link.provenance.kind,
                    link.provenance.uri,
                    ";".join(c.document_id for c in link.evidence),
                ]
            ]
        )
    return buffer.getvalue()
