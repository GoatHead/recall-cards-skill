---
name: recall-cards
description: Turn the current Claude Code session's learnings into an interactive study page (field notes + multiple-choice recall quiz) as a single HTML file. Use when the user asks to review the session, study what was learned, quiz them on today's work, make recall/flash cards, or says things like "세션 복습", "오늘 배운 거 정리해서 퀴즈로", "회상 카드 만들어줘", "recall", "quiz me on this session". Leverages retrieval practice: reading the notes, then actively recalling via quiz.
---

# recall-cards

세션에서 배운 내용을 **필드노트 + 객관식 회상 퀴즈** 한 장짜리 HTML로 만든다.
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
2. 세션을 회고해 **배울 가치가 있는 것**만 추린다: 설계 결정과 그 이유, 부딪힌 함정과 해결, 원리(왜 그렇게 동작하는가). 단순 작업 로그(파일 몇 개 고침 등)는 제외.
3. depth 규칙에 맞춰 `content.json` 작성 (스키마 아래).
4. 빌드:
   ```bash
   python3 scripts/build.py content.json --style <style> -o /mnt/user-data/outputs/recall.html
   ```
5. 검증 에러가 나오면 메시지의 JSON 경로를 보고 content.json을 고쳐 재실행. 성공하면 파일을 사용자에게 제시.

## Content schema (content.json)

```json
{
  "title": "결산 세션 구현에서 건진 것들",
  "date": "2026-07-27 · Claude Code 세션",
  "stats": [{"label": "배운 것", "value": "12"}, {"label": "주제 영역", "value": "5"}],
  "sections": [
    {
      "no": "01",
      "title": "동시성 · 백그라운드",
      "subtitle": "이벤트 루프, 요청 컨텍스트, 프로세스가 죽을 때",
      "cards": [
        {
          "tag": "경합 방지",
          "heading": "전역 409 + CAS 종결",
          "body": "종결 전이는 `UPDATE ... WHERE status='RUNNING'`로 걸어 rowcount로 적용 여부를 판정한다. 취소와 완료가 서로를 **덮어쓰지 못한다**.",
          "rule": "\"먼저 읽고 나중에 쓰기\"의 틈은 조건부 UPDATE(CAS)로 닫는다."
        }
      ]
    }
  ],
  "quiz": [
    {
      "q": "rebase 후 커밋 해시가 바뀌는 근본적인 이유는?",
      "options": ["커밋 메시지가 수정되기 때문", "부모 커밋이 달라져 해시가 재계산되기 때문", "보안을 위한 주기적 갱신", "파일 내용이 압축되기 때문"],
      "answer": 1,
      "explanation": "해시는 내용 + 부모까지 포함해 계산된다. rebase는 부모를 바꾸므로 내용이 같아도 해시가 달라진다. 나머지 선지가 틀린 이유: 메시지는 그대로 보존되고, Git에 주기적 갱신·압축 개념은 해시와 무관하다."
    }
  ]
}
```

- 텍스트 필드는 **미니 마크다운만**: `` `code` ``와 `**bold**`. raw HTML 금지 (스크립트가 이스케이프함).
- `answer`는 0-기반 인덱스. `options`는 2~5개.
- `stats`, `no`, `subtitle`, `tag`, `rule`은 optional — 템플릿이 없으면 건너뜀.

## Depth rules

**detail (디폴트)** — 참고 문서 수준의 필드노트를 목표로:
- 섹션 2~5개, 주제 영역별로 묶기 (`no`: "01", "02"…). `subtitle` 포함.
- 카드당 body 3~6문장. 구체적 코드·수치·조건을 `` `code` ``로 포함. 추상적 요약("동시성을 잘 다뤘다") 금지 — 다시 읽었을 때 그날의 판단을 재현할 수 있어야 함.
- **모든 카드에 `rule` 필수** — 한 문장으로 일반화한 교훈. 이 문장이 퀴즈의 씨앗이 된다.
- `stats` 포함 (배운 것 개수, 주제 영역 수, 회상 카드 수 등 실측값).

**brief** — 빠른 복습용:
- 섹션 1개 (no/subtitle 생략 가능), 카드 3~5개, 카드당 body 2~3문장.
- `rule`, `stats`, `tag` 생략 가능.

## Quiz quality rules (가장 중요)

인출 연습의 효과는 퀴즈 품질이 좌우한다:

1. **원리를 묻는다.** "명령어 이름이 뭐였나"보다 "왜 그렇게 동작하나", "이 상황에서 무엇이 깨지나". 카드의 `rule`을 뒤집거나 적용하는 문제가 좋다.
2. **오답 선지는 그럴듯한 오개념.** 세션 중 실제로 헷갈렸던 것, 흔한 착각, 겉보기에 맞아 보이는 것에서 뽑는다. 뻔히 틀린 선지는 인출이 아니라 소거법 놀이가 된다.
3. **explanation은 정답 근거 + 주요 오답이 왜 틀렸는지**까지.
4. **정답 위치를 섞는다.** 한 인덱스에 60% 이상 몰리면 스크립트가 경고한다.
5. 개수는 `quiz_count`. 카드 수보다 퀴즈가 많으면 한 카드에서 각도 다른 문제 2개 가능.

## Style reference

| style | 느낌 | 어울리는 경우 |
|---|---|---|
| swiss-minimal | 흰 종이 + 검은 선 + 빨강, 시험지 | 디폴트, 장문 읽기 |
| neubrutalism | 두꺼운 테두리 + 원색, 게임 같은 | 가볍고 재미있게 |
| glassmorphism | 그라데이션 + 유리 카드 | 모던, 발표용 |
| terminal-dark | 터미널 창 + 모노스페이스 | 코드 중심 세션 |
| claymorphism | 말랑한 점토 + 파스텔 | 친근한 학습 앱 |
