# Code Commenter Pro

A professional, multi-language repository commenter built from the original Colab notebook.

It clones or reads a repository, detects supported source files, asks a **generator LLM** to propose sparse explanatory comments, asks a **reviewer LLM** to accept or reject the plan, and applies only safe comment-line insertions. Unsupported, binary, and oversized files are copied unchanged.

## Why this repo exists

The notebook version was useful, but it was not a clean GitHub project. This repository separates the system into reusable modules, tests the routing and safety logic, and provides a CLI that can be run locally, in Colab, Kaggle, or on a GPU machine.

## Supported languages

Python, MATLAB, JavaScript, TypeScript, Java, Kotlin, Scala, C, C++, Go, Rust, Swift, Dart, C#, PHP, Ruby, Perl, Shell, PowerShell, R, SQL, Lua, Haskell, HTML, XML, CSS, YAML, TOML, INI/CFG, Dockerfile, Makefile, and CMake.

The language registry is automatic. You do **not** run one block per language.

## Safety model

The insertion engine is intentionally conservative.

1. The generator returns JSON only: `[{"before_line": 12, "comment": "..."}]`.
2. The reviewer accepts or rejects the plan.
3. The engine inserts only comments using the detected language's comment syntax.
4. A safety check strips inserted comments and verifies that the original code is exactly recovered.
5. If the check fails, the original file is copied unchanged.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For real LLM inference:

```bash
pip install -e ".[llm]"
```

On Colab/T4, the default models are small enough to run with 4-bit loading:

- Generator: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- Reviewer: `deepseek-ai/deepseek-coder-1.3b-instruct`

## Quick smoke test without model downloads

```bash
code-commenter --input-repo examples/sample_repo --work-dir work --mock
```

This uses deterministic mock LLMs and verifies the whole routing/commenting/zipping pipeline.

## Real usage with a GitHub repo

```bash
code-commenter \
  --repo-url https://github.com/OWNER/REPO \
  --work-dir work
```

Output:

```text
work/commented_repo/
work/commented_repo_full.zip
work/pipeline_data/reports/comment_report.json
work/pipeline_data/reports/summary.json
```

## Local repo usage

```bash
code-commenter --input-repo /path/to/repo --work-dir work
```

## Colab usage

Use the CLI instead of a long fragile notebook:

```python
!git clone <this repo>
%cd code-commenter-pro
!pip install -e ".[llm]"
!code-commenter --repo-url https://github.com/OWNER/REPO --work-dir /content/code_commenter_work
```

For repeated repos in the same runtime, keep the Python process/model loading pattern if you wrap the package in a script. The CLI is clean and reproducible; a notebook wrapper can import `TransformersLLMClient` once and call `comment_repository` repeatedly.

## Development

Run tests:

```bash
python -m unittest discover -s tests -v
```

The tests avoid LLM downloads. They check language detection, routing, comment insertion, safety rejection, and zip creation.
