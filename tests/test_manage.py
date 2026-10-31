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
        route.write_bytes(route.read_bytes().replace(b"tiny", b"small"))
        self.cli("uninstall", ok=False)
        self.assertTrue((self.home / manage.RUNTIMES["codex"][0]).is_symlink())
        self.assertIn(b"small", route.read_bytes())

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
