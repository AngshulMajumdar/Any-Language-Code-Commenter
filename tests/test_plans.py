import unittest

from repo_commenter.plans import apply_plan, clean_plan, fallback_plan, safety_check


class PlanTests(unittest.TestCase):
    def test_apply_python_comment_is_safe(self):
        original = "def f(x):\n    return x + 1\n"
        style = {"line": "#", "block_start": None, "block_end": None}
        candidate, applied = apply_plan(original, [{"before_line": 1, "comment": "Defines the function."}], style)
        self.assertTrue(applied)
        ok, reason = safety_check(original, candidate, style)
        self.assertTrue(ok, reason)

    def test_apply_matlab_comment_is_safe(self):
        original = "function y = f(x)\ny = x + 1;\nend\n"
        style = {"line": "%", "block_start": None, "block_end": None}
        candidate, applied = apply_plan(original, [{"before_line": 1, "comment": "Defines the function."}], style)
        self.assertTrue(candidate.startswith("% Defines"))
        ok, reason = safety_check(original, candidate, style)
        self.assertTrue(ok, reason)

    def test_block_comment_html_is_safe(self):
        original = "<main>\n</main>\n"
        style = {"line": None, "block_start": "<!--", "block_end": "-->"}
        candidate, _ = apply_plan(original, [{"before_line": 1, "comment": "Main page section."}], style)
        self.assertIn("<!-- Main page section. -->", candidate)
        ok, reason = safety_check(original, candidate, style)
        self.assertTrue(ok, reason)

    def test_safety_rejects_code_edit(self):
        original = "x = 1\n"
        candidate = "# comment\nx = 2\n"
        ok, _ = safety_check(original, candidate, {"line": "#"})
        self.assertFalse(ok)

    def test_clean_plan_rejects_bad_items(self):
        plan = clean_plan([
            {"before_line": 1, "comment": "ok"},
            {"before_line": 999, "comment": "bad"},
            {"before_line": 2, "comment": "``` code"},
        ], num_lines=3)
        self.assertEqual(len(plan), 1)

    def test_fallback_returns_plan(self):
        packet = {"language": "python", "num_lines": 2, "comment_style": {"line": "#"}}
        plan = fallback_plan(packet, "def f():\n    pass\n")
        self.assertTrue(plan)


if __name__ == "__main__":
    unittest.main()
