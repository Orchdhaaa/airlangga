"""Airlangga CLI: init / validate / run / demo / trace / replay /
telegram gateway / API server / scheduler."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import click

from .api_server import run_server
from .blackboard import Blackboard
from .budget import BudgetGovernor
from .config import AirlanggaConfig
from .gateway_telegram import TelegramGateway
from .ledger import Ledger
from .scheduler import Job, Scheduler
from .team import TeamRuntime, new_run_id
from .trace import baseline_comparison, render_trace

PACKAGE_DIR = Path(__file__).resolve().parent
EXAMPLE_CONFIG = PACKAGE_DIR.parent / "airlangga.yaml"


def _mockify(config: AirlanggaConfig) -> AirlanggaConfig:
    """Replace every endpoint with the offline mock provider (demo mode)."""
    config.main_brain.provider = "mock"
    config.main_brain.wire_format = "mock"
    config.main_brain.auth_ref = "none"
    for team in config.teams.values():
        for member in team.members:
            member.provider = "mock"
            member.wire_format = "mock"
            member.auth_ref = "none"
            member.endpoint = None
            member.fallback = []
    return config


def _run_team(config: AirlanggaConfig, team_name: str, goal: str, run_dir: Path,
              files_root: Path | None = None) -> str:
    run_id = new_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(run_dir / "ledger.db")
    blackboard = Blackboard(run_dir / "blackboard.db")
    budget = BudgetGovernor()
    budget.set_cap(f"run:{run_id}", config.main_brain.budget)
    runtime = TeamRuntime(
        config=config,
        team_name=team_name,
        run_id=run_id,
        ledger=ledger,
        blackboard=blackboard,
        budget=budget,
        workdir=str(run_dir / "artifacts"),
        files_root=files_root,
    )
    reports = runtime.run_team(goal)
    click.echo(f"Run {run_id}: {len(reports)} member report(s)")
    for report in reports:
        click.echo(
            f"  {report.member_id}: verdict={report.verdict_self} "
            f"claims={len(report.claims)} cost_usd=${report.cost.get('usd', 0.0):.4f}"
        )
    click.echo(render_trace(ledger, run_id))
    state = ledger.reconstruct(run_id)
    total_usd = sum(c["usd"] for c in state["cost_by_actor"].values())
    passed = all(v == "done" for v in state["contracts"].values())
    ledger.close()
    blackboard.close()
    return run_id, total_usd, passed


@click.group()
def cli() -> None:
    """Airlangga — a persistent, accountable Agentic Team runtime."""


@cli.command()
@click.option("--path", default="airlangga.yaml", help="Where to write the example config.")
def init(path: str) -> None:
    """Write an example airlangga.yaml in the current directory."""
    dest = Path(path)
    if dest.exists():
        raise click.ClickException(f"{dest} already exists; refusing to overwrite")
    shutil.copy(EXAMPLE_CONFIG, dest)
    click.echo(f"Wrote example config to {dest}")


@cli.command(name="validate")
@click.option("--config", default="airlangga.yaml", help="Config file to validate.")
def validate_cmd(config: str) -> None:
    """Validate an airlangga.yaml config file."""
    cfg = AirlanggaConfig.load(config)
    teams = ", ".join(
        f"{name} ({len(team.members)} members)" for name, team in cfg.teams.items()
    )
    click.echo(f"Config OK: {len(cfg.teams)} team(s): {teams or 'none'}")


@cli.command()
@click.option("--config", default="airlangga.yaml", help="Config file.")
@click.option("--team", default="research-01", help="Team to run.")
@click.option("--goal", required=True, help="Goal for the Main Brain.")
@click.option("--run-dir", default="runs", help="Directory for run state.")
def run(config: str, team: str, goal: str, run_dir: str) -> None:
    """Run a team against a goal (uses the configured providers)."""
    cfg = AirlanggaConfig.load(config)
    _run_team(cfg, team, goal, Path(run_dir),
              files_root=Path(config).resolve().parent / "files")


@cli.command()
@click.option("--goal", default="Produce a sourced brief on the history of the Airlangga kingdom.",
              help="Goal for the demo run.")
@click.option("--run-dir", default="runs", help="Directory for run state.")
def demo(goal: str, run_dir: str) -> None:
    """Run the demo end to end with the offline mock provider (no API key)."""
    cfg = _mockify(AirlanggaConfig.load(EXAMPLE_CONFIG))
    click.echo("Demo run (mock provider, no API key, no network)")
    _run_team(cfg, "research-01", goal, Path(run_dir))


@cli.command()
@click.option("--ledger", required=True, help="Ledger database path (runs/<run>/ledger.db).")
@click.option("--run-id", required=True, help="Run id to trace.")
def trace(ledger: str, run_id: str) -> None:
    """Show the trace for a recorded run."""
    store = Ledger(ledger)
    click.echo(render_trace(store, run_id))
    store.close()


@cli.command()
@click.option("--ledger", required=True, help="Ledger database path.")
@click.option("--run-id", required=True, help="Run id to replay.")
@click.option("--config", default="airlangga.yaml", help="Config to replay against.")
def replay(ledger: str, run_id: str, config: str) -> None:
    """Replay a recorded run against the mock provider and compare with
    the single-agent baseline (same goal, first member only)."""
    store = Ledger(ledger)
    state = store.reconstruct(run_id)
    goal = ""
    for ev in store.events(run_id):
        if ev["type"] == "plan_created":
            goal = str(ev["payload"].get("goal", ""))
    click.echo(f"Replaying {run_id}: recorded contracts={state['contracts']}")
    total_usd = sum(c["usd"] for c in state["cost_by_actor"].values())
    team_passed = all(v == "done" for v in state["contracts"].values())
    click.echo(f"Recorded team: passed={team_passed} cost_usd=${total_usd:.4f}")
    store.close()
    if not goal:
        click.echo("No plan_created event found; cannot replay.")
        return
    cfg = _mockify(AirlanggaConfig.load(config))
    # Team replay (mock).
    click.echo("--- team replay (mock) ---")
    _replay_id, replay_usd, replay_passed = _run_team(cfg, "research-01", goal, Path("runs"))
    # Single-agent baseline: same goal, first member only.
    baseline_cfg = _mockify(AirlanggaConfig.load(config))
    team_cfg = baseline_cfg.teams["research-01"]
    team_cfg.members = team_cfg.members[:1]
    team_cfg.lead_member = team_cfg.members[0].id
    click.echo("--- single-agent baseline (mock, first member only) ---")
    _base_id, baseline_usd, baseline_passed = _run_team(
        baseline_cfg, "research-01", goal, Path("runs")
    )
    click.echo(
        f"Replayed team: passed={replay_passed} cost_usd=${replay_usd:.4f}; "
        f"baseline: passed={baseline_passed} cost_usd=${baseline_usd:.4f}"
    )
    click.echo(
        baseline_comparison(
            team_cost_usd=replay_usd,
            team_passed=replay_passed,
            baseline_cost_usd=baseline_usd,
            baseline_passed=baseline_passed,
        )
    )


@cli.command()
@click.option("--config", default="airlangga.yaml", help="Config file.")
@click.option("--team", default="research-01", help="Team to run goals with.")
@click.option("--allow-user", multiple=True, type=int, help="Telegram user ID on the allowlist (repeatable).")
@click.option("--mock/--no-mock", default=True, help="Use the offline mock provider.")
@click.option("--max-iterations", default=0, help="Poll iterations (0 = run forever).")
def telegram(config: str, team: str, allow_user: tuple[int, ...], mock: bool, max_iterations: int) -> None:
    """Run the Telegram gateway: receive /goal messages, run the team,
    reply with the result. Token from TELEGRAM_BOT_TOKEN (env only)."""
    allowed = list(allow_user) or [
        int(x) for x in os.environ.get("AIRLANGGA_TELEGRAM_ALLOWLIST", "").split(",") if x.strip()
    ]
    if not allowed:
        raise click.ClickException(
            "no Telegram user on the allowlist; pass --allow-user <id> or set AIRLANGGA_TELEGRAM_ALLOWLIST"
        )
    cfg = AirlanggaConfig.load(config)
    if mock:
        cfg = _mockify(cfg)
    gateway = TelegramGateway(allowed_user_ids=allowed)
    click.echo(f"Telegram gateway running (allowlist: {allowed}); send /goal <your goal>")

    def on_goal(parsed: dict) -> str:
        _run_team(cfg, team, parsed["goal"], Path("runs"))
        return f"Done. Goal: {parsed['goal']!r} — see the run trace in runs/."

    gateway.poll_loop(on_goal, max_iterations=max_iterations or None)
    gateway.close()


@cli.command()
@click.option("--config", default="airlangga.yaml", help="Config file.")
@click.option("--host", default="127.0.0.1", help="Bind address (default: localhost only).")
@click.option("--port", default=8765, type=int, help="Port.")
@click.option("--mock/--no-mock", default=True, help="Use the offline mock provider.")
def serve(config: str, host: str, port: int, mock: bool) -> None:
    """Serve the OpenAI-compatible API stub (GET /v1/models,
    POST /v1/chat/completions). Local bind only by default."""
    cfg = AirlanggaConfig.load(config)
    if mock:
        cfg = _mockify(cfg)
    server = run_server(cfg, host=host, port=port)
    click.echo(f"Airlangga API server on http://{host}:{port} (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.shutdown()


@cli.command()
@click.option("--config", default="airlangga.yaml", help="Config file.")
@click.option("--host", default="127.0.0.1", help="Bind address (default: localhost only).")
@click.option("--port", default=None, type=int, help="Port (default: $AIRLANGGA_UI_PORT or 8100).")
@click.option("--project-root", default=".", help="Project root (holds airlangga.yaml, files/, runs/).")
def ui(config: str, host: str, port: int | None, project_root: str) -> None:
    """Serve the Web UI: node-graph team editor, config, files, runs.

    Binds localhost by default. A public address requires the
    AIRLANGGA_UI_TOKEN environment variable (no default password).
    """
    import os as _os

    from .web_ui import UI_DEFAULT_PORT, run_ui_server

    port = port if port is not None else int(_os.environ.get("AIRLANGGA_UI_PORT", UI_DEFAULT_PORT))
    server = run_ui_server(project_root, host=host, port=port, config_name=config)
    click.echo(f"Airlangga Web UI on http://{host}:{port} (Ctrl-C to stop)")
    if not _os.environ.get("AIRLANGGA_UI_TOKEN"):
        click.echo("Warning: no AIRLANGGA_UI_TOKEN set — localhost only, no auth.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.shutdown()


@cli.command()
@click.option("--config", default="airlangga.yaml", help="Config file.")
@click.option("--team", default="research-01", help="Team to run.")
@click.option("--goal", required=True, help="Goal for the scheduled job.")
@click.option("--interval-min", default=60, type=int, help="Job interval in minutes.")
@click.option("--mock/--no-mock", default=True, help="Use the offline mock provider.")
def schedule(config: str, team: str, goal: str, interval_min: int, mock: bool) -> None:
    """Run one scheduler tick: run the team job if it is due."""
    cfg = AirlanggaConfig.load(config)
    if mock:
        cfg = _mockify(cfg)
    scheduler = Scheduler(Path("runs") / "scheduler.lock")
    scheduler.add(
        Job(
            name=f"{team}-job",
            team=team,
            goal=goal,
            interval_s=interval_min * 60,
            run=lambda g: _run_team(cfg, team, g, Path("runs")),
        )
    )
    ran = scheduler.tick()
    click.echo(f"Scheduler tick: ran {ran or 'nothing (not due)'}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
