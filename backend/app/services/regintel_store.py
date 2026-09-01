import json
from datetime import datetime
from pathlib import Path
from typing import List

from app.services.store_utils import safe_join, read_json, write_json
from app.models.regintel_schemas import (
    SourceKey,
    RegulatoryAlert,
    ChangeRecord,
    ComplianceDeadline,
)

# Base directory for global regintel store
_REGINTEL_ROOT = Path(__file__).resolve().parents[3] / "regintel"

# Ensure directory exists
_REGINTEL_ROOT.mkdir(parents=True, exist_ok=True)

# File paths
_SOURCES_PATH = safe_join(_REGINTEL_ROOT, "sources.json")
_DOCUMENTS_PATH = safe_join(_REGINTEL_ROOT, "documents.json")
_ALERTS_PATH = safe_join(_REGINTEL_ROOT, "alerts.json")
_CHANGES_PATH = safe_join(_REGINTEL_ROOT, "changes.json")
_DEADLINES_PATH = safe_join(_REGINTEL_ROOT, "deadlines.json")


def _load(path: Path):
    data = read_json(path)
    return data if isinstance(data, list) else []


def _save(path: Path, data: List[dict]):
    write_json(path, data)

# ---------- Sources ----------

def get_sources() -> List[SourceKey]:
    raw = _load(_SOURCES_PATH)
    return [SourceKey(**item) for item in raw]


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
    _save(_SOURCES_PATH, placeholder_sources)


def ensure_sources_seeded() -> None:
    if not _SOURCES_PATH.is_file():
        _seed_sources()

# ---------- Documents ----------

def get_documents() -> List[dict]:
    return _load(_DOCUMENTS_PATH)


def add_or_update_document(doc: dict) -> None:  # Updated to merge fields on duplicate hash
    """Add a new document or update timestamps if content_hash already exists.
    Expected keys: source_key, url, title, content_hash, doc_type, first_seen, last_seen.
    """
    docs = _load(_DOCUMENTS_PATH)
    now_iso = datetime.utcnow().isoformat()
    for existing in docs:
        if existing.get("content_hash") == doc.get("content_hash"):
            # Update fields and timestamps
            existing.update(doc)
            existing["last_seen"] = now_iso
            # Preserve original first_seen if present, else set now
            existing.setdefault("first_seen", now_iso)
            _save(_DOCUMENTS_PATH, docs)
            return
    # New document
    doc.setdefault("first_seen", now_iso)
    doc.setdefault("last_seen", now_iso)
    docs.append(doc)
    _save(_DOCUMENTS_PATH, docs)

# ---------- Alerts ----------

def get_alerts() -> List[RegulatoryAlert]:
    raw = _load(_ALERTS_PATH)
    return [RegulatoryAlert(**item) for item in raw]


def add_alert(alert: RegulatoryAlert) -> None:
    alerts = _load(_ALERTS_PATH)
    alerts.append(json.loads(alert.model_dump_json()))
    _save(_ALERTS_PATH, alerts)

# ---------- Changes ----------

def get_changes() -> List[ChangeRecord]:
    raw = _load(_CHANGES_PATH)
    return [ChangeRecord(**item) for item in raw]


def add_change(change: ChangeRecord) -> None:
    changes = _load(_CHANGES_PATH)
    changes.append(json.loads(change.model_dump_json()))
    _save(_CHANGES_PATH, changes)

# ---------- Deadlines ----------

def get_deadlines() -> List[ComplianceDeadline]:
    raw = _load(_DEADLINES_PATH)
    return [ComplianceDeadline(**item) for item in raw]


def add_deadline(deadline: ComplianceDeadline) -> None:
    deadlines = _load(_DEADLINES_PATH)
    deadlines.append(json.loads(deadline.model_dump_json()))
    _save(_DEADLINES_PATH, deadlines)

# Ensure sources are seeded on import
ensure_sources_seeded()
