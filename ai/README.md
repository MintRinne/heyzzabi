# heyzzabi_ai

헤이짜비 AI 에이전트 — **Django 무관** 순수 파이썬 패키지.
내부 구조는 팀 저장소(`SKN31-FINAL-1Team`)의 `ai/` 컨벤션을 따른다.

## 구조 (팀 컨벤션)

```
heyzzabi_ai/
  __init__.py            백엔드가 쓰는 안정 함수 파사드
  state.py               PipelineState (TypedDict)
  graph.py               노드 순서 문서 (LangGraph 조립은 미도입)
  config.py              parse_agent_config (temperature/개수 clamp)
  shared/
    llm_client.py        get_client()=instructor.from_openai, get_raw_client(), configure()
    retry_config.py      DEFAULT_MODEL / MAX_RETRIES / TEMPERATURE_*
    schemas_base.py      공통 Enum (FeaturePriority, ReqPriority, Difficulty)
    prompt_loader.py     YAML 로더 (lru_cache)
  <agent>/               agent.py · prompt_builder.py · schemas.py · prompts/*.yaml · __init__.py
```

| 에이전트 | 파이프라인 단계 | 하는 일 |
|---|---|---|
| `meeting_analysis`  | A1-1 (선택) | 회의록 원문 → 구조화 요약 |
| `plan_draft`        | A1-2 | 회의록 → 기획서 (tool-calling 과거사례 + 2차 검토) |
| `requirement_draft` | A2-1 | 승인된 기획서 → 요구사항정의서 (2차 검토) |
| `task_generation`   | A2-2 | 요구사항정의서 → 실행 단위 업무 (2차 검토) |
| `assignee_recommend`| A2-3 | 담당자 추천 (단건 `recommend` / 배치 `batch`) + `rule_filter` |
| `qa_answer`         | Track B | AI Hub 챗봇 (사내 데이터 그라운딩) |
| `retrieval`         | Track B | 딥리서치 (내부 packet, 팩트체크 → 보고서) |
| `reject_insight`    | 피드백 | PM 반려 사유 → 반복 패턴 + 프롬프트 개선 제안 |

- 각 `agent.py` 는 `<domain>()`(직접 호출용) + `<name>_node(state)`(그래프 노드용) 둘 다 제공.
- 출력은 **instructor + Pydantic** 으로 스키마 강제. 필드명은 프론트 템플릿과 맞춰 camelCase.
- 프로바이더는 **OpenAI** (팀 `ai/` 는 Anthropic — `shared/llm_client.py` 만 다름).

## 개발 (백엔드 없이 단독)

```bash
cd ai
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pytest                              # OpenAI 불필요 (config + schema 테스트)

set OPENAI_API_KEY=sk-...
python -c "from heyzzabi_ai import generate_reqspec; print(generate_reqspec('{\"features\":[{\"name\":\"로그인\"}]}', '', 0.0))"
```

## 백엔드 연동

`backend/requirements.txt` 의 `-e ../ai` 로 설치. 뷰는 `from heyzzabi_ai import generate_proposal, ...`.
`core/apps.py` `ready()` 에서 `configure(settings.OPENAI_API_KEY)`.
