from __future__ import annotations


def comment_syntax_text(style: dict) -> str:
    if style.get("line"):
        return f"line comments using {style['line']}"
    return f"single-line block comments using {style['block_start']} ... {style['block_end']}"


def generator_prompt(packet: dict) -> str:
    syntax = comment_syntax_text(packet["comment_style"])
    return f"""
You are the COMMENT GENERATOR for a {packet['language']} source file.

Return JSON only, with this exact format:
[
  {{"before_line": 12, "comment": "Explains what this block does"}}
]

Rules:
- Maximum 20 comments.
- Use only existing line numbers from 1 to {packet['num_lines']}.
- Do not return code.
- Do not modify code.
- Add sparse useful comments only.
- Avoid obvious comments.
- Comments must be short, one sentence, and language-neutral text only.
- The insertion engine will convert comments into {syntax}; do not include comment delimiters yourself.
- Focus on purpose, APIs, control flow, important functions/classes, data structures, configuration, or non-obvious logic.

File: {packet['path']}
Language: {packet['language']}

Source with line numbers:
{packet['source_preview']}
""".strip()


def reviewer_prompt(packet: dict, plan: list[dict]) -> str:
    return f"""
You are the COMMENT REVIEWER.

Review this JSON comment plan.

Return JSON only:
{{"decision": "accept" or "reject", "reason": "short reason"}}

Accept only if:
- It is a list of comment insertions.
- There are at most 20 comments.
- before_line values are integers between 1 and {packet['num_lines']}.
- Comments are useful and short.
- The plan contains no code edits and no comment delimiters.

File: {packet['path']}
Language: {packet['language']}

Plan:
{plan}
""".strip()
