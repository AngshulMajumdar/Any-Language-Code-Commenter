from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from .languages import BINARY_EXTS, LANGUAGE_SPECS, detect_language, should_ignore


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return True
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\0" in chunk


def read_text_safe(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def route_files(input_repo: Path, max_file_bytes: int = 250_000) -> list[dict]:
    routes: list[dict] = []
    for p in sorted(input_repo.rglob("*")):
        if not p.is_file() or should_ignore(p.relative_to(input_repo)):
            continue
        rel = p.relative_to(input_repo).as_posix()
        lang = detect_language(p)
        if is_binary(p):
            route = "copy_binary"
        elif lang is None:
            route = "copy_unsupported"
        elif p.stat().st_size > max_file_bytes:
            route = "copy_too_large"
        else:
            route = "comment"
        routes.append({
            "path": rel,
            "language": lang,
            "route": route,
            "size_bytes": p.stat().st_size,
        })
    return routes


def make_prompt_packet(input_repo: Path, route: dict, max_preview_lines: int = 240) -> dict | None:
    if route["route"] != "comment" or not route.get("language"):
        return None
    src = input_repo / route["path"]
    text = read_text_safe(src)
    lines = text.splitlines()
    preview = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines[:max_preview_lines]))
    spec = LANGUAGE_SPECS[route["language"]]
    style = spec.style
    return {
        "path": route["path"],
        "language": route["language"],
        "num_lines": max(1, len(lines)),
        "source_preview": preview,
        "comment_style": asdict(style),
    }


def write_routing_artifacts(input_repo: Path, pipeline_dir: Path, routes: list[dict]) -> None:
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    (pipeline_dir / "file_routes.json").write_text(json.dumps({"files": routes}, indent=2), encoding="utf-8")
    with (pipeline_dir / "file_prompt_packets.jsonl").open("w", encoding="utf-8") as f:
        for route in routes:
            packet = make_prompt_packet(input_repo, route)
            if packet:
                f.write(json.dumps(packet, ensure_ascii=False) + "\n")
