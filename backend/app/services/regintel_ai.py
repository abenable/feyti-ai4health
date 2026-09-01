from datetime import datetime
import json
from typing import Optional

from app.models.regintel_schemas import RegulatoryAlert
from app.services.llm import generate_text
from app.services.regintel_store import get_alerts, add_alert


def generate_impact(alert_id: str, product_context: str) -> Optional[str]:
    """Generate an impact summary for a given alert and store it.
    Returns the generated summary or None if generation fails.
    """
    alerts = get_alerts()
    alert = next((a for a in alerts if a.alert_id == alert_id), None)
    if not alert:
        return None
    if alert.impact_summary:
        return alert.impact_summary
    prompt = (
        f"You are a regulatory analyst. Summarise the compliance impact of the following regulatory document for the product context: {product_context}.\n\n"
        f"Title: {alert.title}\n"
        f"URL: {alert.url}\n"
        f"Document type: {alert.doc_type}\n"
    )
    try:
        summary = generate_text(prompt, max_tokens=500)
        if summary:
            # Update alert in store
            alert.impact_summary = summary.strip()
            # replace in store (simple rewrite whole list)
            _replace_alert(alert)
            return alert.impact_summary
    except Exception:
        return None
    return None


def _replace_alert(updated_alert: RegulatoryAlert) -> None:
    """Replace the alert with matching alert_id in the JSON store."""
    alerts = get_alerts()
    new_list = []
    for a in alerts:
        if a.alert_id == updated_alert.alert_id:
            new_list.append(updated_alert)
        else:
            new_list.append(a)
    # Direct write using store utils
    from app.services.regintel_store import _save, _ALERTS_PATH

    _save(_ALERTS_PATH, [json.loads(a.model_dump_json()) for a in new_list])
