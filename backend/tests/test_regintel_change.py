import pytest
from app.services.regintel_change import detect_change
from app.services.regintel_store import get_changes

def test_detect_change_monkeypatched_ai(monkeypatch):
    # Monkeypatch LLM generate_text to return a dummy summary
    def fake_generate_text(prompt, max_tokens=None):
        return "- Change bullet 1\n- Change bullet 2"
    monkeypatch.setattr('app.services.regintel_change.generate_text', fake_generate_text)
    old = "Line one\nLine two"
    new = "Line one\nLine two modified"
    record = detect_change("http://example.com/doc", "TEST_SRC", old, new)
    assert 0 < record.similarity < 1
    assert record.summary is not None
    # Ensure persisted
    changes = get_changes()
    assert len(changes) == 1
    assert changes[0].url == "http://example.com/doc"
