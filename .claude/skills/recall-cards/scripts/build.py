#!/usr/bin/env python3
"""recall-cards build script.

Usage:
    python3 build.py content.json --style swiss-minimal -o index.html

Validates content.json against the recall-cards schema, converts
mini-markdown (paragraphs, `code`, **bold**) to safe HTML, injects
the data into the chosen style template, and writes a single
self-contained HTML file.

On validation failure: prints every problem with its JSON path and exits 1,
so the caller (Claude) can fix content.json and re-run.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
THEMES_DIR = ASSETS / "themes"
PLACEHOLDER = "/*__DATA__*/null"
THEMES_PLACEHOLDER = "/*__THEMES__*/null"

def load_themes() -> dict:
    """Load theme configs + CSS. Returns {name: {**config, "css": str}}."""
    cfg = json.loads((THEMES_DIR / "themes.json").read_text(encoding="utf-8"))
    for name, t in cfg.items():
        css_path = THEMES_DIR / f"{name}.css"
        if not css_path.exists():
            sys.exit(f"[error] theme css not found: {css_path}")
        t["css"] = css_path.read_text(encoding="utf-8")
    return cfg

STYLES = list(json.loads((THEMES_DIR / "themes.json").read_text(encoding="utf-8")).keys())

# ---------- mini-markdown ----------

def md_inline(s: str) -> str:
    """HTML-escape everything, then allow only `code` and **bold**."""
    s = html.escape(str(s), quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def md_body(s: str) -> str:
    """Convert body text with paragraph breaks to HTML paragraphs.

    Splits on double-newline for paragraphs. Within each paragraph,
    applies inline formatting (code, bold). Extracts and parses callouts first.
    """
    s = str(s).strip()
    
    callouts_config = {
        "principle": {"icon": "💡", "label": "핵심 원칙"},
        "warning": {"icon": "⚠️", "label": "주의"},
        "analogy": {"icon": "🔗", "label": "일상으로"},
    }
    
    placeholders = {}
    counter = 0
    
    def callout_repl(match):
        nonlocal counter
        ctype = match.group(1)
        content = match.group(2).strip()
        content = re.sub(r"\n", " ", content)
        content = md_inline(content)
        icon = callouts_config[ctype]["icon"]
        label = callouts_config[ctype]["label"]
        
        html_str = f'<div class="callout callout-{ctype}"><span class="callout-icon">{icon}</span><span class="callout-label">{label}</span><div class="callout-body"><p>{content}</p></div></div>'
        ph = f"__CALLOUT_{counter}__"
        placeholders[ph] = html_str
        counter += 1
        return f"\n\n{ph}\n\n"
        
    # Extract ``` code blocks first
    def codeblock_repl(match):
        nonlocal counter
        lang = match.group(1).strip() if match.group(1) else ""
        code_content = html.escape(match.group(2).strip())
        lang_class = f' class="language-{lang}"' if lang else ''
        html_str = f'<pre><code{lang_class}>{code_content}</code></pre>'
        ph = f"__CODEBLOCK_{counter}__"
        placeholders[ph] = html_str
        counter += 1
        return f"\n\n{ph}\n\n"

    s = re.sub(r"```(\w*)\n(.*?)```", codeblock_repl, s, flags=re.DOTALL)
    s = re.sub(r":::(principle|warning|analogy)\n(.*?)\n:::", callout_repl, s, flags=re.DOTALL)

    paragraphs = re.split(r"\n\n+", s)
    parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p in placeholders:
            parts.append(placeholders[p])
        else:
            # Collapse single newlines within a paragraph into spaces
            p = re.sub(r"\n", " ", p)
            parts.append(f"<p>{md_inline(p)}</p>")
    return "\n".join(parts)

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

    # --- sections: array of {title, body} ---
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
        need_str(sec, "body", p)

        diagram = sec.get("diagram")
        if diagram is not None:
            if not isinstance(diagram, dict):
                e(f"{p}.diagram: 객체여야 함")
            else:
                if diagram.get("type") != "mermaid":
                    e(f"{p}.diagram.type: 'mermaid'여야 함")
                need_str(diagram, "code", f"{p}.diagram")
                if "caption" in diagram:
                    need_str(diagram, "caption", f"{p}.diagram", required=False)

        cc = sec.get("codeCompare")
        if cc is not None:
            if not isinstance(cc, dict):
                e(f"{p}.codeCompare: 객체여야 함")
            else:
                for side in ["before", "after"]:
                    if side not in cc or not isinstance(cc[side], dict):
                        e(f"{p}.codeCompare.{side}: 객체여야 함")
                    else:
                        sp = f"{p}.codeCompare.{side}"
                        need_str(cc[side], "label", sp)
                        need_str(cc[side], "code", sp)
                        if "lang" in cc[side]:
                            need_str(cc[side], "lang", sp, required=False)

        if "analogy" in sec:
            need_str(sec, "analogy", p, required=False)

    # --- quiz ---
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
        if "difficulty" in q:
            diff = q["difficulty"]
            if diff not in [1, 2, 3]:
                e(f"{p}.difficulty: 1, 2, 3 중 하나여야 함")

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
        "title": md_inline(data["title"]),
        "date": md_inline(data.get("date", "")),
        "sections": [],
        "quiz": [],
    }
    for sec in data["sections"]:
        sec_out = {
            "title": md_inline(sec["title"]),
            "body": md_body(sec["body"]),
        }
        if "diagram" in sec:
            d = {"type": sec["diagram"]["type"], "code": sec["diagram"]["code"]}
            if "caption" in sec["diagram"]:
                d["caption"] = md_inline(sec["diagram"]["caption"])
            sec_out["diagram"] = d
        if "codeCompare" in sec:
            cc = sec["codeCompare"]
            cc_out = {}
            for side in ["before", "after"]:
                cc_out[side] = {
                    "label": md_inline(cc[side]["label"]),
                    "code": html.escape(cc[side]["code"]),
                }
                if "lang" in cc[side]:
                    cc_out[side]["lang"] = cc[side]["lang"]
            sec_out["codeCompare"] = cc_out
        if "analogy" in sec:
            sec_out["analogy"] = md_body(sec["analogy"])
        out["sections"].append(sec_out)

    for q in data["quiz"]:
        q_out = {
            "q": md_inline(q["q"]),
            "options": [md_inline(o) for o in q["options"]],
            "answer": q["answer"],
            "explanation": md_inline(q["explanation"]),
        }
        if "difficulty" in q:
            q_out["difficulty"] = q["difficulty"]
        out["quiz"].append(q_out)
    return out

# ---------- main ----------

def _slugify(title: str, max_len: int = 40) -> str:
    """Create a filename-safe slug from a title (Korean-friendly)."""
    import unicodedata
    # Strip HTML tags that md_inline might have produced
    s = re.sub(r"<[^>]+>", "", title)
    # Remove chars illegal in filenames
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    # Collapse whitespace to hyphens
    s = re.sub(r'\s+', '-', s.strip())
    # Remove leading/trailing hyphens
    s = s.strip('-')
    # Truncate
    if len(s) > max_len:
        s = s[:max_len].rstrip('-')
    return s or "recall"


def main():
    from datetime import datetime

    ap = argparse.ArgumentParser(description="recall-cards HTML builder")
    ap.add_argument("content", help="content.json path")
    ap.add_argument("--style", choices=STYLES, default="velog",
                    help="initial theme (readers can switch themes in the page)")
    ap.add_argument("-o", "--out", default=None,
                    help="output path (default: {timestamp}-{title}-recall.html)")
    args = ap.parse_args()

    try:
        raw = Path(args.content).read_text(encoding="utf-8")
    except OSError as ex:
        sys.exit(f"[error] cannot read content file: {ex}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as ex:
        sys.exit(f"[error] JSON parse error (line {ex.lineno}, col {ex.colno}): {ex.msg}\n"
                 f"        check quotes/newlines/backslash escaping.")

    errs = validate(data)
    if errs:
        print(f"[error] schema validation failed - {len(errs)} issues:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    template_path = ASSETS / "shell.html"
    if not template_path.exists():
        sys.exit(f"[error] template not found: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    for ph in (PLACEHOLDER, THEMES_PLACEHOLDER):
        if ph not in template:
            sys.exit(f"[error] placeholder ({ph}) missing in template: {template_path}")

    def esc(payload: str) -> str:
        return payload.replace("</", "<\\/")  # prevent </script> early close

    themes_payload = esc(json.dumps({"default": args.style, "themes": load_themes()},
                                    ensure_ascii=False))
    data_payload = esc(json.dumps(transform(data), ensure_ascii=False))
    out_html = template.replace(THEMES_PLACEHOLDER, themes_payload, 1)
    out_html = out_html.replace(PLACEHOLDER, data_payload, 1)

    # Determine output filename
    if args.out:
        out_path = args.out
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        slug = _slugify(data.get("title", ""))
        out_path = f"{ts}-{slug}-recall.html"

    Path(out_path).write_text(out_html, encoding="utf-8")
    print(f"[ok] {out_path} - style={args.style}, sections={len(data['sections'])}, "
          f"quiz={len(data['quiz'])}")


if __name__ == "__main__":
    main()

