"""Safety layers enforced by the runtime, at the action boundary.

These are Airlangga's own layers, written from the spec's first principles:
a hardline denylist that no mode can override, file-write safety, secret
redaction, and input hygiene. Enforcement happens here, in code, never
only in a prompt.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

# Layer 1 — hardline denylist. A proposed tool call / command matching any
# of these is refused outright, regardless of approval mode, Brain, or
# member. Patterns are matched against a normalised (lower-cased,
# whitespace-collapsed) form of the proposed action text.
HARDLINE_PATTERNS: tuple[str, ...] = (
    r"rm\s+-rf\s+/",  # recursive delete from root
    r"rm\s+-rf\s+~",
    r"mkfs(\.|$|\s)",
    r"dd\s+.*of=/dev/",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;",  # fork bomb
    r"shutdown(\s|$)",
    r"reboot(\s|$)",
    r"curl\s+.*\|\s*(sh|bash)",  # pipe-to-shell
    r"wget\s+.*\|\s*(sh|bash)",
    r"/dev/tcp/",
    r"/dev/udp/",
    r"chmod\s+.*777\s+/",
    r"chown\s+-R\s+.*\s+/",
)

_HARDLINE_RES = [re.compile(p) for p in HARDLINE_PATTERNS]


def normalise_action(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def is_hardline(action_text: str) -> str | None:
    """Return the matching pattern, or None when the action is not hardline."""
    text = normalise_action(action_text)
    for pattern, compiled in zip(HARDLINE_PATTERNS, _HARDLINE_RES):
        if compiled.search(text):
            return pattern
    return None


# Layer 2 — file-write safety: paths an agent may never write or patch.
WRITE_DENYLIST: tuple[str, ...] = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".netrc",
    "/etc/sudoers",
    ".env",
    "credentials",
    "id_rsa",
    "id_ed25519",
)


def is_write_denied(path: str) -> bool:
    lowered = path.lower()
    return any(denied in lowered for denied in WRITE_DENYLIST)


def is_write_inside_root(path: str, root: str) -> bool:
    """True when ``path`` resolves inside the run workspace ``root``."""
    try:
        PurePosixPath(path).relative_to(PurePosixPath(root))
        return True
    except ValueError:
        # Absolute paths outside the root, and '..' escapes, fail the check.
        candidate = PurePosixPath(root) / path
        return ".." not in candidate.parts


# Layer 8 — secret redaction for logs, traces, blackboard entries, reports.
_SECRET_RES = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([^\s'\",}]{8,})"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{8,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{8,}"),
]


def redact_secrets(text: str) -> str:
    redacted = _SECRET_RES[0].sub(
        lambda m: f"{m.group(1)}=[REDACTED]", text
    )
    for pattern in _SECRET_RES[1:]:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
