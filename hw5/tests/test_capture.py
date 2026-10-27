"""Regression checks for preserved evidence and truthful capture behavior."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import capture_live_evidence as capture


class CaptureTests(unittest.TestCase):
    def tearDown(self):
        capture.STATE = None

    def test_multiple_runs_preserve_reference_and_each_other(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "attack-01-rerun.json"
            reference.write_text("reference evidence")
            first = capture.save_run({"stdout": "first response"}, root / "runs")
            second = capture.save_run({"stdout": "second response"}, root / "runs")
            self.assertNotEqual(first["run_id"], second["run_id"])
            for record in (first, second):
                folder = root / "runs" / record["run_id"]
                self.assertEqual((folder / "stdout.txt").read_text(), record["stdout"])
                self.assertEqual(json.loads((folder / "run.json").read_text()), record)
            self.assertEqual(reference.read_text(), "reference evidence")

    def test_fixed_target_command_and_model_are_recorded(self):
        completion = subprocess.CompletedProcess(capture.COMMAND, 0, stdout="You are Incident Compass\n")
        with patch.object(capture.shutil, "which", return_value="/example/uv"), patch.object(capture.subprocess, "run", return_value=completion) as request, patch.dict(capture.os.environ, {"GOOGLE_MODEL": "gemini-2.5-flash"}):
            record = capture.run_attack()
        self.assertEqual(request.call_args.args[0], capture.COMMAND)
        self.assertEqual(request.call_args.kwargs["cwd"], capture.TARGET)
        self.assertEqual(request.call_args.kwargs["env"]["GOOGLE_MODEL"], record["model"])
        self.assertTrue(record["source_unchanged"])
        self.assertEqual(record["stdout"], completion.stdout)
        self.assertEqual(record["tool_result_lines"], 0)

    def test_failed_request_is_not_a_successful_capture(self):
        completion = subprocess.CompletedProcess(capture.COMMAND, 1, stdout="")
        with patch.object(capture.shutil, "which", return_value="/example/uv"), patch.object(capture.subprocess, "run", return_value=completion):
            with self.assertRaises(RuntimeError):
                capture.run_attack()

    def test_unavailable_runtime_is_reported_before_request(self):
        with patch.object(capture.shutil, "which", return_value=None), patch.object(capture.subprocess, "run") as request:
            with self.assertRaises(RuntimeError):
                capture.run_attack()
            request.assert_not_called()

    def test_metadata_view_accepts_returned_order_and_escapes_output(self):
        capture.STATE = {"stdout": 'def Terminal(\n command: str\n)\n<script>bad()</script>\ndef search_policy(\n query: str\n)\ndef triage_incident(\n facts: bool\n)\n```', "finished_utc": "audit", "exit_code": 0, "tool_result_lines": 0, "model": "gemini-2.5-flash"}
        rendered = capture.render("tools").decode()
        self.assertIn("Returned tool metadata", rendered)
        self.assertIn("&lt;script&gt;bad()&lt;/script&gt;", rendered)
        self.assertNotIn("<script>", rendered)


if __name__ == "__main__":
    unittest.main()
