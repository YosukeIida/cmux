#!/usr/bin/env python3

import argparse
import json
import os
import queue
import statistics
import subprocess
import threading
import time
from pathlib import Path


def write_command(proc: subprocess.Popen[bytes], payload: dict[str, object]) -> float:
    assert proc.stdin is not None
    started = time.perf_counter()
    proc.stdin.write(json.dumps(payload, separators=(",", ":")).encode() + b"\n")
    proc.stdin.flush()
    return started


def wait_for_response(
    responses: queue.Queue[tuple[float, dict[str, object]]],
    request_id: str,
    timeout: float,
) -> tuple[dict[str, object], float]:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        try:
            received, payload = responses.get(timeout=max(0.0, deadline - time.perf_counter()))
        except queue.Empty:
            break
        if payload.get("type") == "response" and payload.get("id") == request_id:
            return payload, received
    raise TimeoutError(f"timed out waiting for {request_id}")


def read_jsonl(
    proc: subprocess.Popen[bytes],
    responses: queue.Queue[tuple[float, dict[str, object]]],
) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        received = time.perf_counter()
        responses.put((received, json.loads(line)))


def run_trial(
    *,
    label: str,
    iteration: int,
    pi: str,
    extension: str,
    evidence: Path,
    cli: str,
    socket: str,
    workspace_id: str,
    surface_id: str,
    window_id: str,
) -> dict[str, object]:
    session_id = f"pi-rpc-{label}-{iteration}"
    args = [
        pi,
        "--mode",
        "rpc",
        "--offline",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--tools",
        "ls",
        "--session-dir",
        str(evidence / "rpc-sessions"),
        "--session-id",
        session_id,
        "--name",
        session_id,
    ]
    if label == "noext":
        args.insert(1, "-ne")
    elif label == "cmux-only":
        args[1:1] = ["-ne", "-e", extension]

    env = os.environ.copy()
    env.update(
        {
            "CMUX_SOCKET": socket,
            "CMUX_SOCKET_PATH": socket,
            "CMUX_WORKSPACE_ID": workspace_id,
            "CMUX_SURFACE_ID": surface_id,
            "CMUX_WINDOW_ID": window_id,
            "CMUX_BUNDLED_CLI_PATH": cli,
            "CMUX_PI_CMUX_BIN": str(evidence / "cmux-timing-wrapper.zsh"),
            "CMUX_TEST_PI_TIMING_LOG": str(evidence / f"rpc-{label}-hooks.log"),
            "CMUX_AGENT_HOOK_STATE_DIR": str(evidence / "hook-state"),
        }
    )

    spawned_at = time.perf_counter()
    proc = subprocess.Popen(
        args,
        cwd=evidence.parents[1],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    responses: queue.Queue[tuple[float, dict[str, object]]] = queue.Queue()
    reader = threading.Thread(target=read_jsonl, args=(proc, responses), daemon=True)
    reader.start()
    result: dict[str, object] = {"label": label, "iteration": iteration}
    try:
        ready_id = f"ready-{label}-{iteration}"
        write_command(proc, {"id": ready_id, "type": "get_state"})
        ready_response, ready_at = wait_for_response(responses, ready_id, 15)
        if not ready_response.get("success"):
            raise RuntimeError(f"startup failed: {ready_response}")
        result["startup_ms"] = round((ready_at - spawned_at) * 1000, 3)

        prompt_id = f"prompt-{label}-{iteration}"
        prompt_started = write_command(
            proc,
            {
                "id": prompt_id,
                "type": "prompt",
                "message": f"Reply with exactly READY {label} {iteration}.",
            },
        )
        prompt_response, prompt_at = wait_for_response(responses, prompt_id, 15)
        if not prompt_response.get("success"):
            raise RuntimeError(f"prompt failed: {prompt_response}")
        result["prompt_accept_ms"] = round((prompt_at - prompt_started) * 1000, 3)

        abort_id = f"abort-{label}-{iteration}"
        abort_started = write_command(proc, {"id": abort_id, "type": "abort"})
        abort_response, abort_at = wait_for_response(responses, abort_id, 15)
        if not abort_response.get("success"):
            raise RuntimeError(f"abort failed: {abort_response}")
        result["abort_ms"] = round((abort_at - abort_started) * 1000, 3)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            result["forced_kill"] = True
        assert proc.stderr is not None
        stderr = proc.stderr.read().decode(errors="replace").strip()
        if stderr:
            result["stderr"] = stderr
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pi", required=True)
    parser.add_argument("--extension", required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        help="label,workspace-id,surface-id",
    )
    args = parser.parse_args()

    evidence = Path(__file__).resolve().parent
    (evidence / "rpc-sessions").mkdir(exist_ok=True)
    (evidence / "hook-state").mkdir(exist_ok=True)
    targets: dict[str, tuple[str, str]] = {}
    for raw in args.target:
        label, workspace_id, surface_id = raw.split(",", 2)
        targets[label] = (workspace_id, surface_id)

    results: list[dict[str, object]] = []
    for iteration in range(1, args.trials + 1):
        for label in ("noext", "cmux-only", "all"):
            workspace_id, surface_id = targets[label]
            trial = run_trial(
                label=label,
                iteration=iteration,
                pi=args.pi,
                extension=args.extension,
                evidence=evidence,
                cli=args.cli,
                socket=args.socket,
                workspace_id=workspace_id,
                surface_id=surface_id,
                window_id=args.window_id,
            )
            results.append(trial)
            print(json.dumps(trial), flush=True)

    summary: dict[str, dict[str, float]] = {}
    for label in ("noext", "cmux-only", "all"):
        label_results = [item for item in results if item["label"] == label]
        summary[label] = {}
        for metric in ("startup_ms", "prompt_accept_ms", "abort_ms"):
            values = [float(item[metric]) for item in label_results]
            summary[label][f"{metric}_median"] = round(statistics.median(values), 3)
            summary[label][f"{metric}_min"] = round(min(values), 3)
            summary[label][f"{metric}_max"] = round(max(values), 3)
    output = {"results": results, "summary": summary}
    output_path = evidence / "rpc-prompt-latency.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"summary": summary, "output": str(output_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
