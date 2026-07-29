# recall-cards

Claude Code 세션에서 건진 **기반 지식**을 블로그 글처럼 풀어쓰고, **객관식 회상 퀴즈**로 인출하는 한 장짜리 HTML을 만드는 스킬.

인지심리학의 인출 연습(retrieval practice)에 기반한다. 읽기만 하면 금방 잊지만, 기억을 **꺼내는** 행위 자체가 기억을 강화한다. 그래서 정리 본문과 퀴즈가 한 페이지에 함께 있다.

세션의 구체 작업은 출발점일 뿐 — 그 아래 깔린 CS 원리, 언어 설계 철학, 알고리즘의 **왜**를 파고들어, 교수가 학생에게 설명하듯 산문으로 풀어쓴다.

## Install

### Claude Code — 마켓플레이스 (권장)

```
/plugin marketplace add GoatHead/recall-cards-skill
/plugin install recall-cards@recall-cards-skill
```

### Claude Code — 수동 설치

```bash
# 전역 (모든 프로젝트)
git clone https://github.com/GoatHead/recall-cards-skill.git /tmp/rc
cp -r /tmp/rc/.claude/skills/recall-cards ~/.claude/skills/

# 특정 프로젝트만
cp -r /tmp/rc/.claude/skills/recall-cards .claude/skills/
```

설치 확인: 새 세션에서 `/plugin` 또는 스킬 목록에 `recall-cards`가 보이면 완료.

## Update

새 버전이 나오면 마켓플레이스 카탈로그를 먼저 갱신한 뒤 플러그인을 업데이트한다:

```
/plugin marketplace update recall-cards-skill
/plugin update recall-cards@recall-cards-skill
```

CLI에서는:

```bash
claude plugin marketplace update recall-cards-skill
claude plugin update recall-cards@recall-cards-skill
```

카탈로그 갱신 없이 `plugin update`만 하면 이전 버전이 최신으로 보고되어 업데이트되지 않는다. 수동 설치한 경우는 Install의 수동 설치 절차를 다시 실행하면 된다.

## Usage

```
recall-cards로 이번 세션 복습 만들어줘
```

파라미터는 자연어로:

```
터미널 스타일에 퀴즈 10개로 복습 만들어줘
간단하게 브리프로만
```

| 파라미터 | 값 | 디폴트 |
|---|---|---|
| style | swiss-minimal · neubrutalism · glassmorphism · terminal-dark · claymorphism | swiss-minimal |
| quiz_count | 1~15 | 5 |
| depth | brief · detail | detail |

**depth 차이** — `brief`는 핵심 원리를 1~2섹션으로 짧게, `detail`은 주제 영역별로 2~5섹션, 각 섹션이 하나의 완결된 블로그 포스트 수준으로. 나중에 다시 읽었을 때 그날의 판단을 재현할 수 있는 수준이 detail의 목표다.

## How it works

Claude는 콘텐츠 JSON만 쓰고, HTML은 스크립트가 만든다. 매번 UI 코드를 다시 생성하지 않으므로 출력 토큰이 절약되고 결과물의 모양이 항상 일정하다.

```
세션 회고 → 기반 지식 발굴 → content.json → build.py → 단일 HTML
```

```bash
python3 scripts/build.py content.json --style terminal-dark -o recall.html
```

`build.py`는 스키마를 검증해 문제가 있으면 JSON 경로와 함께 알려준다(`$.quiz[0].answer: 0 이상 3 이하의 정수여야 함`). 본문은 전부 HTML 이스케이프되고 `` `code` ``와 `**bold**`만 태그로 변환되며, `\n\n`으로 문단이 분리되므로 긴 산문도 깔끔하게 렌더링된다.

결과물은 외부 요청이 없는 단일 파일이라 브라우저로 그냥 열면 된다.

## Structure

```
.claude-plugin/
├── marketplace.json
└── plugin.json
.claude/skills/recall-cards/
├── SKILL.md              # 파라미터·스키마·퀴즈 품질 규칙
├── assets/               # 5개 스타일 템플릿 (마크업 동일, CSS만 상이)
└── scripts/build.py      # 검증 → 마크다운 변환 → 주입
```

템플릿 5개는 CSS만 다르다. 마크업이나 퀴즈 로직을 고칠 땐 하나를 고친 뒤 나머지에 `<style>` 블록만 갈아끼우면 된다.

## License

MIT
