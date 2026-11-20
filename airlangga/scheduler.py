"""Small job runner: a tick loop with a file lock so overlapping ticks
cannot run. Team-scheduled work is a job with a team target, a contract
template, and its own budget — the same code path as interactive runs.
"""

from __future__ import annotations

import fcntl
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Job:
    name: str
    team: str
    goal: str
    interval_s: int = 3600
    last_run: float = 0.0
    run: Callable[[str], None] | None = None


class Scheduler:
    def __init__(self, lock_path: str | Path) -> None:
        self.lock_path = Path(lock_path)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.jobs: list[Job] = []

    def add(self, job: Job) -> None:
        self.jobs.append(job)

    def tick(self) -> list[str]:
        """Run due jobs once, under a file lock. Returns names of jobs run."""
        ran: list[str] = []
        with open(self.lock_path, "w", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return ran  # another tick is already running
            now = time.time()
            for job in self.jobs:
                if now - job.last_run >= job.interval_s and job.run is not None:
                    job.run(job.goal)
                    job.last_run = now
                    ran.append(job.name)
        return ran
