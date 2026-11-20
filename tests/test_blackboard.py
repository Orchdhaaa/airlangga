"""Blackboard: propose/commit rules, search, abstracts, staleness."""

import pytest

from airlangga.blackboard import Blackboard, entry_to_report, make_abstract


def test_member_may_propose_but_not_commit(tmp_path):
    board = Blackboard(tmp_path / "board.db")
    entry_id = board.propose("r1", "t1", "fact", "Title", "Body text", author="m1")
    entry = board.get(entry_id)
    assert entry["status"] == "proposed"
    with pytest.raises(PermissionError):
        board.commit(entry_id, by_role="member")
    board.commit(entry_id, by_role="lead")
    assert board.get(entry_id)["status"] == "committed"
    board.close()


def test_team_brain_may_commit(tmp_path):
    board = Blackboard(tmp_path / "board.db")
    entry_id = board.propose("r1", "t1", "decision", "D", "body", author="m1")
    board.commit(entry_id, by_role="team_brain")
    assert board.get(entry_id)["status"] == "committed"
    board.close()


def test_search_and_abstract(tmp_path):
    board = Blackboard(tmp_path / "board.db")
    long_body = "word " * 500
    entry_id = board.propose("r1", "t1", "fact", "Airlangga history", long_body, author="m1")
    entry = board.get(entry_id)
    assert len(entry["abstract"]) <= 610  # ~150 tokens
    assert make_abstract("short") == "short"
    results = board.search("r1", "t1", "Airlangga")
    assert any(r["id"] == entry_id for r in results)
    board.close()


def test_stale_on_expiry(tmp_path):
    board = Blackboard(tmp_path / "board.db")
    entry_id = board.propose(
        "r1", "t1", "fact", "Old", "body", author="m1",
        valid_until="2020-01-01T00:00:00+00:00",
    )
    assert board.is_stale(board.get(entry_id)) is True
    entry2 = board.propose("r1", "t1", "fact", "New", "body", author="m1")
    assert board.is_stale(board.get(entry2)) is False
    board.close()


def test_list_for_run_and_count_by_run(tmp_path):
    board = Blackboard(tmp_path / "board.db")
    a = board.propose("r1", "t1", "fact", "A", "body a", author="m1")
    board.commit(a, by_role="lead")
    b = board.propose("r1", "t2", "fact", "B", "body b", author="m2")
    board.propose("r2", "t1", "fact", "C", "body c", author="m1")
    assert [e["id"] for e in board.list_for_run("r1")] == [a, b]
    assert [e["id"] for e in board.list_for_run("r1", status="committed")] == [a]
    assert board.list_for_run("rX") == []
    assert board.count_by_run() == {"r1": 2, "r2": 1}
    board.close()


def test_entry_to_report_handles_report_json_and_fallbacks(tmp_path):
    import json

    board = Blackboard(tmp_path / "board.db")
    report_body = json.dumps({
        "contract_id": "contract-1",
        "member_id": "researcher",
        "claims": [
            {"claim": "Kahuripan was founded in 1019.", "evidence_refs": ["artifact://doc1"], "confidence": 0.9},
        ],
        "diff": "artifact://patch1",
        "open_questions": ["Verify inscription date"],
        "cost": {"tokens": 120.0, "usd": 0.001, "tool_calls": 0.0},
        "verdict_self": "pass",
    })
    e1 = board.propose("r1", "t1", "fact", "Report 1", report_body, author="researcher")
    board.commit(e1, by_role="lead")
    rep1 = entry_to_report(board.get(e1))
    assert rep1["member_id"] == "researcher"
    assert rep1["contract_id"] == "contract-1"
    assert rep1["verdict"] == "pass"
    assert rep1["diff"] == "artifact://patch1"
    assert rep1["open_questions"] == ["Verify inscription date"]
    assert rep1["claims"] == [
        {"claim": "Kahuripan was founded in 1019.", "evidence_refs": ["artifact://doc1"], "confidence": 0.9}
    ]

    # Non-JSON entry with evidence falls back to evidence list.
    e2 = board.propose("r1", "t1", "fact", "Legacy", "not json", author="writer", evidence=["Fallback claim"], confidence=0.7)
    rep2 = entry_to_report(board.get(e2))
    assert rep2["claims"] == [{"claim": "Fallback claim", "evidence_refs": [], "confidence": 0.7}]

    # Non-JSON entry with no evidence falls back to plain-text body.
    e3 = board.propose("r1", "t1", "fact", "Plain", "Plain text answer", author="critic", confidence=0.6)
    rep3 = entry_to_report(board.get(e3))
    assert rep3["claims"] == [{"claim": "Plain text answer", "evidence_refs": [], "confidence": 0.6}]
    board.close()
