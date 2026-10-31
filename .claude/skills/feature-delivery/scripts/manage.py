#!/usr/bin/env python3
"""Reversible, user-level installation. Standard library only; no runtime config rewrites."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]
BEGIN = b"<!-- feature-delivery:begin -->"
END = b"<!-- feature-delivery:end -->"
RUNTIMES = {
    "codex": (".codex/skills/feature-delivery", ".codex/AGENTS.md"),
    "opencode": (".config/opencode/skills/feature-delivery", ".config/opencode/AGENTS.md"),
    "pi": (".pi/agent/skills/feature-delivery", ".pi/agent/AGENTS.md"),
    "claude": (".claude/skills/feature-delivery", ".claude/CLAUDE.md"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".feature-delivery.tmp")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    return json.loads(path.read_text())


def routing():
    return (BEGIN + b"\nFor feature implementation (including tiny features), use the feature-delivery skill. "
            b"Coordinator dispatches independent implementer and design-review peers; design agreement precedes coding. "
            b"Delegated implementer/reviewer: obey your assigned role, do not recursively launch this workflow. "
            b"Pure discussion/research does not trigger it. Preserve existing instructions and authorization.\n" + END + b"\n")


def agent_content(role, profile):
    data = (SKILL / "adapters/opencode" / f"{role}.md").read_bytes()
    model = profile["runtimes"].get("opencode", {}).get(role)
    if model:
        data = data.replace(b"mode: subagent\n", b"mode: subagent\nmodel: " + json.dumps(model).encode() + b"\n", 1)
    return data


def paths(home):
    return home / ".local/state/feature-delivery/install.json", home / ".config/feature-delivery/profile.json"


def load_manifest(home):
    manifest, _ = paths(home)
    if manifest.is_symlink():
        raise ValueError("Manifest may not be a symlink")
    return read_json(manifest) if manifest.exists() else None


def check_profile(profile):
    if profile.get("schema") != 1 or not isinstance(profile.get("runtimes"), dict):
        raise ValueError("Profile requires schema 1 and runtimes object")
    for runtime, roles in profile["runtimes"].items():
        if runtime not in RUNTIMES or not isinstance(roles, dict):
            raise ValueError("Unknown runtime or malformed role profile")
        for role, model in roles.items():
            if role not in ("implementer", "reviewer", "computer_use") or not (model is None or isinstance(model, str) and model.strip()):
                raise ValueError("Invalid profile role/model")


def owned_problems(home, manifest):
    problems = []
    if manifest.get("source") != str(SKILL):
        problems.append("Installation belongs to another source; uninstall from that source first")
    for entry in manifest["entries"]:
        path = home / entry["path"]
        if entry["kind"] == "link":
            if not path.is_symlink() or os.readlink(path) != entry["target"]:
                problems.append(f"Changed/missing managed link: {path}")
        elif entry["kind"] == "routing":
            if path.is_symlink() or not path.is_file():
                problems.append(f"Changed/missing routing file: {path}")
                continue
            data = path.read_bytes()
            addition = entry["addition"].encode()
            if data.count(BEGIN) != 1 or data.count(END) != 1 or data.count(addition) != 1:
                problems.append(f"Changed managed routing block: {path}")
        elif entry["kind"] == "agent":
            if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != entry["hash"]:
                problems.append(f"Changed/missing managed agent: {path}")
    return problems


def install(home, selected, profile_source, dry_run):
    manifest_path, profile_path = paths(home)
    existing = load_manifest(home)
    if existing:
        problems = owned_problems(home, existing)
        if not profile_path.is_file() or profile_path.is_symlink():
            problems.append("Missing or unsafe profile")
        else:
            check_profile(read_json(profile_path))
        if set(existing["runtimes"]) != set(selected):
            problems.append("Runtime selection differs; uninstall before changing selected runtimes")
        if problems:
            raise ValueError("; ".join(problems))
        print(json.dumps({"action": "install", "result": "already installed", "profile": str(profile_path)}))
        return
    profile_data = profile_source.read_bytes()
    profile = json.loads(profile_data)
    check_profile(profile)
    entries = []
    plans = []
    # Complete preflight before any destination is written.
    for runtime in selected:
        link_rel, route_rel = RUNTIMES[runtime]
        link, route = home / link_rel, home / route_rel
        if link.exists() or link.is_symlink():
            raise ValueError(f"Conflict at {link}; existing paths are never adopted or replaced")
        if route.is_symlink() or route.exists() and not route.is_file():
            raise ValueError(f"Routing path must be a regular file: {route}")
        original = route.read_bytes() if route.exists() else b""
        if BEGIN in original or END in original:
            raise ValueError(f"Unowned routing marker conflict: {route}")
        separator = b"" if not original or original.endswith(b"\n") else b"\n"
        addition = separator + routing()
        entries.append({"kind": "link", "path": link_rel, "target": str(SKILL)})
        entries.append({"kind": "routing", "path": route_rel, "addition": addition.decode(), "existed": route.exists()})
        plans.append((link, route, original, addition))
    if profile_path.is_symlink() or profile_path.exists() and not profile_path.is_file():
        raise ValueError(f"Profile path must be a regular file: {profile_path}")
    if profile_path.exists():
        profile = read_json(profile_path)
        check_profile(profile)
    agent_plans = []
    if "opencode" in selected:
        for role in ("implementer", "reviewer"):
            relative = f".config/opencode/agents/feature-delivery-{role}.md"
            destination = home / relative
            if destination.exists() or destination.is_symlink():
                raise ValueError(f"Conflict at {destination}; existing agents are never replaced")
            content = agent_content(role, profile)
            agent_plans.append((destination, content))
            entries.append({"kind": "agent", "path": relative, "role": role, "hash": digest(content)})
    # Reject symlinked parent directories: otherwise an innocuous --home can write elsewhere.
    for destination in [manifest_path, profile_path] + [p for plan in plans for p in plan[:2]] + [p for p, _ in agent_plans]:
        for parent in destination.parents:
            if parent == home:
                break
            if parent.is_symlink() or parent.exists() and not parent.is_dir():
                raise ValueError(f"Unsafe destination parent: {parent}")
    result = {"action": "install", "dry_run": dry_run, "source": str(SKILL), "runtimes": selected, "profile": str(profile_path)}
    if dry_run:
        print(json.dumps(result))
        return
    manifest = {"schema": 1, "source": str(SKILL), "runtimes": selected, "entries": entries}
    completed = []
    try:
        for link, route, original, addition in plans:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(SKILL, target_is_directory=True)
            completed.append(("link", link, None))
            existed = route.exists()
            atomic_write(route, original + addition)
            completed.append(("file", route, original if existed else None))
        for destination, content in agent_plans:
            atomic_write(destination, content)
            completed.append(("file", destination, None))
        if not profile_path.exists():
            atomic_write(profile_path, profile_data)
            manifest["profile_hash"] = digest(profile_data)
            completed.append(("file", profile_path, None))
        atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode())
    except BaseException:
        for kind, path, original in reversed(completed):
            if kind == "link" or original is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, original)
        raise
    print(json.dumps(result))


def uninstall(home, dry_run):
    manifest_path, profile_path = paths(home)
    manifest = load_manifest(home)
    if not manifest:
        print(json.dumps({"action": "uninstall", "result": "not installed"}))
        return
    problems = owned_problems(home, manifest)
    if problems:
        raise ValueError("; ".join(problems) + "; nothing removed")
    preserved = []
    remove_profile = False
    if "profile_hash" in manifest and profile_path.exists():
        remove_profile = not profile_path.is_symlink() and digest(profile_path.read_bytes()) == manifest["profile_hash"]
        if not remove_profile:
            preserved.append(str(profile_path))
    if not dry_run:
        for entry in manifest["entries"]:
            path = home / entry["path"]
            if entry["kind"] in ("link", "agent"):
                path.unlink()
            else:
                data = path.read_bytes().replace(entry["addition"].encode(), b"", 1)
                if not entry["existed"] and not data:
                    path.unlink()
                else:
                    atomic_write(path, data)
        if remove_profile:
            profile_path.unlink()
        manifest_path.unlink()
    print(json.dumps({"action": "uninstall", "dry_run": dry_run, "preserved_edited_files": preserved,
                      "note": "Peer sessions retained for resumption; remove separately if no longer needed"}))


def sync_models(home, dry_run):
    manifest_path, profile_path = paths(home)
    manifest = load_manifest(home)
    if not manifest:
        raise ValueError("Install before syncing models")
    problems = owned_problems(home, manifest)
    if problems:
        raise ValueError("; ".join(problems) + "; nothing updated")
    if profile_path.is_symlink():
        raise ValueError("Profile may not be a symlink")
    profile = read_json(profile_path)
    check_profile(profile)
    updates = []
    for entry in manifest["entries"]:
        if entry["kind"] == "agent":
            content = agent_content(entry["role"], profile)
            updates.append((home / entry["path"], content))
            entry["hash"] = digest(content)
    if not dry_run:
        originals = [(path, path.read_bytes()) for path, _ in updates]
        try:
            for path, content in updates:
                atomic_write(path, content)
            atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode())
        except BaseException:
            for path, content in originals:
                atomic_write(path, content)
            raise
    print(json.dumps({"action": "sync-models", "dry_run": dry_run, "updated": len(updates)}))


def verify(home):
    manifest = load_manifest(home)
    problems = owned_problems(home, manifest) if manifest else ["Not installed"]
    _, profile = paths(home)
    if not profile.is_file() or profile.is_symlink():
        problems.append("Missing or unsafe user profile")
    else:
        try:
            check_profile(read_json(profile))
        except (ValueError, OSError) as exc:
            problems.append(str(exc))
        if manifest:
            for entry in manifest["entries"]:
                if entry["kind"] == "agent" and entry["hash"] != digest(agent_content(entry["role"], read_json(profile))):
                    problems.append("OpenCode models differ from profile; run sync-models")
    print(json.dumps({"action": "verify", "ok": not problems, "problems": problems}))
    return not problems


def catalog_models(runtime, output):
    """Return exact base model IDs for known CLI formats, or None for unknown output."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if runtime == "opencode":
        if not lines or any(not re.fullmatch(r"[^\s/]+/[^\s]+", line) for line in lines):
            return None
        return set(lines)
    if runtime == "pi":
        if not lines or lines[0].split() != ["provider", "model", "context", "max-out", "thinking", "images"]:
            return None
        models = set()
        for line in lines[1:]:
            columns = line.split()
            if len(columns) != 6 or "/" in columns[0] or columns[4] not in ("yes", "no") or columns[5] not in ("yes", "no"):
                return None
            models.add(columns[0] + "/" + columns[1])
        return models
    return None


def doctor(home, probe):
    info = {}
    _, profile_path = paths(home)
    profile = read_json(profile_path) if profile_path.is_file() else read_json(SKILL / "profiles/default.json")
    check_profile(profile)
    for runtime in RUNTIMES:
        binary = shutil.which(runtime)
        item = {"available": bool(binary), "roles": profile["runtimes"].get(runtime, {}),
                "peer_route": "persistent CLI bridge" if runtime == "pi" else "detect native agent tool at runtime"}
        if binary:
            try:
                result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
                item["version"] = result.stdout.strip()[:160] if result.returncode == 0 else "version probe failed"
                if probe and runtime in ("pi", "opencode"):
                    args = [binary, "--list-models"] if runtime == "pi" else [binary, "models"]
                    catalog = subprocess.run(args, capture_output=True, text=True, timeout=30)
                    models = catalog_models(runtime, catalog.stdout) if catalog.returncode == 0 else None
                    item["model_catalog_probe"] = ("ok" if models is not None else "unknown format; inspect CLI locally") if catalog.returncode == 0 else "failed; inspect CLI locally"
                    item["configured_models_seen"] = {
                        role: None if models is None else (model.split("#", 1)[0] if runtime == "opencode" else model) in models
                        for role, model in item["roles"].items() if model
                    }
                    if runtime == "opencode":
                        item["configured_variants_verified"] = {role: False for role, model in item["roles"].items() if model and "#" in model}
            except (OSError, subprocess.TimeoutExpired):
                item["probe_error"] = "CLI unavailable or timed out"
        info[runtime] = item
    print(json.dumps({"action": "doctor", "runtimes": info, "note": "Catalog/config presence does not verify authentication, live generation or OpenCode variants; null presence means unknown catalog format. Native tools require session inspection"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "install", "verify", "doctor", "uninstall", "sync-models"))
    parser.add_argument("--home", type=Path, default=Path.home(), help="User home (temporary directory for lifecycle tests)")
    parser.add_argument("--runtimes", default=",".join(RUNTIMES))
    parser.add_argument("--profile", type=Path, default=SKILL / "profiles/default.json", help="Initial profile; existing profile is preserved")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--probe", action="store_true", help="Doctor only: query model catalogs")
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    selected = list(dict.fromkeys(args.runtimes.split(",")))
    if any(runtime not in RUNTIMES for runtime in selected):
        parser.error("Unknown runtime")
    try:
        if args.command in ("plan", "install"):
            install(home, selected, args.profile, args.dry_run or args.command == "plan")
        elif args.command == "uninstall":
            uninstall(home, args.dry_run)
        elif args.command == "verify":
            return 0 if verify(home) else 1
        elif args.command == "sync-models":
            sync_models(home, args.dry_run)
        else:
            doctor(home, args.probe)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
