"""Canonical run lifecycle status — shared by ORM, domain, and services."""

from __future__ import annotations

import enum


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
