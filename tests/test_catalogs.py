import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / ".claude/skills/feature-delivery/scripts"
sys.path.insert(0, str(SCRIPTS))
import manage

# Representative safe rows observed from OpenCode v2.2.2 and Pi 1.4.0.
OPENCODE = "deepseek/deepseek-chat\nollama/deepseek-v4.1-flash:cloud\n"
PI = """provider  model                      context  max-out  thinking  images
deepseek  deepseek-chat              128K     8.2K     no        no
ollama    deepseek-v4.1-flash:cloud  1M       384K     yes       yes
"""


class CatalogTests(unittest.TestCase):
    def test_known_rows_and_unknown_formats(self):
        expected = {"deepseek/deepseek-chat", "ollama/deepseek-v4.1-flash:cloud"}
        self.assertEqual(manage.catalog_models("opencode", OPENCODE), expected)
        self.assertEqual(manage.catalog_models("pi", PI), expected)
        self.assertEqual(manage.catalog_models("pi", PI.splitlines()[0]), set())
        for runtime, output in (("opencode", ""), ("opencode", OPENCODE + "warning: changed format\n"),
                                ("pi", "new header\n"), ("pi", PI + "truncated row\n")):
            self.assertIsNone(manage.catalog_models(runtime, output))

    def doctor_output(self, outputs):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            _, profile_path = manage.paths(home)
            profile_path.parent.mkdir(parents=True)
            roles = {"implementer": "ollama/deepseek-v4.1-flash:cloud", "reviewer": "missing/model"}
            profile_path.write_text(json.dumps({"schema": 1, "runtimes": {
                "pi": roles,
                "opencode": {**roles, "implementer": roles["implementer"] + "#max"},
            }}))

            def run(args, **kwargs):
                if args[1] == "--version":
                    return SimpleNamespace(returncode=0, stdout="test-version")
                return SimpleNamespace(returncode=0, stdout=outputs[args[0]])

            output = io.StringIO()
            with patch.object(manage.shutil, "which", lambda runtime: runtime if runtime in outputs else None), patch.object(manage.subprocess, "run", run), contextlib.redirect_stdout(output):
                manage.doctor(home, True)
            return json.loads(output.getvalue())["runtimes"]

    def test_doctor_reports_known_base_models_without_asserting_variants(self):
        info = self.doctor_output({"opencode": OPENCODE, "pi": PI})
        for runtime in ("opencode", "pi"):
            self.assertEqual(info[runtime]["configured_models_seen"], {"implementer": True, "reviewer": False})
            self.assertEqual(info[runtime]["model_catalog_probe"], "ok")
        self.assertEqual(info["opencode"]["configured_variants_verified"], {"implementer": False})

    def test_doctor_unknown_catalog_is_unknown_not_absent(self):
        info = self.doctor_output({"opencode": "unexpected", "pi": "new format"})
        for runtime in ("opencode", "pi"):
            self.assertEqual(info[runtime]["configured_models_seen"], {"implementer": None, "reviewer": None})
            self.assertIn("unknown format", info[runtime]["model_catalog_probe"])


if __name__ == "__main__":
    unittest.main()
