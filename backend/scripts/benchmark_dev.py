#!/usr/bin/env python3
"""Unified dev benchmarks: stress, queue depth, extraction experiments.

Usage:
  python backend/scripts/benchmark_dev.py stress --api http://127.0.0.1:8000
  python backend/scripts/benchmark_dev.py queue --runs 4
  python backend/scripts/benchmark_dev.py experiments --trial all
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
for _path in (_BACKEND / "src", _BACKEND):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)


def _stress_parser(sub: argparse._SubParsersAction) -> None:
    from scripts.benchmark_dev_stress import add_arguments, run_stress

    parser = sub.add_parser("stress", help="Queue stress test (burst + random traffic)")
    add_arguments(parser)
    parser.set_defaults(_runner=lambda args: asyncio.run(run_stress(args)))


def _queue_parser(sub: argparse._SubParsersAction) -> None:
    from scripts.benchmark_dev_queue import add_arguments, run_benchmark

    parser = sub.add_parser("queue", help="Benchmark queue depth while OCR worker is busy")
    add_arguments(parser)
    parser.set_defaults(_runner=lambda args: asyncio.run(run_benchmark(args)))


def _experiments_parser(sub: argparse._SubParsersAction) -> None:
    from scripts.benchmark_dev_experiments import add_arguments, run_experiments

    parser = sub.add_parser("experiments", help="Facture extraction speed experiments")
    add_arguments(parser)
    parser.set_defaults(_runner=lambda args: asyncio.run(run_experiments(args)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    _stress_parser(sub)
    _queue_parser(sub)
    _experiments_parser(sub)
    args = parser.parse_args()
    return args._runner(args)


if __name__ == "__main__":
    raise SystemExit(main())
