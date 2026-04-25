from __future__ import annotations

import difflib
import json
import re
from typing import Any


def parse_json_array(text: str) -> list[dict]:
    if not text:
        return []
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, list) else []
    except Exception:
        pass
    match = re.search(r"\[.*\]", text, flags=re.S)
    if not match:
        return []
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, list) else []
    except Exception:
        return []


def parse_review(text: str) -> str:
    if not text:
        return "reject"
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            return str(obj.get("decision", "reject")).lower()
        except Exception:
            pass
    lowered = text.lower()
    return "accept" if "accept" in lowered and "reject" not in lowered else "reject"


def clean_plan(plan: list[Any], num_lines: int) -> list[dict]:
    cleaned: list[dict] = []
    seen: set[tuple[int, str]] = set()
    for item in plan:
        if not isinstance(item, dict):
            continue
        try:
            before_line = int(item.get("before_line"))
        except Exception:
            continue
        comment = " ".join(str(item.get("comment", "")).strip().split())
        if not comment or before_line < 1 or before_line > max(1, num_lines):
            continue
        if any(token in comment for token in ["\n", "```", "/*", "*/", "<!--", "-->"]):
            continue
        key = (before_line, comment.lower())
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"before_line": before_line, "comment": comment[:180]})
        if len(cleaned) >= 20:
            break
    return sorted(cleaned, key=lambda x: x["before_line"])


def fallback_plan(packet: dict, original: str, max_comments: int = 8) -> list[dict]:
    lines = original.splitlines()
    patterns = [
        (r"^\s*(class|interface|enum|record|struct|trait)\s+", "Defines the main type or abstraction used by this file."),
        (r"^\s*(public\s+|private\s+|protected\s+|static\s+)?(def|function|func|fn|sub)\s+", "Defines a function that implements part of the repository logic."),
        (r"^\s*(if|for|while|switch|case)\b", "Handles a control-flow branch or iteration used by the algorithm."),
        (r"^\s*(try|catch|except|finally)\b", "Handles exceptional cases while keeping the workflow safe."),
        (r"^\s*(SELECT|CREATE|INSERT|UPDATE|DELETE|WITH)\b", "Defines a database operation used by the application."),
        (r"^\s*(FROM|RUN|COPY|CMD|ENTRYPOINT)\b", "Configures one step of the container build or runtime setup."),
    ]
    plan: list[dict] = []
    used_lines: set[int] = set()
    for idx, line in enumerate(lines, start=1):
        for pat, comment in patterns:
            if re.search(pat, line, flags=re.I):
                if idx not in used_lines:
                    plan.append({"before_line": idx, "comment": comment})
                    used_lines.add(idx)
                break
        if len(plan) >= max_comments:
            break
    if not plan and lines:
        plan.append({"before_line": 1, "comment": "Provides the implementation for this source file."})
    return clean_plan(plan, packet.get("num_lines", len(lines) or 1))


def render_comment(style: dict, text: str) -> str:
    comment = " ".join(str(text).strip().split())
    if style.get("line"):
        return f"{style['line']} {comment}"
    if style.get("block_start") and style.get("block_end"):
        return f"{style['block_start']} {comment} {style['block_end']}"
    raise ValueError("Invalid comment style")


def apply_plan(original: str, plan: list[dict], style: dict) -> tuple[str, list[dict]]:
    lines = original.splitlines(keepends=True)
    inserts_by_line: dict[int, list[str]] = {}
    for item in plan:
        before = int(item["before_line"])
        inserts_by_line.setdefault(before, []).append(render_comment(style, item["comment"]))

    output: list[str] = []
    applied: list[dict] = []
    for idx, line in enumerate(lines, start=1):
        for comment in inserts_by_line.get(idx, []):
            indent = re.match(r"^\s*", line).group(0)
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            output.append(indent + comment + newline)
            applied.append({"before_line": idx, "comment": comment})
        output.append(line)
    if not lines and inserts_by_line.get(1):
        for comment in inserts_by_line[1]:
            output.append(comment + "\n")
            applied.append({"before_line": 1, "comment": comment})
    return "".join(output), applied


def _strip_inserted_comments(candidate: str, style: dict) -> str:
    out: list[str] = []
    line_prefix = style.get("line")
    block_start = style.get("block_start")
    block_end = style.get("block_end")
    for line in candidate.splitlines(keepends=True):
        stripped = line.strip()
        if line_prefix and stripped.startswith(line_prefix):
            continue
        if block_start and block_end and stripped.startswith(block_start) and stripped.endswith(block_end):
            continue
        out.append(line)
    return "".join(out)


def safety_check(original: str, candidate: str, style: dict) -> tuple[bool, str]:
    restored = _strip_inserted_comments(candidate, style)
    if restored == original:
        return True, "only_comment_insertions"
    diff = "\n".join(difflib.unified_diff(original.splitlines(), restored.splitlines(), lineterm=""))
    return False, "non_comment_change_detected: " + diff[:600]
