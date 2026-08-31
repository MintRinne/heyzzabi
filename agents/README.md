# heyzzabi_agents

헤이짜비 AI 에이전트 — **Django 무관** 순수 파이썬 패키지. AI 담당이 소유.

백엔드(`../backend`)가 `pip install -e ../agents` 로 설치해서 import 한다.
DB 접근이 필요한 부분(후보 조회, WBS 날짜 계산, 결과 저장)은 백엔드가 담당하고,
여기서는 **"LLM에게 무엇을 어떻게 물어보는가"** 만 다룬다.

## 구조

```
src/heyzzabi_agents/
  client.py      OpenAI 래퍼 — 키는 configure(key) 또는 OPENAI_API_KEY 환경변수
  prompts.py     모델·프롬프트 상수·JSON 스키마  ← 튜닝 1차 지점
  _normalize.py  모델 응답 정규화(필드 누락 방어)
  proposal.py    generate_proposal, past_case_insight (tool calling)
  reqspec.py     generate_reqspec
  tasks.py       extract_tasks, recommend_assignees, batch_assign
  chat.py        chat_answer (AI Hub 챗봇)
  research.py    deep_research
  reject.py      analyze_reject_patterns
  config.py      parse_agent_config (temperature/개수 clamp)
```

## 개발 (백엔드 없이 단독)

```bash
cd agents
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"

pytest                      # OpenAI 불필요 (config clamp 테스트)

# 실제 LLM 호출 스모크
set OPENAI_API_KEY=sk-...
python -c "from heyzzabi_agents import generate_proposal; print(generate_proposal('[회의록] 이메일 로그인만. 다크모드 지원.', '참고 없음', 0.0))"
```

## 공개 API

`from heyzzabi_agents import ...`

- `generate_proposal(raw_content, past_case_insight, temperature) -> dict`
- `past_case_insight(raw_content, draft_overview, search_fn) -> str`
- `generate_reqspec(proposal_content, raw_content, temperature) -> dict`
- `extract_tasks(reqspec_content, min_tasks, max_tasks, temperature) -> list`
- `recommend_assignees(task_payload, candidates, max_n=3) -> list`
- `batch_assign(tasks_payload, candidates) -> list`
- `chat_answer(previous_messages, projects_json, members_json) -> str`
- `deep_research(question, packet) -> {content, degraded}`
- `analyze_reject_patterns(reasons) -> {overallSummary, patterns}`
- `parse_agent_config(raw) -> dict` · `DEFAULT_AGENT_CONFIG`
- `configure(api_key)` · `AIConfigError`

반환 dict의 키는 **camelCase**(프론트 템플릿 스키마와 일치) — 바꾸지 말 것.
