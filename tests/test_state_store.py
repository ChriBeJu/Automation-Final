from automation_hub.stores.state_store import StateStore


def test_state_store_persistence(tmp_path):
    path = tmp_path / "state.db"
    store = StateStore(path)
    store.set("cursor", {"last_id": 10})
    store.close()

    store = StateStore(path)
    assert store.get("cursor") == {"last_id": 10}
    store.close()
