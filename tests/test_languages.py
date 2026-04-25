import unittest

from repo_commenter.languages import LANGUAGE_SPECS, detect_language


class LanguageTests(unittest.TestCase):
    def test_core_language_detection(self):
        cases = {
            "main.py": "python",
            "algo.m": "matlab",
            "app.js": "javascript",
            "app.tsx": "typescript",
            "Main.java": "java",
            "main.cpp": "cpp",
            "query.sql": "sql",
            "index.html": "html",
            "style.css": "css",
            "Dockerfile": "dockerfile",
            "Makefile": "makefile",
            "CMakeLists.txt": "cmake",
        }
        for path, expected in cases.items():
            self.assertEqual(detect_language(path), expected, path)

    def test_many_languages_registered(self):
        self.assertGreaterEqual(len(LANGUAGE_SPECS), 30)
        self.assertEqual(LANGUAGE_SPECS["matlab"].style.line, "%")
        self.assertEqual(LANGUAGE_SPECS["python"].style.line, "#")
        self.assertEqual(LANGUAGE_SPECS["html"].style.block_start, "<!--")


if __name__ == "__main__":
    unittest.main()
