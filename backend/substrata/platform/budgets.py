"""Durable daily cost reservations serialize against the organisation row."""

import math
from datetime import UTC, datetime

from sqlalchemy import select

from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Measure
from substrata.platform.models import WorkRecord
from substrata.platform.records import add, require_record


def reserve(store, actor, upper_bound_usd, purpose):
    if not math.isfinite(upper_bound_usd) or upper_bound_usd < 0:
        raise ValueError("Cost reservation must be finite and nonnegative.")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        limit = (
            Measure.model_validate(org.policy["llm_daily_budget"])
            if org.policy.get("llm_daily_budget")
            else None
        )
        if limit is None or limit.unit != "USD":
            raise ValueError("Live inference requires a sourced tenant daily budget in USD.")
        today = datetime.now(UTC).date().isoformat()
        spent = sum(
            r.payload["charged_usd"]
            for r in session.scalars(
                select(WorkRecord).where(
                    WorkRecord.tenant_id == actor.tenant_id, WorkRecord.kind == "cost"
                )
            )
            if r.payload["day"] == today
        )
        if spent + upper_bound_usd > limit.value:
            raise ValueError("Tenant daily inference cost budget is exhausted.")
        record = add(
            session,
            actor.tenant_id,
            "cost",
            "reserved",
            {
                "day": today,
                "upper_bound_usd": upper_bound_usd,
                "charged_usd": upper_bound_usd,
                "purpose": purpose,
            },
        )
        store.append(
            session,
            org,
            "cost.reserved",
            actor.subject,
            {"id": record.id, "upper_bound_usd": upper_bound_usd, "purpose": purpose},
        )
        return record.id


def settle(store, actor, reservation_id, actual_usd=None):
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        record = require_record(session, actor.tenant_id, reservation_id, "cost")
        if record.status != "reserved":
            return
        if actual_usd is not None and (not math.isfinite(actual_usd) or actual_usd < 0):
            raise ValueError("Reported inference cost must be finite and nonnegative.")
        charged = record.payload["upper_bound_usd"] if actual_usd is None else actual_usd
        record.payload = {
            **record.payload,
            "charged_usd": charged,
            "usage_known": actual_usd is not None,
        }
        record.status = "settled"
        store.append(
            session,
            org,
            "cost.settled",
            actor.subject,
            {"id": reservation_id, "charged_usd": charged, "usage_known": actual_usd is not None},
        )
