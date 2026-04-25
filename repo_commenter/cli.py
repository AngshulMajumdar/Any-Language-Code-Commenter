from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import shutil

from .commenter import DEFAULT_GEN_MODEL, DEFAULT_REV_MODEL, clone_repo, comment_repository, zip_output
from .llm import MockLLMClient, TransformersLLMClient


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Safely add explanatory comments to a GitHub/local repository using a generator LLM and reviewer LLM.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo-url", help="GitHub repository URL to clone")
    src.add_argument("--input-repo", type=Path, help="Existing local repository path")
    p.add_argument("--work-dir", type=Path, default=Path("work"), help="Working directory for clone, output, reports, and zip")
    p.add_argument("--output-zip", type=Path, default=None, help="Path for final zip. Defaults to <work-dir>/commented_repo_full.zip")
    p.add_argument("--generator-model", default=DEFAULT_GEN_MODEL)
    p.add_argument("--reviewer-model", default=DEFAULT_REV_MODEL)
    p.add_argument("--mock", action="store_true", help="Use deterministic mock LLMs. Useful for smoke tests and CI.")
    p.add_argument("--no-4bit", action="store_true", help="Disable 4-bit quantized loading for Transformers models.")
    p.add_argument("--max-file-bytes", type=int, default=250_000)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    work = args.work_dir
    input_repo = work / "input_repo"
    out_repo = work / "commented_repo"
    pipeline_dir = work / "pipeline_data"
    zip_path = args.output_zip or work / "commented_repo_full.zip"
    work.mkdir(parents=True, exist_ok=True)

    if args.repo_url:
        print("Cloning repository...")
        clone_repo(args.repo_url, input_repo)
    else:
        if input_repo.exists():
            shutil.rmtree(input_repo)
        shutil.copytree(args.input_repo, input_repo, ignore=shutil.ignore_patterns(".git"))

    if args.mock:
        generator = MockLLMClient("generator")
        reviewer = MockLLMClient("reviewer")
    else:
        print("Loading generator LLM once...")
        generator = TransformersLLMClient(args.generator_model, load_in_4bit=not args.no_4bit)
        print("Loading reviewer LLM once...")
        reviewer = TransformersLLMClient(args.reviewer_model, load_in_4bit=not args.no_4bit)

    print("Commenting repository...")
    report = comment_repository(input_repo, out_repo, pipeline_dir, generator, reviewer, max_file_bytes=args.max_file_bytes)
    zip_output(out_repo, pipeline_dir, zip_path)
    print("Summary:", dict(Counter(item["status"] for item in report)))
    print("Output repo:", out_repo)
    print("Output zip:", zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
