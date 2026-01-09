from datetime import datetime

from automation_hub.models import Event
from automation_hub.pipeline import steps
from automation_hub.stores.state_store import StateStore


def test_dedupe_skips_processed(tmp_path):
    store = StateStore(tmp_path / "state.db")
    event = Event(
        event_type="sms_inbound",
        source="test",
        payload={},
        occurred_at=datetime.utcnow(),
        dedupe_key="abc",
    )
    assert steps.dedupe(store, event) is not None
    assert steps.dedupe(store, event) is None
    store.close()
