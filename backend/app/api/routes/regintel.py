from fastapi import APIRouter, HTTPException, Query, Body
import json
from datetime import datetime
from typing import List, Optional

from app.models.regintel_schemas import (
    SourceKey,
    RegulatoryAlert,
    ChangeRecord,
    ComplianceDeadline,
)
from app.services.regintel_store import (
    get_sources,
    get_alerts,
    get_changes,
    get_deadlines,
    add_deadline,
    ensure_sources_seeded,
)
from app.services.regintel_crawlers import crawl_all, get_sources as _get_sources
from app.services.regintel_ai import generate_impact


router = APIRouter()


@router.get("/health")
def health():
    return {"feature": "ok"}


@router.get("/dashboard")
def get_dashboard():
    """Return aggregated data for the dashboard."""
    alerts = get_alerts()
    changes = get_changes()
    deadlines = get_deadlines()
    sources = get_sources()
    # Simple stats: new alerts in last 7 days, pending deadlines (due in future)
    now = datetime.utcnow()
    week_ago = now.timestamp() - 7 * 24 * 60 * 60
    new_this_week = sum(
        1 for a in alerts if a.detected_at.timestamp() >= week_ago
    )
    pending_deadlines = sum(
        1 for d in deadlines if datetime.fromisoformat(d.due_date) > now
    )
    return {
        "alerts": [a.model_dump() for a in alerts],
        "changes": [c.model_dump() for c in changes],
        "deadlines": [d.model_dump() for d in deadlines],
        "sources": [s.model_dump() for s in sources],
        "stats": {"new_this_week": new_this_week, "pending_deadlines": pending_deadlines},
    }


@router.get("/sources")
def list_sources():
    return [s.model_dump() for s in get_sources()]


@router.post("/sources")
def toggle_source(source_key: str = Body(...), enabled: bool = Body(...)):
    srcs = get_sources()
    for s in srcs:
        if s.key == source_key:
            s.enabled = enabled
            # rewrite whole file
            from app.services.regintel_store import _save, _SOURCES_PATH
            _save(_SOURCES_PATH, [json.loads(item.model_dump_json()) for item in srcs])
            return {"key": source_key, "enabled": enabled}
    raise HTTPException(status_code=404, detail="Source not found")


@router.post("/crawl")
async def trigger_crawl(source_key: Optional[str] = Query(None)):
    # For simplicity, ignore source_key filtering – crawl_all respects enabled flag.
    result = await crawl_all()
    return result


@router.get("/alerts")
def get_alerts_endpoint():
    return [a.model_dump() for a in get_alerts()]


@router.get("/changes")
def get_changes_endpoint():
    return [c.model_dump() for c in get_changes()]


@router.get("/deadlines")
def get_deadlines_endpoint():
    return [d.model_dump() for d in get_deadlines()]


@router.post("/deadlines")
def create_deadline(deadline: ComplianceDeadline = Body(...)):
    add_deadline(deadline)
    return deadline.model_dump()


@router.post("/alerts/{alert_id}/impact")
def add_impact(alert_id: str, product_context: str = Body(...)):
    summary = generate_impact(alert_id, product_context)
    if not summary:
        raise HTTPException(status_code=404, detail="Alert not found or LLM failed")
    return {"alert_id": alert_id, "impact_summary": summary}

