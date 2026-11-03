#!/usr/bin/env python3
"""Round-trip content.json prose fields through a plain markdown file.

Usage:
    python3 textfields.py extract content.json 01_input.txt
    python3 textfields.py apply   content.json final.md
    python3 textfields.py selftest

extract writes every body / analogy / explanation as a block headed by
`## [path] context`. The humanize-korean pipeline keeps headings intact,
so apply can map the polished blocks back by path. A block whose `code`,
fenced code or callout markers changed is rejected and the original kept.
"""
import json
import re
import sys
from pathlib import Path

HEAD_RE = re.compile(r"^## \[((?:sections|quiz)\.\d+\.(?:body|analogy|explanation))\][^\n]*$", re.M)
PROTECTED_RE = re.compile(r"```.*?```|`[^`\n]+`|^:::\w*$", re.S | re.M)


def fields(data):
    """Yield (path, context, text) for every polishable field."""
    for i, sec in enumerate(data["sections"]):
        for key in ("body", "analogy"):
            if key in sec:
                yield f"sections.{i}.{key}", sec["title"], sec[key]
    for i, q in enumerate(data["quiz"]):
        yield f"quiz.{i}.explanation", f"Q{i + 1}. {q['q']}", q["explanation"]


def extract(data) -> str:
    return "\n\n".join(f"## [{p}] {ctx}\n\n{text.strip()}" for p, ctx, text in fields(data)) + "\n"


def parse(md: str) -> dict:
    md = md.split("<!-- HUMANIZE-SUMMARY", 1)[0]
    parts = HEAD_RE.split(md)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def apply(data, md: str) -> list:
    """Write polished text into data in place. Returns warnings."""
    polished, warns = parse(md), []
    for path, _, old in fields(data):
        new = polished.get(path)
        if not new:
            warns.append(f"{path}: 윤문본에 없음 - 원문 유지")
        elif PROTECTED_RE.findall(new) != PROTECTED_RE.findall(old):
            warns.append(f"{path}: 코드/콜아웃 표기가 바뀜 - 원문 유지")
        else:
            kind, idx, key = path.split(".")
            data[kind][int(idx)][key] = new
    return warns


def selftest():
    data = {"sections": [{"title": "T", "body": "a `x` b\n\n:::warning\nw\n:::", "analogy": "c"}],
            "quiz": [{"q": "Q", "explanation": "e"}]}
    md = extract(data).replace("a `x` b", "A `x` B").replace("\nc\n", "\nC\n")
    md = md.replace("\ne\n", "\n`y` e\n") + "\n<!-- HUMANIZE-SUMMARY\nx\n-->\n"
    warns = apply(data, md)
    assert data["sections"][0]["body"] == "A `x` B\n\n:::warning\nw\n:::", data
    assert data["sections"][0]["analogy"] == "C", data
    assert data["quiz"][0]["explanation"] == "e" and len(warns) == 1, warns
    print("[ok] selftest")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "selftest":
        return selftest()
    if cmd not in ("extract", "apply") or len(sys.argv) != 4:
        sys.exit(__doc__)
    content, text = Path(sys.argv[2]), Path(sys.argv[3])
    data = json.loads(content.read_text(encoding="utf-8"))
    if cmd == "extract":
        text.parent.mkdir(parents=True, exist_ok=True)
        text.write_text(extract(data), encoding="utf-8")
        print(f"[ok] {text} - {sum(1 for _ in fields(data))} fields")
        return
    warns = apply(data, text.read_text(encoding="utf-8"))
    for w in warns:
        print(f"[warn] {w}", file=sys.stderr)
    content.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {content} - applied, {len(warns)} kept original")


if __name__ == "__main__":
    main()
