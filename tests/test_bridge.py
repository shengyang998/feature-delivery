import fcntl
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / ".claude/skills/feature-delivery/scripts"
sys.path.insert(0, str(SCRIPTS))
import bridge

FAKE = r'''
import json, pathlib, sys, time
args = sys.argv[1:]
if "--version" in args:
    print("1.4.0-fake"); sys.exit(0)
if "--help" in args:
    print("--session-id --session-dir --mode --append-system-prompt"); sys.exit(0)
if "--no-extensions" in args: sys.exit(9)
prompt = sys.stdin.read().strip()
if prompt == "fail": sys.exit(7)
if prompt == "slow": time.sleep(5)
if prompt.startswith("wait "):
    pathlib.Path(prompt[5:]).write_text(str(__import__("os").getpid()))
    time.sleep(20)
if prompt == "malformed": print("not json"); sys.exit(0)
session = args[args.index("--session-id") + 1]
directory = pathlib.Path(args[args.index("--session-dir") + 1])
directory.mkdir(parents=True, exist_ok=True)
memory = directory / (session + ".txt")
prior = memory.read_text() if memory.exists() else ""
if prompt.startswith("remember "): memory.write_text(prompt[9:])
response = (prior or "(no memory)") if prompt == "recall" else prompt
print(json.dumps({"type":"session", "id":session, "version":3}))
print(json.dumps({"type":"message_end", "message":{"role":"assistant", "content":[{"type":"text", "text":response}], "stopReason":"stop", "model":"model", "provider":"fake"}}))
print(json.dumps({"type":"agent_settled", "aborted":False}))
'''


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fake = self.root / "pi"
        self.fake.write_text("#!" + sys.executable + "\n" + FAKE)
        self.fake.chmod(0o755)
        self.cwd = self.root / "project"
        self.cwd.mkdir()
        self.state = self.root / "state"
        self.profile = self.root / "default-profile.json"
        self.profile.write_bytes((bridge.SKILL / "profiles/default.json").read_bytes())

    def cli(self, prompt, role="reviewer", task="feature-one", extra=(), ok=True):
        args = [sys.executable, str(SCRIPTS / "bridge.py"), "--pi", str(self.fake), "--task", task,
                "--role", role, "--cwd", str(self.cwd), "--state-dir", str(self.state),
                "--profile", str(self.profile), *extra]
        result = subprocess.run(args, input=prompt, capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result

    def test_persistent_context_and_independent_roles_tasks(self):
        first = self.cli("remember private-marker")
        second = self.cli("recall")
        implementer = self.cli("recall", role="implementer")
        another = self.cli("recall", task="feature-two")
        self.assertFalse(first["resumed"])
        self.assertTrue(second["resumed"])
        self.assertEqual(first["session"], second["session"])
        self.assertEqual(second["response"], "private-marker")
        self.assertNotEqual(implementer["session"], second["session"])
        self.assertNotEqual(another["session"], second["session"])
        self.assertEqual(implementer["response"], "(no memory)")

    def test_errors_release_lock_for_resume(self):
        for prompt in ("fail", "malformed", "slow"):
            self.cli(prompt, extra=("--timeout", "0.05"), ok=False)
            self.assertEqual(self.cli("healthy")["response"], "healthy")

    def test_concurrent_peer_rejected(self):
        peer = self.state / "feature-one/reviewer"
        peer.mkdir(parents=True)
        with (peer / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn("already running", self.cli("hello", ok=False).stderr)

    def test_route_changes_rejected(self):
        self.cli("hello", extra=("--parent-model", "provider/model"))
        self.assertIn("cwd/model changed", self.cli("hello", ok=False).stderr)
        second_cwd = self.root / "second"
        second_cwd.mkdir()
        self.cwd = second_cwd
        self.cli("hello", extra=("--parent-model", "provider/model"), ok=False)

    def test_sigterm_kills_child_and_releases_peer(self):
        pid_file = self.root / "child.pid"
        args = [sys.executable, str(SCRIPTS / "bridge.py"), "--pi", str(self.fake), "--task", "feature-one",
                "--role", "reviewer", "--cwd", str(self.cwd), "--state-dir", str(self.state),
                "--profile", str(self.profile)]
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        process.stdin.write("wait " + str(pid_file))
        process.stdin.close()
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(pid_file.exists())
        child_pid = int(pid_file.read_text())
        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(timeout=5), 130)
        process.stdout.close()
        process.stderr.close()
        with self.assertRaises(ProcessLookupError):
            os.kill(child_pid, 0)
        self.assertEqual(self.cli("healthy")["response"], "healthy")

    def test_model_profile_selection_and_bad_task(self):
        profile = json.loads((bridge.SKILL / "profiles/default.json").read_text())
        profile["runtimes"]["pi"]["implementer"] = "provider/explicit"
        path = self.root / "profile.json"
        path.write_text(json.dumps(profile))
        result = self.cli("hello", role="implementer", extra=("--profile", str(path)))
        self.assertEqual(result["requested_model"], "provider/explicit")
        self.assertEqual(result["selection"], "profile")
        self.cli("hello", task="../escape", ok=False)
        self.assertIn("Explicit profile", self.cli("hello", extra=("--profile", str(self.root / "missing")), ok=False).stderr)

    def test_version_flags_and_incomplete_error_events_fail(self):
        self.fake.write_text("#!" + sys.executable + '\nprint("old unsupported")\n')
        self.assertIn("Unsupported Pi CLI", self.cli("hello", ok=False).stderr)
        with self.assertRaises(ValueError):
            bridge.parse_events('{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"partial"}]}}')
        with self.assertRaises(ValueError):
            bridge.parse_events('{"type":"message_end","message":{"role":"assistant","stopReason":"error","content":[]}}\n{"type":"agent_settled","aborted":false}')


if __name__ == "__main__":
    unittest.main()
