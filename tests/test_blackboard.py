"""Blackboard: propose/commit rules, search, abstracts, staleness."""

import pytest

from airlangga.blackboard import Blackboard, make_abstract


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
