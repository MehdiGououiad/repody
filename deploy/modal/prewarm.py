# ruff: noqa: T201, S603, S607 - a script: it prints progress and runs the Modal CLI
"""Pre-warm the deployed NuExtract app after a deploy, so the slow starts that build its memory
snapshots (2-3 per GPU type, https://modal.com/docs/guide/memory-snapshots) happen here and not
on a client's run.

It calls the *deployed* app (snapshots are only made for deployed apps, never for `modal run`),
then stops its container, so each call is a fresh start. Each line says how long a start took:
minutes while a snapshot is built, seconds once one is restored.

    uv run --no-project --with modal python deploy/modal/prewarm.py --env main
    uv run --no-project --with modal python deploy/modal/prewarm.py --env staging
"""

import argparse
import json
import subprocess
import time

import modal

APP = "repody-nuextract"


def modal_cli(*args: str) -> str:
    return subprocess.run(["modal", *args], capture_output=True, text=True, check=True).stdout


def deployed_app_id(env: str) -> str:
    apps = json.loads(modal_cli("app", "list", "--env", env, "--json"))
    return next(a["app_id"] for a in apps if a["description"] == APP and a["state"] == "deployed")


def stop_containers(env: str, app_id: str) -> None:
    """Stop the app's containers and wait until none is left, so the next call starts cold."""
    while True:
        containers = json.loads(modal_cli("container", "list", "--env", env, "--json"))
        ids = [c["container_id"] for c in containers if c["app_id"] == app_id]
        if not ids:
            return
        for container_id in ids:
            subprocess.run(["modal", "container", "stop", container_id, "--yes"], check=False)
        time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", default="main", help="Modal environment (main is production)")
    parser.add_argument("--starts", type=int, default=4)
    args = parser.parse_args()

    app_id = deployed_app_id(args.env)
    vllm = modal.Cls.from_name(APP, "Vllm", environment_name=args.env)
    stop_containers(args.env, app_id)
    for start in range(1, args.starts + 1):
        began = time.monotonic()
        vllm().ping.remote()
        print(f"start {start}: ready in {time.monotonic() - began:.0f} s", flush=True)
        stop_containers(args.env, app_id)


if __name__ == "__main__":
    main()
