"""End-to-end team run with the mock provider + config loading."""

from pathlib import Path

from airlangga.blackboard import Blackboard
from airlangga.budget import BudgetGovernor
from airlangga.config import AirlanggaConfig
from airlangga.ledger import Ledger
from airlangga.team import TeamRuntime


def _mock_config() -> AirlanggaConfig:
    cfg = AirlanggaConfig.load(Path(__file__).resolve().parent.parent / "airlangga.yaml")
    for team in cfg.teams.values():
        for member in team.members:
            member.provider = "mock"
            member.wire_format = "mock"
            member.auth_ref = "none"
            member.endpoint = None
            member.fallback = []
    return cfg


def test_example_config_loads_and_has_three_providers(tmp_path):
    cfg = AirlanggaConfig.load(Path(__file__).resolve().parent.parent / "airlangga.yaml")
    team = cfg.team("research-01")
    assert len(team.members) == 3
    assert {m.provider for m in team.members} == {"anthropic", "custom", "ollama"}
    assert team.lead_member == "researcher"


def test_full_team_run_mock(tmp_path):
    cfg = _mock_config()
    run_id = "run-test"
    ledger = Ledger(tmp_path / "ledger.db")
    board = Blackboard(tmp_path / "board.db")
    budget = BudgetGovernor()
    runtime = TeamRuntime(
        config=cfg, team_name="research-01", run_id=run_id,
        ledger=ledger, blackboard=board, budget=budget,
        workdir=str(tmp_path / "artifacts"),
    )
    reports = runtime.run_team("Produce a sourced brief on topic X.")
    assert len(reports) == 3
    assert all(r.verdict_self == "pass" for r in reports)
    state = ledger.reconstruct(run_id)
    assert all(v == "done" for v in state["contracts"].values())
    assert len(state["blackboard_committed"]) == 3
    assert state["member_states"] == {
        "researcher": "DONE", "fact_checker": "DONE", "writer": "DONE",
    }
    ledger.close()
    board.close()
