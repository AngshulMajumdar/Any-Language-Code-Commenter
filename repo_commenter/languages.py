from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CommentStyle:
    line: Optional[str] = None
    block_start: Optional[str] = None
    block_end: Optional[str] = None

    def render(self, text: str) -> str:
        clean = " ".join(str(text).strip().split())
        if not clean:
            clean = "Explains the following code block."
        if self.line:
            return f"{self.line} {clean}"
        if self.block_start and self.block_end:
            return f"{self.block_start} {clean} {self.block_end}"
        raise ValueError("Invalid comment style")


@dataclass(frozen=True)
class LanguageSpec:
    name: str
    extensions: tuple[str, ...]
    style: CommentStyle
    aliases: tuple[str, ...] = ()


IGNORE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", "dist", "build", "target", ".next", ".nuxt",
    "venv", ".venv", "env", ".env", ".idea", ".vscode",
    "coverage", ".gradle", ".terraform", ".ipynb_checkpoints",
    "vendor", "third_party", ".cache", ".tox", ".eggs",
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".mkv",
    ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a", ".class", ".jar",
    ".pkl", ".joblib", ".npy", ".npz", ".pt", ".pth", ".onnx",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".db", ".sqlite", ".sqlite3",
}

LANGUAGE_SPECS: dict[str, LanguageSpec] = {}
EXT_TO_LANG: dict[str, str] = {}
SPECIAL_NAMES: dict[str, str] = {}


def register_language(
    name: str,
    extensions: tuple[str, ...] | list[str] = (),
    *,
    line_prefix: str | None = None,
    block_start: str | None = None,
    block_end: str | None = None,
    aliases: tuple[str, ...] | list[str] = (),
) -> None:
    if not line_prefix and not (block_start and block_end):
        raise ValueError(f"{name}: provide either line_prefix or block_start/block_end")
    spec = LanguageSpec(
        name=name,
        extensions=tuple(extensions),
        style=CommentStyle(line=line_prefix, block_start=block_start, block_end=block_end),
        aliases=tuple(aliases),
    )
    LANGUAGE_SPECS[name] = spec
    for ext in extensions:
        EXT_TO_LANG[ext.lower()] = name


def register_all_languages() -> None:
    LANGUAGE_SPECS.clear()
    EXT_TO_LANG.clear()
    SPECIAL_NAMES.clear()

    # Hash/comment-line families
    register_language("python", [".py"], line_prefix="#")
    register_language("ruby", [".rb"], line_prefix="#")
    register_language("perl", [".pl", ".pm"], line_prefix="#")
    register_language("shell", [".sh", ".bash", ".zsh", ".ksh"], line_prefix="#")
    register_language("powershell", [".ps1", ".psm1", ".psd1"], line_prefix="#")
    register_language("r", [".r", ".R"], line_prefix="#")
    register_language("yaml", [".yml", ".yaml"], line_prefix="#")
    register_language("toml", [".toml"], line_prefix="#")
    register_language("ini", [".ini", ".cfg", ".conf"], line_prefix="#")
    register_language("dockerfile", [], line_prefix="#")
    register_language("makefile", [], line_prefix="#")
    register_language("cmake", [".cmake"], line_prefix="#")

    # Percent-line family
    register_language("matlab", [".m"], line_prefix="%")

    # Slash-line families
    register_language("javascript", [".js", ".jsx", ".mjs", ".cjs"], line_prefix="//")
    register_language("typescript", [".ts", ".tsx"], line_prefix="//")
    register_language("java", [".java"], line_prefix="//")
    register_language("kotlin", [".kt", ".kts"], line_prefix="//")
    register_language("scala", [".scala", ".sc"], line_prefix="//")
    register_language("c", [".c", ".h"], line_prefix="//")
    register_language("cpp", [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"], line_prefix="//")
    register_language("go", [".go"], line_prefix="//")
    register_language("rust", [".rs"], line_prefix="//")
    register_language("swift", [".swift"], line_prefix="//")
    register_language("dart", [".dart"], line_prefix="//")
    register_language("csharp", [".cs"], line_prefix="//")
    register_language("php", [".php"], line_prefix="//")

    # Double-dash families
    register_language("sql", [".sql"], line_prefix="--")
    register_language("lua", [".lua"], line_prefix="--")
    register_language("haskell", [".hs", ".lhs"], line_prefix="--")

    # Block-only markup/style families
    register_language("html", [".html", ".htm"], block_start="<!--", block_end="-->")
    register_language("xml", [".xml"], block_start="<!--", block_end="-->")
    register_language("css", [".css"], block_start="/*", block_end="*/")

    SPECIAL_NAMES.update({
        "dockerfile": "dockerfile",
        "containerfile": "dockerfile",
        "makefile": "makefile",
        "gnumakefile": "makefile",
        "cmakelists.txt": "cmake",
    })


def detect_language(path: str | Path) -> str | None:
    p = Path(path)
    name = p.name.lower()
    if name in SPECIAL_NAMES:
        return SPECIAL_NAMES[name]
    return EXT_TO_LANG.get(p.suffix.lower())


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


register_all_languages()
