"""CLI: demo/run/trace print the team's actual output, not just claim counts."""

import json
import yaml
from click.testing import CliRunner

from airlangga.blackboard import Blackboard
from airlangga.cli import cli
from airlangga.ledger import Ledger


def test_demo_and_trace_print_claim_text(tmp_path):
    run_dir = tmp_path / "runs"
    runner = CliRunner()
    result = runner.invoke(cli, ["demo", "--run-dir", str(run_dir)])
    assert result.exit_code == 0, result.output
    # P0 regression: the claim text itself must be printed, not only
    # "claims=1" — otherwise the user can never see what the team said.
    assert "Mock researcher completed its assigned work" in result.output
    assert "Mock critic completed" in result.output
    assert "Mock writer completed" in result.output

    # Extract run_id and verify `airlangga trace` also displays the outputs
    # from the sibling blackboard.db.
    run_line = next(l for l in result.output.splitlines() if l.startswith("Run run-"))
    run_id = run_line.split()[1].rstrip(":")
    trace_res = runner.invoke(
        cli, ["trace", "--ledger", str(run_dir / "ledger.db"), "--run-id", run_id]
    )
    assert trace_res.exit_code == 0, trace_res.output
    assert "Outputs:" in trace_res.output
    assert "Mock researcher completed its assigned work" in trace_res.output
    assert "Mock critic completed" in trace_res.output
    assert "Mock writer completed" in trace_res.output


def test_run_on_scratch_team_prints_claim_text(tmp_path):
    cfg = {
        "version": 1,
        "main_brain": {
            "provider": "mock",
            "model": "mock",
            "auth_ref": "none",
            "wire_format": "mock",
        },
        "teams": {
            "scratch-01": {
                "template": "research",
                "goal": "Scratch goal",
                "lead_member": "analyst",
                "members": [
                    {
                        "id": "analyst",
                        "role": "researcher",
                        "provider": "mock",
                        "model": "mock",
                        "auth_ref": "none",
                        "wire_format": "mock",
                        "capabilities": ["tool_calling", "structured_json"],
                        "toolsets": ["web"],
                    }
                ],
            }
        },
    }
    cfg_path = tmp_path / "airlangga.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    run_dir = tmp_path / "runs"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "run",
            "--config", str(cfg_path),
            "--team", "scratch-01",
            "--goal", "Summarize P0 findings",
            "--run-dir", str(run_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Mock researcher completed its assigned work" in result.output
    assert "Summarize P0 findings" in result.output


def test_trace_includes_evidence_diff_and_questions_and_handles_missing_blackboard(tmp_path):
    # Case 1: Ledger without sibling blackboard.db must succeed and not create blackboard.db.
    dir_no_bb = tmp_path / "no_bb"
    ledger = Ledger(dir_no_bb / "ledger.db")
    ledger.append("run-empty", "plan_created", "main_brain", {"goal": "g", "contracts": []})
    ledger.close()

    runner = CliRunner()
    res = runner.invoke(
        cli, ["trace", "--ledger", str(dir_no_bb / "ledger.db"), "--run-id", "run-empty"]
    )
    assert res.exit_code == 0, res.output
    assert "Run run-empty" in res.output
    assert not (dir_no_bb / "blackboard.db").exists()

    # Case 2: Rich report with evidence_refs, diff, open_questions appears in trace.
    dir_rich = tmp_path / "rich"
    ledger2 = Ledger(dir_rich / "ledger.db")
    ledger2.append("run-rich", "plan_created", "main_brain", {"goal": "Rich", "contracts": ["c1"]})
    ledger2.close()
    board = Blackboard(dir_rich / "blackboard.db")
    eid = board.propose(
        "run-rich",
        "team-1",
        "fact",
        "Report from analyst (c1)",
        json.dumps({
            "contract_id": "c1",
            "member_id": "analyst",
            "claims": [
                {
                    "claim": "Verified result text",
                    "evidence_refs": ["artifact://ev-1"],
                    "confidence": 0.95,
                }
            ],
            "diff": "artifact://diff-1",
            "open_questions": ["Need follow-up?"],
            "verdict_self": "pass",
        }),
        author="analyst",
    )
    board.commit(eid, by_role="lead")
    board.close()

    res2 = runner.invoke(
        cli, ["trace", "--ledger", str(dir_rich / "ledger.db"), "--run-id", "run-rich"]
    )
    assert res2.exit_code == 0, res2.output
    assert "Outputs:" in res2.output
    assert "Verified result text (confidence 0.95) [evidence: artifact://ev-1]" in res2.output
    assert "diff: artifact://diff-1" in res2.output
    assert "? Need follow-up?" in res2.output
