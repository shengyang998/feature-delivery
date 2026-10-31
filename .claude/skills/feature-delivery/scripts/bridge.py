#!/usr/bin/env python3
"""Persistent independent Pi peers via coordinator relay. No extension required."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import uuid

from manage import SKILL, atomic_write, check_profile, read_json


def capability(binary):
    version = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
    help_result = subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=15)
    required = ("--session-id", "--session-dir", "--mode", "--append-system-prompt")
    if version.returncode or help_result.returncode or not all(flag in help_result.stdout for flag in required):
        raise ValueError("Unsupported Pi CLI: required session/JSON controls unavailable; inspect pi --help")
    return version.stdout.strip()[:160]


def parse_events(stdout):
    """Authoritative message_end records only; never accept partial text as success."""
    response = None
    actual_model = None
    settled = False
    error = None
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ValueError("Pi emitted non-JSON stdout; unsupported CLI/extension output") from exc
        if not isinstance(event, dict):
            raise ValueError("Pi JSON event must be an object")
        if event.get("type") == "agent_settled":
            settled = not event.get("aborted", False)
            if not settled:
                error = "Pi peer aborted"
        if event.get("type") == "message_end":
            message = event.get("message", {})
            if message.get("role") == "assistant":
                if message.get("stopReason") in ("error", "aborted") or message.get("errorMessage"):
                    error = "Pi assistant reported " + str(message.get("stopReason", "error"))
                content = message.get("content", [])
                text = "\n".join(part["text"] for part in content if part.get("type") == "text" and isinstance(part.get("text"), str))
                response = text or None
                if message.get("model"):
                    provider = message.get("provider")
                    actual_model = (provider + "/" if provider else "") + message["model"]
    if error:
        raise ValueError(error)
    if not settled or response is None:
        raise ValueError("Pi JSON contract incomplete: require agent_settled and final assistant text")
    return response, actual_model


def invoke(command, prompt, cwd, timeout):
    environment = dict(os.environ, PWD=str(cwd))
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True, env=environment)
    try:
        stdout, stderr = process.communicate(prompt, timeout=timeout)
        if process.returncode:
            # Keep provider stderr out of public output: it can contain private request/config details.
            raise ValueError(f"Pi peer exited {process.returncode}; inspect private runtime session/logs locally")
        return stdout
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()


def run(args):
    binary = shutil.which(args.pi)
    if not binary:
        raise ValueError("Pi CLI missing; install/configure Pi or use native independent agents")
    version = capability(binary)
    if args.check:
        return {"ok": True, "runtime": "pi", "version": version, "route": "independent persistent subprocesses"}
    if not args.task or not args.role or args.cwd is None:
        raise ValueError("--task, --role and --cwd are required except with --check")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", args.task) or args.task in (".", ".."):
        raise ValueError("Task ID must be 1–101 safe letters/numbers/dots/underscores/hyphens")
    cwd = args.cwd.expanduser().resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("cwd must be a directory")
    profile_path = args.profile.expanduser() if args.profile else Path.home() / ".config/feature-delivery/profile.json"
    if args.profile is not None and not profile_path.is_file():
        raise ValueError("Explicit profile does not exist or is not a file")
    profile = read_json(profile_path) if profile_path.exists() else read_json(SKILL / "profiles/default.json")
    check_profile(profile)
    requested = profile["runtimes"].get("pi", {}).get(args.role)
    model = requested or args.parent_model
    selection = "profile" if requested else "explicit parent model" if args.parent_model else "runtime configured default"
    prompt = sys.stdin.read()
    if not prompt.strip():
        raise ValueError("Supply nonempty task message on stdin")
    peer_dir = args.state_dir.expanduser().resolve() / args.task / args.role
    peer_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = peer_dir / "lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Peer already running; serialize calls to this task/role") from exc
        metadata_path = peer_dir / "peer.json"
        resumed = metadata_path.exists()
        if resumed:
            metadata = read_json(metadata_path)
            if metadata["cwd"] != str(cwd) or metadata["model"] != model:
                raise ValueError("Peer cwd/model changed; use a new task ID and disclose replacement")
        else:
            metadata = {"schema": 1, "session": str(uuid.uuid4()), "cwd": str(cwd), "model": model, "role": args.role}
            atomic_write(metadata_path, (json.dumps(metadata, indent=2) + "\n").encode())
        instructions = (
            f"You are the independent {args.role} peer for feature-delivery task {args.task}. "
            "Follow this assigned role; never recursively start a coordinator/peer workflow or spawn subagents. "
            "Communicate with your partner via the coordinator. Keep this context for follow-ups. "
            "Respect project/user permissions; this role is not a security sandbox. "
        )
        if args.role == "reviewer":
            instructions += ("First discuss the proposed design with the implementer, explicitly agree or request changes. "
                             "After implementation, remain the same reviewer, inspect actual revision and test evidence, "
                             "report findings or revision-bound approval. Do not edit implementation.")
        else:
            instructions += ("Propose concrete design to your reviewer before editing implementation. "
                             "Wait for explicit design agreement relayed by coordinator. Self-test every handoff/commit. "
                             "Fix findings and return the exact revision and test evidence.")
        command = [binary, "--mode", "json", "-p", "--session-id", metadata["session"],
                   "--session-dir", str(peer_dir / "sessions"), "--append-system-prompt", instructions]
        if model:
            command.extend(["--model", model])
        stdout = invoke(command, prompt, cwd, args.timeout)
        response, actual_model = parse_events(stdout)
        return {"runtime": "pi", "version": version, "role": args.role, "task": args.task,
                "session": metadata["session"], "resumed": resumed, "requested_model": requested,
                "selected_model": actual_model or model or "runtime configured default",
                "selection": selection, "fallback": ("Runtime returned a different model identity; coordinator must verify selection"
                                                        if model and actual_model and model != actual_model else None), "response": response}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--task")
    parser.add_argument("--role", choices=("implementer", "reviewer"))
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--profile", type=Path, help="Explicit profile must exist; otherwise use installed or bundled defaults")
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".local/state/feature-delivery/peers")
    parser.add_argument("--parent-model")
    parser.add_argument("--pi", default="pi", help="Pi executable; override for a pinned installation")
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    def terminate(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    try:
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        print(json.dumps({"error": "Peer interrupted; same task/role can resume"}), file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
