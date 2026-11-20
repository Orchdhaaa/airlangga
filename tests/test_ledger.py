"""Ledger: append-only event log, replay, crash-resume reconstruction."""

from airlangga.ledger import Ledger


def test_append_and_replay(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    ledger.append("run-1", "plan_created", "main_brain", {"goal": "g"})
    ledger.append("run-1", "contract_created", "main_brain", {"contract_id": "c1"})
    ledger.append("run-1", "contract_completed", "m1", {"contract_id": "c1"})
    ledger.append("run-1", "cost", "m1", {"tokens": 100, "usd": 0.30, "tool_calls": 2})
    events = ledger.replay("run-1")
    assert len(events) == 4
    assert [e["type"] for e in events] == [
        "plan_created", "contract_created", "contract_completed", "cost",
    ]
    assert events[0]["seq"] < events[1]["seq"]
    ledger.close()


def test_reconstruct_after_restart(tmp_path):
    path = tmp_path / "ledger.db"
    ledger = Ledger(path)
    ledger.append("run-1", "contract_created", "main_brain", {"contract_id": "c1"})
    ledger.append("run-1", "contract_completed", "m1", {"contract_id": "c1"})
    ledger.append("run-1", "contract_created", "main_brain", {"contract_id": "c2"})
    ledger.append("run-1", "cost", "m1", {"tokens": 50, "usd": 0.10, "tool_calls": 1})
    ledger.append("run-1", "member_state", "m1", {"state": "DONE"})
    ledger.close()
    # Simulate a crash + restart: a fresh Ledger on the same file replays.
    reopened = Ledger(path)
    state = reopened.reconstruct("run-1")
    assert state["contracts"] == {"c1": "done", "c2": "open"}
    assert state["cost_by_actor"]["m1"]["tokens"] == 50
    assert state["member_states"]["m1"] == "DONE"
    reopened.close()
