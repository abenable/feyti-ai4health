"""PostgreSQL-backed regulatory intelligence store (FeatureRecord rows).

Sources, crawled documents, alerts, changes and deadlines are feature records
with scope="global" and a kind per entity; `record_key` is the entity's
natural key (source key, content hash, alert/deadline id, or a fresh uuid for
append-only change records).
"""

import json
import logging
from datetime import datetime
from typing import List
from uuid import uuid4

from app.models.regintel_schemas import (
    SourceKey,
    RegulatoryAlert,
    ChangeRecord,
    ComplianceDeadline,
)
from app.services import db_repo

logger = logging.getLogger(__name__)

_SCOPE = "global"
_KIND_SOURCE = "regintel_source"
_KIND_DOCUMENT = "regintel_document"
_KIND_ALERT = "regintel_alert"
_KIND_CHANGE = "regintel_change"
_KIND_DEADLINE = "regintel_deadline"


def _rows(kind: str) -> List[dict]:
    return [dict(row.data or {}) for row in db_repo.feature_list(_SCOPE, kind)]


# ---------- Sources ----------

def get_sources() -> List[SourceKey]:
    return [SourceKey(**item) for item in _rows(_KIND_SOURCE)]


def touch_source(source_key: str) -> None:
    """Record the last successful crawl time for one configured source."""
    for row in db_repo.feature_list(_SCOPE, _KIND_SOURCE):
        data = dict(row.data or {})
        if data.get("key") == source_key:
            data["last_crawled"] = datetime.utcnow()
            db_repo.feature_put(_SCOPE, _KIND_SOURCE, row.record_key,
                                json.loads(SourceKey(**data).model_dump_json()))
            break


def _seed_sources() -> None:
    # Minimal placeholder seed for East‑African authorities.
    placeholder_sources = [
        {
            "key": "NDA_UG",
            "country": "Uganda",
            "authority": "NDA Uganda",
            "listing_urls": [
                "https://www.nda.or.ug/category/alerts/",
                "https://www.nda.or.ug/category/news/",
                "https://www.nda.or.ug/circulars-2/",
            ],
            "enabled": True,
        },
        {
            "key": "TFDA_TZ",
            "country": "Tanzania",
            "authority": "TFDA Tanzania",
            "listing_urls": [
                "https://www.tmda.go.tz/registration",
                "https://www.tmda.go.tz/fees",
                "https://www.tmda.go.tz/",
            ],
            "enabled": True,
        },
        {
            "key": "PPB_KE",
            "country": "Kenya",
            "authority": "PPB Kenya",
            "listing_urls": [
                "https://www.ppb.go.ke/index.php/product-registration",
                "https://www.ppb.go.ke/index.php/fees-charges",
            ],
            "enabled": True,
        },
        {
            "key": "NAFDAC_NG",
            "country": "Nigeria",
            "authority": "NAFDAC Nigeria",
            "listing_urls": [
                "https://www.nafdac.gov.ng/product-registration/",
                "https://www.nafdac.gov.ng/fee-schedule/",
            ],
            "enabled": True,
        },
        {
            "key": "Rwanda_FDA",
            "country": "Rwanda",
            "authority": "Rwanda FDA",
            "listing_urls": [
                "https://www.rfa.gov.rw/product-registration",
                "https://www.rwandafda.gov.rw",
            ],
            "enabled": True,
        },
    ]
    for source in placeholder_sources:
        db_repo.feature_put(_SCOPE, _KIND_SOURCE, source["key"], source)


def ensure_sources_seeded() -> None:
    if not db_repo.feature_exists(_SCOPE, _KIND_SOURCE):
        _seed_sources()

# ---------- Documents ----------

def get_documents() -> List[dict]:
    return _rows(_KIND_DOCUMENT)


def add_or_update_document(doc: dict) -> None:  # Updated to merge fields on duplicate hash
    """Add a new document or update timestamps if content_hash already exists.
    Expected keys: source_key, url, title, content_hash, doc_type, first_seen, last_seen.
    """
    now_iso = datetime.utcnow().isoformat()
    for row in db_repo.feature_list(_SCOPE, _KIND_DOCUMENT):
        if (row.data or {}).get("content_hash") == doc.get("content_hash"):
            # Update fields and timestamps
            data = dict(row.data)
            data.update(doc)
            data["last_seen"] = now_iso
            # Preserve original first_seen if present, else set now
            data.setdefault("first_seen", now_iso)
            db_repo.feature_put(_SCOPE, _KIND_DOCUMENT, row.record_key, data)
            return
    # New document
    doc.setdefault("first_seen", now_iso)
    doc.setdefault("last_seen", now_iso)
    db_repo.feature_put(_SCOPE, _KIND_DOCUMENT, doc["content_hash"], doc)

# ---------- Alerts ----------

def get_alerts() -> List[RegulatoryAlert]:
    return [RegulatoryAlert(**item) for item in _rows(_KIND_ALERT)]


def add_alert(alert: RegulatoryAlert) -> None:
    db_repo.feature_put(_SCOPE, _KIND_ALERT, alert.alert_id,
                        json.loads(alert.model_dump_json()))

# ---------- Changes ----------

def get_changes() -> List[ChangeRecord]:
    return [ChangeRecord(**item) for item in _rows(_KIND_CHANGE)]


def add_change(change: ChangeRecord) -> None:
    db_repo.feature_put(_SCOPE, _KIND_CHANGE, uuid4().hex,
                        json.loads(change.model_dump_json()))

# ---------- Deadlines ----------

def get_deadlines() -> List[ComplianceDeadline]:
    return [ComplianceDeadline(**item) for item in _rows(_KIND_DEADLINE)]


def add_deadline(deadline: ComplianceDeadline) -> None:
    db_repo.feature_put(_SCOPE, _KIND_DEADLINE, deadline.deadline_id,
                        json.loads(deadline.model_dump_json()))

# Ensure sources are seeded on import (degrades gracefully without a DB).
try:
    ensure_sources_seeded()
except Exception as exc:  # pragma: no cover - DB-less import (e.g. tooling)
    logger.warning("Regintel sources not seeded (DB unavailable): %s", exc)
