import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DemoTests(unittest.TestCase):
    def test_module_demonstrates_isolation_and_rollback_without_leaving_data(self):
        expected = {
            "alpha": [{"id": "shared", "name": "Alpha Updated", "email": "a@example.test"}],
            "beta": [
                {"id": "beta-only", "name": "Beta Only", "email": "only@example.test"},
                {"id": "shared", "name": "Beta Demo", "email": "b@example.test"},
            ],
            "cross_tenant_read": None,
            "cross_tenant_update": "not_found",
            "malicious_import": "rejected",
            "conflicting_import": "rolled_back",
            "partial_contact": None,
        }
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as temporary:
            for execution in range(2):
                with self.subTest(execution=execution):
                    result = subprocess.run(
                        [sys.executable, "-W", "error", "-m", "tenant_crm"],
                        cwd=temporary, env=environment, capture_output=True,
                        text=True, encoding="utf-8", timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(json.loads(result.stdout), expected)
                    self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
