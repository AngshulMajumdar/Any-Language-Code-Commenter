import tempfile
import unittest
import zipfile
from pathlib import Path

from repo_commenter.commenter import run_local_pipeline


class PipelineTests(unittest.TestCase):
    def test_mock_pipeline_creates_commented_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            (repo / "main.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            (repo / "algo.m").write_text("function y=f(x)\ny=x+1;\nend\n", encoding="utf-8")
            (repo / "image.bin").write_bytes(b"\x00\x01")
            out = root / "out"
            pipe = root / "pipe"
            zip_path = root / "out.zip"
            report, zp = run_local_pipeline(repo, out, pipe, zip_path)
            self.assertTrue(zp.exists())
            statuses = {r["path"]: r["status"] for r in report}
            self.assertEqual(statuses["main.py"], "commented")
            self.assertEqual(statuses["algo.m"], "commented")
            self.assertIn("# Provides", (out / "main.py").read_text(encoding="utf-8"))
            self.assertIn("% Provides", (out / "algo.m").read_text(encoding="utf-8"))
            with zipfile.ZipFile(zp) as zf:
                names = set(zf.namelist())
            self.assertIn("commented_repo/main.py", names)
            self.assertIn("pipeline_data/reports/comment_report.json", names)


if __name__ == "__main__":
    unittest.main()
