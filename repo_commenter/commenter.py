from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re
import shutil
import subprocess
import zipfile

from .llm import LLMClient, MockLLMClient
from .plans import apply_plan, clean_plan, fallback_plan, parse_json_array, parse_review, safety_check
from .prompts import generator_prompt, reviewer_prompt
from .router import make_prompt_packet, route_files, write_routing_artifacts


DEFAULT_GEN_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
DEFAULT_REV_MODEL = "deepseek-ai/deepseek-coder-1.3b-instruct"


def clone_repo(github_url: str, input_repo: Path) -> None:
    if input_repo.exists():
        shutil.rmtree(input_repo)
    cmd = ["git", "clone", "--depth", "1", github_url, str(input_repo)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def copy_tree_without_git(src_root: Path, dst_root: Path) -> None:
    for src in src_root.rglob("*"):
        if ".git" in src.parts or not src.is_file():
            continue
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def comment_repository(
    input_repo: Path,
    out_repo: Path,
    pipeline_dir: Path,
    generator: LLMClient,
    reviewer: LLMClient,
    *,
    use_fallback: bool = True,
    max_file_bytes: int = 250_000,
) -> list[dict]:
    if not input_repo.exists():
        raise FileNotFoundError(f"Input repo not found: {input_repo}")
    if out_repo.exists():
        shutil.rmtree(out_repo)
    out_repo.mkdir(parents=True, exist_ok=True)
    report_dir = pipeline_dir / "reports"
    raw_dir = pipeline_dir / "llm_raw"
    report_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    routes = route_files(input_repo, max_file_bytes=max_file_bytes)
    write_routing_artifacts(input_repo, pipeline_dir, routes)

    report: list[dict] = []
    for idx, route in enumerate(routes, start=1):
        rel = route["path"]
        src = input_repo / rel
        dst = out_repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if route["route"] != "comment":
            shutil.copy2(src, dst)
            report.append({"path": rel, "status": route["route"], "language": route.get("language")})
            continue

        try:
            packet = make_prompt_packet(input_repo, route)
            if not packet:
                shutil.copy2(src, dst)
                report.append({"path": rel, "status": "no_packet", "language": route.get("language")})
                continue

            original = src.read_text(encoding="utf-8", errors="replace")
            style = packet["comment_style"]
            gen_raw = generator.generate(generator_prompt(packet), max_new_tokens=320)
            plan = clean_plan(parse_json_array(gen_raw), packet["num_lines"])

            rev_raw = ""
            decision = "reject"
            used_fallback = False
            if plan:
                rev_raw = reviewer.generate(reviewer_prompt(packet, plan), max_new_tokens=96)
                decision = parse_review(rev_raw)

            if (not plan or decision != "accept") and use_fallback:
                fallback = fallback_plan(packet, original)
                if fallback:
                    plan = clean_plan(fallback, packet["num_lines"])
                    decision = "accept"
                    used_fallback = True

            safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", rel)[:160]
            (raw_dir / f"{safe_name}.generator.txt").write_text(gen_raw, encoding="utf-8")
            (raw_dir / f"{safe_name}.reviewer.txt").write_text(rev_raw, encoding="utf-8")

            if decision != "accept" or not plan:
                shutil.copy2(src, dst)
                report.append({"path": rel, "language": packet["language"], "status": "not_commented", "plan_items": len(plan), "used_fallback": used_fallback})
                continue

            candidate, applied = apply_plan(original, plan, style)
            ok, reason = safety_check(original, candidate, style)
            if ok:
                dst.write_text(candidate, encoding="utf-8")
                report.append({"path": rel, "language": packet["language"], "status": "commented", "plan_items": len(plan), "comments_applied": len(applied), "used_fallback": used_fallback})
            else:
                shutil.copy2(src, dst)
                report.append({"path": rel, "language": packet["language"], "status": "safety_rejected", "reason": reason, "plan_items": len(plan), "used_fallback": used_fallback})
        except Exception as exc:
            shutil.copy2(src, dst)
            report.append({"path": rel, "language": route.get("language"), "status": "error", "error": repr(exc)})

    (report_dir / "comment_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = Counter(item["status"] for item in report)
    (report_dir / "summary.json").write_text(json.dumps(dict(summary), indent=2), encoding="utf-8")
    return report


def zip_output(out_repo: Path, pipeline_dir: Path, zip_path: Path) -> Path:
    if zip_path.exists():
        zip_path.unlink()
    missing = []
    if not out_repo.exists():
        raise FileNotFoundError(f"Output repo not found: {out_repo}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in out_repo.rglob("*"):
            if p.is_file():
                zf.write(p, (Path("commented_repo") / p.relative_to(out_repo)).as_posix())
        report_dir = pipeline_dir / "reports"
        if report_dir.exists():
            for p in report_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, (Path("pipeline_data") / "reports" / p.relative_to(report_dir)).as_posix())
    return zip_path


def run_local_pipeline(
    input_repo: Path,
    out_repo: Path,
    pipeline_dir: Path,
    zip_path: Path,
    generator: LLMClient | None = None,
    reviewer: LLMClient | None = None,
) -> tuple[list[dict], Path]:
    generator = generator or MockLLMClient("generator")
    reviewer = reviewer or MockLLMClient("reviewer")
    report = comment_repository(input_repo, out_repo, pipeline_dir, generator, reviewer)
    return report, zip_output(out_repo, pipeline_dir, zip_path)
