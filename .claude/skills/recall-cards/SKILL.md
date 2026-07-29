---
name: recall-cards
description: Turn the current Claude Code session's learnings into an interactive study page (field notes + multiple-choice recall quiz) as a single HTML file. Use when the user asks to review the session, study what was learned, quiz them on today's work, make recall/flash cards, or says things like "세션 복습", "오늘 배운 거 정리해서 퀴즈로", "회상 카드 만들어줘", "recall", "quiz me on this session". Leverages retrieval practice: reading the notes, then actively recalling via quiz.
---

# recall-cards

세션에서 건진 **기반 지식**을 블로그 글처럼 풀어쓰고, 퀴즈로 인출하는 한 장짜리 HTML을 만든다.
Claude는 콘텐츠 JSON만 작성하고, 렌더링은 스크립트가 한다. **직접 HTML을 쓰지 말 것.**

## Parameters

사용자 요청에서 아래 파라미터를 파싱한다. 언급이 없으면 디폴트.

| 파라미터 | 값 | 디폴트 | 적용 위치 |
|---|---|---|---|
| `style` | swiss-minimal, neubrutalism, glassmorphism, terminal-dark, claymorphism | swiss-minimal | build.py `--style` 플래그 |
| `quiz_count` | 정수 (1~15 권장) | 5 | JSON 작성 시 quiz 항목 수 |
| `depth` | brief, detail | detail | JSON 작성 시 분량·구조 (아래 규칙) |

자연어 매핑 예: "간단하게/짧게" → brief, "터미널 느낌" → terminal-dark, "퀴즈 10개" → quiz_count=10.

`quiz_count`와 `depth`는 스크립트가 아니라 **JSON을 쓰는 Claude의 행동**을 바꾸는 파라미터다. 스크립트에 넘기지 않는다.

## Workflow

1. 파라미터 파싱 (없으면 디폴트).
2. **세션 회고 — 기반 지식 발굴.** 세션에서 한 작업은 출발점일 뿐이다. **한 겹 더 파고 들어서 그 작업 아래 깔린 범용 원리를 발굴한다.**
   - 예: 세션에서 `UPDATE ... WHERE status='RUNNING'`을 썼으면 → "우리 코드의 409 핸들러"가 아니라, **"낙관적 동시성 제어(OCC)는 왜 작동하고, 비관적 잠금과 언제 갈리는가"**를 쓴다.
   - 예: React `useEffect` 의존성 배열을 고쳤으면 → "이 컴포넌트의 버그 수정"이 아니라, **"클로저가 stale 값을 캡처하는 메커니즘과, 의존성 배열이 이를 해결하는 원리"**를 쓴다.
   - 세션의 구체 코드·상황은 **"우리가 오늘 마주친 사례"**로만 1~2문장 언급. 본문의 주인공은 기반 원리.
   - 단순 작업 로그(파일 몇 개 고침, 변수 이름 변경 등)는 제외.
3. depth 규칙에 맞춰 `content.json` 작성 (스키마 아래).
4. 빌드:
   ```bash
   python3 scripts/build.py content.json --style <style> -o /mnt/user-data/outputs/recall.html
   ```
5. 검증 에러가 나오면 메시지의 JSON 경로를 보고 content.json을 고쳐 재실행. 성공하면 파일을 사용자에게 제시.

## Content schema (content.json)

```json
{
  "title": "동시성 제어의 두 얼굴",
  "date": "2026-07-27 · Claude Code 세션",
  "sections": [
    {
      "title": "낙관적 vs 비관적 — 같은 문제, 반대의 베팅",
      "body": "데이터베이스에서 두 트랜잭션이 같은 행을 고치려 할 때, 우리에겐 두 가지 전략이 있다.\n\n**비관적 잠금**은 '충돌이 일어날 것이다'에 베팅한다. `SELECT ... FOR UPDATE`로 행을 먼저 잠그고, 다른 트랜잭션은 잠금이 풀릴 때까지 기다린다. 안전하지만, 잠금 대기가 길어지면 처리량이 떨어진다.\n\n**낙관적 동시성 제어(OCC)**는 '충돌은 드물다'에 베팅한다. 아무도 잠그지 않고 작업한 뒤, 커밋 직전에 '내가 읽은 이후 누가 바꿨나?'를 확인한다. `UPDATE ... WHERE version = @old_version`이 대표적이다. rowcount가 0이면 재시도하거나 실패 처리한다.\n\n오늘 세션에서 종결 처리의 경합을 `UPDATE ... WHERE status='RUNNING'`으로 풀었는데, 이것이 정확히 OCC 패턴이다. 상태 컬럼이 버전 역할을 하고, rowcount가 CAS(compare-and-swap)의 성공 여부를 알려준다.\n\n**갈림길은 충돌 빈도다.** 같은 행을 동시에 고치는 일이 잦으면 비관적 잠금이 재시도 비용을 줄여준다. 충돌이 드물고 처리량이 중요하면 OCC가 낫다."
    }
  ],
  "quiz": [
    {
      "q": "낙관적 동시성 제어에서 커밋이 실패했다는 것을 어떻게 감지하는가?",
      "options": ["트랜잭션 타임아웃이 발생한다", "UPDATE의 affected rowcount가 0이다", "데이터베이스가 deadlock 에러를 던진다", "다른 트랜잭션의 잠금에 블로킹된다"],
      "answer": 1,
      "explanation": "OCC는 잠금을 쓰지 않으므로 블로킹이나 데드락이 발생하지 않는다. `WHERE version = @old`를 건 UPDATE가 0행을 수정하면 '누군가 이미 바꿨다'는 뜻이다. 타임아웃은 잠금 기반 전략의 증상이고, 데드락도 비관적 잠금 특유의 문제다."
    }
  ]
}
```

### 스키마 규칙

- **`title`** (필수): 기반 지식의 핵심을 담은 제목. 프로젝트 이름이 아니라 원리를 드러내는 제목.
- **`date`** (선택): 날짜·세션 표시.
- **`sections`** (필수, 1개 이상): 각 섹션은 하나의 주제 영역.
  - `title` (필수): 섹션 제목.
  - `body` (필수): **마크다운 자유형 본문.** `\n\n`으로 문단 구분. 지원 문법: `**bold**`, `` `code` ``, `\n\n`(문단). 이 외의 마크다운(헤더, 리스트, 링크 등)은 사용하지 않는다.
- **`quiz`** (필수, 1개 이상): 객관식 퀴즈 배열.
  - `q` (필수): 질문.
  - `options` (필수, 2~5개): 선지 배열.
  - `answer` (필수): 0-기반 정답 인덱스.
  - `explanation` (필수): 해설.
- 텍스트 필드는 **`code`와 `**bold**`만 허용**. raw HTML 금지 (스크립트가 이스케이프함).

## Writing rules — 톤과 깊이

**교수가 학생에게 가르치듯, 블로그 글 톤으로 쓴다.** 정형화된 필드를 채우는 것이 아니라, 읽는 사람이 원리를 이해하도록 **흐름 있는 산문**을 쓴다.

1. **출발은 세션, 도착은 기반 지식.** 세션의 구체 작업은 도입부 사례 1~2문장으로만 쓰고, 본문은 그 아래 깔린 원리·메커니즘·설계 철학을 풀어쓴다.
2. **추상적 요약 금지.** "동시성을 잘 다뤘다"는 아무것도 알려주지 않는다. 구체적 메커니즘을 설명한다: 어떻게 작동하는지, 왜 그렇게 설계되었는지, 어디서 깨지는지.
3. **비교로 깊이를 만든다.** "A가 좋다"보다 "A와 B는 같은 문제를 반대로 푼다"가 이해를 깊게 한다.
4. **코드 스니펫은 원리를 설명할 때만.** 프로젝트의 구체 코드가 아니라, 원리를 보여주는 최소한의 패턴을 `` `code` ``로 인라인 사용.
5. **나중에 다시 읽었을 때 그날의 판단을 재현할 수 있어야 한다.** 이것이 detail의 목표.

## Depth rules

**detail (디폴트)** — 블로그 포스트 수준:
- 섹션 2~5개, 주제 영역별로 묶기.
- 섹션당 body 3~6문단. 원리→메커니즘→갈림길→세션 사례 순서가 좋지만 강제는 아님. 자연스럽게.
- 하나의 섹션이 하나의 완결된 글이 되어야 한다.

**brief** — 빠른 복습용:
- 섹션 1~2개, 섹션당 body 2~3문단.
- 핵심 원리만 짧게 짚고 넘어간다.

## Quiz quality rules (가장 중요)

인출 연습의 효과는 퀴즈 품질이 좌우한다:

1. **기반 원리를 묻는다.** "우리 프로젝트에서 어떤 함수를 썼나"보다 "이 패턴이 왜 작동하나", "이 전략이 깨지는 조건은 무엇인가". sections의 본문에서 설명한 원리를 인출하는 문제가 좋다.
2. **오답 선지는 그럴듯한 오개념.** 세션 중 실제로 헷갈렸던 것, 흔한 착각, 겉보기에 맞아 보이는 것에서 뽑는다. 뻔히 틀린 선지는 인출이 아니라 소거법 놀이가 된다.
3. **explanation은 정답 근거 + 주요 오답이 왜 틀렸는지**까지.
4. **정답 위치를 섞는다.** 한 인덱스에 60% 이상 몰리면 스크립트가 경고한다.
5. 개수는 `quiz_count`. 섹션 수보다 퀴즈가 많으면 한 섹션에서 각도 다른 문제 2개 가능.

## Style reference

| style | 느낌 | 어울리는 경우 |
|---|---|---|
| swiss-minimal | 흰 종이 + 검은 선 + 빨강, 시험지 | 디폴트, 장문 읽기 |
| neubrutalism | 두꺼운 테두리 + 원색, 게임 같은 | 가볍고 재미있게 |
| glassmorphism | 그라데이션 + 유리 카드 | 모던, 발표용 |
| terminal-dark | 터미널 창 + 모노스페이스 | 코드 중심 세션 |
| claymorphism | 말랑한 점토 + 파스텔 | 친근한 학습 앱 |
