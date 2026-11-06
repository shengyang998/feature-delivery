import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / ".claude/skills/feature-delivery/scripts"
sys.path.insert(0, str(SCRIPTS))
import manage


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()

    def cli(self, command, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPTS / "manage.py"), command, "--home", str(self.home), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_plan_never_writes(self):
        self.cli("plan")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_lifecycle_preserves_bytes_permissions_edits_and_is_idempotent(self):
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)
        originals = {}
        for index, (_, route) in enumerate(manage.RUNTIMES.values()):
            path = self.home / route
            path.parent.mkdir(parents=True, exist_ok=True)
            data = b"Existing instructions\r\n" if index % 2 else b"No final newline"
            path.write_bytes(data)
            path.chmod(0o660)
            originals[path] = data
        self.cli("install")
        before = {p: p.read_bytes() for p in originals}
        self.cli("install")
        self.assertEqual(before, {p: p.read_bytes() for p in originals})
        self.assertTrue(self.cli("verify")["ok"])
        route = next(iter(originals))
        route.write_bytes(b"User added prefix\n" + route.read_bytes())
        self.cli("uninstall", "--dry-run")
        self.assertTrue((self.home / manage.RUNTIMES["codex"][0]).is_symlink())
        self.cli("uninstall")
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), (b"User added prefix\n" if path == route else b"") + original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o660)
        self.cli("uninstall")

    def test_new_files_removed_and_edited_profile_retained(self):
        self.cli("install")
        _, profile = manage.paths(self.home)
        profile.write_bytes(profile.read_bytes() + b"\n")
        result = self.cli("uninstall")
        self.assertIn(str(profile), result["preserved_edited_files"])
        self.assertTrue(profile.exists())
        for link, route in manage.RUNTIMES.values():
            self.assertFalse((self.home / link).is_symlink())
            self.assertFalse((self.home / route).exists())

    def test_conflict_preflight_makes_no_partial_install(self):
        conflict = self.home / manage.RUNTIMES["pi"][0]
        conflict.mkdir(parents=True)
        (conflict / "mine").write_text("owned by user")
        self.cli("install", ok=False)
        self.assertFalse((self.home / manage.RUNTIMES["codex"][0]).exists())
        self.assertEqual((conflict / "mine").read_text(), "owned by user")

    def test_managed_block_edit_refuses_entire_uninstall(self):
        self.cli("install")
        route = self.home / manage.RUNTIMES["pi"][1]
        route.write_bytes(route.read_bytes().replace(b"substantial", b"all"))
        self.cli("uninstall", ok=False)
        self.assertTrue((self.home / manage.RUNTIMES["codex"][0]).is_symlink())
        self.assertIn(b"all shared", route.read_bytes())

    def test_foreign_link_and_symlink_parent_rejected(self):
        foreign = self.home / manage.RUNTIMES["codex"][0]
        foreign.parent.mkdir(parents=True)
        foreign.symlink_to("/does/not/exist")
        self.cli("install", ok=False)
        foreign.unlink()
        outside = self.home / "outside"
        outside.mkdir()
        (self.home / ".pi").symlink_to(outside, target_is_directory=True)
        self.cli("install", ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_models_sync_and_modified_agent_is_preserved(self):
        self.cli("install")
        _, profile_path = manage.paths(self.home)
        profile = json.loads(profile_path.read_text())
        profile["runtimes"]["opencode"]["reviewer"] = "provider/model#variant"
        profile_path.write_text(json.dumps(profile))
        self.cli("verify", ok=False)
        agent = self.home / ".config/opencode/agents/feature-delivery-reviewer.md"
        original = agent.read_bytes()
        self.cli("sync-models", "--dry-run")
        self.assertEqual(agent.read_bytes(), original)
        self.cli("sync-models")
        self.assertIn(b'model: "provider/model#variant"', agent.read_bytes())
        self.cli("verify")
        agent.write_bytes(agent.read_bytes() + b"User edit\n")
        self.cli("sync-models", ok=False)
        self.cli("uninstall", ok=False)
        self.assertTrue(agent.read_bytes().endswith(b"User edit\n"))

    def test_prior_policy_refresh_uses_owned_uninstall_install_and_preserves_user_state(self):
        from unittest.mock import patch
        import contextlib
        import io

        # Represent the previously shipped managed block, not the new template.
        prior_routing = (manage.BEGIN + b"\nFor feature implementation (including tiny features), use the feature-delivery skill. "
                         b"Coordinator dispatches independent implementer and design-review peers; design agreement precedes coding. "
                         b"Delegated implementer/reviewer: obey your assigned role, do not recursively launch this workflow. "
                         b"Pure discussion/research does not trigger it. Preserve existing instructions and authorization.\n" + manage.END + b"\n")
        originals = {}
        for i, (_, relative) in enumerate(manage.RUNTIMES.values()):
            route = self.home / relative
            route.parent.mkdir(parents=True, exist_ok=True)
            original = b"User instructions\r\n" if i % 2 else b"User instructions without final newline"
            route.write_bytes(original)
            route.chmod(0o640)
            originals[route] = original
        _, profile_path = manage.paths(self.home)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile = manage.read_json(manage.SKILL / "profiles/default.json")
        profile["runtimes"]["opencode"]["reviewer"] = "provider/preserved-model#variant"
        profile_bytes = (json.dumps(profile, indent=4) + "\n").encode()
        profile_path.write_bytes(profile_bytes)
        profile_path.chmod(0o600)
        peer = self.home / ".local/state/feature-delivery/peers/retained.json"
        peer.parent.mkdir(parents=True, exist_ok=True)
        peer.write_bytes(b'{"reviewer_session":"preserved"}\n')
        peer_bytes = peer.read_bytes()
        # Previous generated wrappers are owned by manifest hashes, not current templates.
        previous_agent = b"---\nmode: subagent\n---\nPrior owned role instructions.\n"
        with patch.object(manage, "routing", return_value=prior_routing), \
             patch.object(manage, "agent_content", return_value=previous_agent), \
             contextlib.redirect_stdout(io.StringIO()):
            manage.install(self.home, list(manage.RUNTIMES), manage.SKILL / "profiles/default.json", False)
        agent = self.home / ".config/opencode/agents/feature-delivery-reviewer.md"
        self.assertEqual(agent.read_bytes(), previous_agent)
        self.assertEqual(self.cli("install")["result"], "already installed")
        self.assertEqual(agent.read_bytes(), previous_agent)
        for route in originals:
            self.assertIn(prior_routing, route.read_bytes())
        # User additions outside managed bytes must survive both operations.
        outside = b"User-added prefix\n"
        first = next(iter(originals))
        first.write_bytes(outside + first.read_bytes())
        self.cli("uninstall", "--dry-run")
        self.assertEqual(agent.read_bytes(), previous_agent)
        self.cli("uninstall")
        for route, original in originals.items():
            self.assertEqual(route.read_bytes(), (outside if route == first else b"") + original)
            self.assertEqual(route.stat().st_mode & 0o777, 0o640)
        self.assertEqual(profile_path.read_bytes(), profile_bytes)
        self.assertEqual(peer.read_bytes(), peer_bytes)
        self.cli("install")
        self.assertTrue(self.cli("verify")["ok"])
        for route, original in originals.items():
            self.assertEqual(route.read_bytes().count(manage.BEGIN), 1)
            self.assertEqual(route.read_bytes().count(manage.END), 1)
            self.assertIn(manage.routing(), route.read_bytes())
            self.assertNotIn(prior_routing, route.read_bytes())
            self.assertTrue(route.read_bytes().startswith((outside if route == first else b"") + original))
            self.assertEqual(route.stat().st_mode & 0o777, 0o640)
        self.assertEqual(agent.read_bytes(), manage.agent_content("reviewer", profile))
        self.assertIn(b'provider/preserved-model#variant', agent.read_bytes())
        self.assertEqual(profile_path.read_bytes(), profile_bytes)
        self.assertEqual(profile_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(peer.read_bytes(), peer_bytes)
        self.cli("uninstall")
        for route, original in originals.items():
            self.assertEqual(route.read_bytes(), (outside if route == first else b"") + original)

    def test_reinstall_snapshot_preserves_initial_unchanged_custom_profile(self):
        profile = manage.read_json(manage.SKILL / "profiles/default.json")
        profile["runtimes"]["opencode"]["reviewer"] = "provider/initial-custom-model"
        custom = (json.dumps(profile, indent=4) + "\n").encode()
        supplied = self.home / "supplied-profile.json"
        supplied.write_bytes(custom)
        supplied.chmod(0o600)
        self.cli("install", "--runtimes", "codex,opencode", "--profile", str(supplied))
        _, installed = manage.paths(self.home)
        self.assertEqual(installed.read_bytes(), custom)
        snapshot = self.home / "private-refresh-profile.json"
        snapshot.write_bytes(installed.read_bytes())
        snapshot.chmod(0o600)
        self.cli("uninstall")
        self.assertFalse(installed.exists(), "Unedited installer-created profiles are owned")
        self.cli("install", "--runtimes", "codex,opencode", "--profile", str(snapshot))
        self.assertEqual(installed.read_bytes(), custom)
        self.assertEqual(installed.stat().st_mode & 0o777, 0o600)
        agent = self.home / ".config/opencode/agents/feature-delivery-reviewer.md"
        self.assertEqual(agent.read_bytes(), manage.agent_content("reviewer", profile))
        self.assertTrue(self.cli("verify")["ok"])
        self.assertFalse((self.home / manage.RUNTIMES["pi"][0]).exists())
        self.assertFalse((self.home / manage.RUNTIMES["claude"][0]).exists())

    def test_write_failure_rolls_back(self):
        from unittest.mock import patch
        real = manage.atomic_write
        calls = 0

        def fail_once(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected write failure")
            return real(path, data)

        with patch.object(manage, "atomic_write", fail_once):
            with self.assertRaises(OSError):
                manage.install(self.home, list(manage.RUNTIMES), manage.SKILL / "profiles/default.json", False)
        for link, route in manage.RUNTIMES.values():
            self.assertFalse((self.home / link).is_symlink())
            self.assertFalse((self.home / route).exists())


if __name__ == "__main__":
    unittest.main()
