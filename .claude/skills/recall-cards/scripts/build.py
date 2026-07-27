#!/usr/bin/env python3
"""recall-cards build script.

Usage:
    python3 build.py content.json --style swiss-minimal -o index.html

Validates content.json against the recall-cards schema, converts
mini-markdown (`code`, **bold**) to safe HTML, injects the data into
the chosen style template, and writes a single self-contained HTML file.

On validation failure: prints every problem with its JSON path and exits 1,
so the caller (Claude) can fix content.json and re-run.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

STYLES = ["swiss-minimal", "neubrutalism", "glassmorphism", "terminal-dark", "claymorphism"]
ASSETS = Path(__file__).resolve().parent.parent / "assets"
PLACEHOLDER = "/*__DATA__*/null"

# ---------- mini-markdown ----------

def md(s: str) -> str:
    """HTML-escape everything, then allow only `code` and **bold**."""
    s = html.escape(str(s), quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s

# ---------- validation ----------

def validate(data) -> list:
    errs = []
    e = errs.append

    def need_str(obj, key, path, required=True):
        v = obj.get(key)
        if v is None:
            if required:
                e(f"{path}.{key}: 필수 문자열이 없음")
            return
        if not isinstance(v, str) or not v.strip():
            e(f"{path}.{key}: 비어있지 않은 문자열이어야 함 (현재: {v!r})")

    if not isinstance(data, dict):
        return ["최상위가 JSON 객체가 아님"]

    need_str(data, "title", "$")
    need_str(data, "date", "$", required=False)

    stats = data.get("stats")
    if stats is not None:
        if not isinstance(stats, list):
            e("$.stats: 배열이어야 함")
        else:
            for i, st in enumerate(stats):
                if not isinstance(st, dict):
                    e(f"$.stats[{i}]: 객체여야 함")
                    continue
                need_str(st, "label", f"$.stats[{i}]")
                need_str(st, "value", f"$.stats[{i}]")

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        e("$.sections: 비어있지 않은 배열이어야 함")
        sections = []
    for si, sec in enumerate(sections):
        p = f"$.sections[{si}]"
        if not isinstance(sec, dict):
            e(f"{p}: 객체여야 함")
            continue
        need_str(sec, "title", p)
        need_str(sec, "no", p, required=False)
        need_str(sec, "subtitle", p, required=False)
        cards = sec.get("cards")
        if not isinstance(cards, list) or not cards:
            e(f"{p}.cards: 비어있지 않은 배열이어야 함")
            continue
        for ci, c in enumerate(cards):
            cp = f"{p}.cards[{ci}]"
            if not isinstance(c, dict):
                e(f"{cp}: 객체여야 함")
                continue
            need_str(c, "heading", cp)
            need_str(c, "body", cp)
            need_str(c, "tag", cp, required=False)
            need_str(c, "rule", cp, required=False)

    quiz = data.get("quiz")
    if not isinstance(quiz, list) or not quiz:
        e("$.quiz: 비어있지 않은 배열이어야 함")
        quiz = []
    for qi, q in enumerate(quiz):
        p = f"$.quiz[{qi}]"
        if not isinstance(q, dict):
            e(f"{p}: 객체여야 함")
            continue
        need_str(q, "q", p)
        need_str(q, "explanation", p)
        opts = q.get("options")
        if not isinstance(opts, list) or not (2 <= len(opts) <= 5):
            e(f"{p}.options: 2~5개의 문자열 배열이어야 함")
            opts = []
        else:
            for oi, o in enumerate(opts):
                if not isinstance(o, str) or not o.strip():
                    e(f"{p}.options[{oi}]: 비어있지 않은 문자열이어야 함")
        ans = q.get("answer")
        if not isinstance(ans, int) or isinstance(ans, bool) or not (0 <= ans < max(len(opts), 1)):
            e(f"{p}.answer: 0 이상 {max(len(opts) - 1, 0)} 이하의 정수여야 함 (현재: {ans!r})")

    # answer position balance: warn (not fail) if one index dominates
    if quiz and not errs:
        answers = [q["answer"] for q in quiz]
        top = max(answers.count(a) for a in set(answers))
        if len(quiz) >= 4 and top / len(quiz) > 0.6:
            print(f"[warn] 정답 위치가 한쪽에 몰려 있음 ({answers}). 골고루 섞는 것을 권장.", file=sys.stderr)
    return errs

# ---------- transform ----------

def transform(data: dict) -> dict:
    """Apply mini-markdown to all human-visible text fields."""
    out = {
        "title": md(data["title"]),
        "date": md(data.get("date", "")),
        "stats": [{"label": md(s["label"]), "value": md(s["value"])} for s in data.get("stats") or []],
        "sections": [],
        "quiz": [],
    }
    for sec in data["sections"]:
        out["sections"].append({
            "no": md(sec.get("no", "")),
            "title": md(sec["title"]),
            "subtitle": md(sec.get("subtitle", "")),
            "cards": [{
                "tag": md(c.get("tag", "")),
                "heading": md(c["heading"]),
                "body": md(c["body"]),
                "rule": md(c.get("rule", "")),
            } for c in sec["cards"]],
        })
    for q in data["quiz"]:
        out["quiz"].append({
            "q": md(q["q"]),
            "options": [md(o) for o in q["options"]],
            "answer": q["answer"],
            "explanation": md(q["explanation"]),
        })
    return out

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="recall-cards HTML builder")
    ap.add_argument("content", help="content.json 경로")
    ap.add_argument("--style", choices=STYLES, default="swiss-minimal")
    ap.add_argument("-o", "--out", default="index.html")
    args = ap.parse_args()

    try:
        raw = Path(args.content).read_text(encoding="utf-8")
    except OSError as ex:
        sys.exit(f"[error] content 파일을 읽을 수 없음: {ex}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as ex:
        sys.exit(f"[error] JSON 파싱 실패 (line {ex.lineno}, col {ex.colno}): {ex.msg}\n"
                 f"        따옴표/줄바꿈/백슬래시 이스케이프를 확인할 것.")

    errs = validate(data)
    if errs:
        print(f"[error] 스키마 검증 실패 — {len(errs)}건:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    template_path = ASSETS / f"{args.style}.html"
    if not template_path.exists():
        sys.exit(f"[error] 템플릿 없음: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        sys.exit(f"[error] 템플릿에 플레이스홀더({PLACEHOLDER})가 없음: {template_path}")

    payload = json.dumps(transform(data), ensure_ascii=False)
    payload = payload.replace("</", "<\\/")  # </script> 조기 종료 방지
    out_html = template.replace(PLACEHOLDER, payload, 1)

    Path(args.out).write_text(out_html, encoding="utf-8")
    n_cards = sum(len(s["cards"]) for s in data["sections"])
    print(f"[ok] {args.out} 생성 — style={args.style}, sections={len(data['sections'])}, "
          f"cards={n_cards}, quiz={len(data['quiz'])}")


if __name__ == "__main__":
    main()
