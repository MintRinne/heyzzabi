"""
shared/retry_config.py

에이전트 전반에 적용되는 모델·재시도 기본값 (팀 컨벤션과 동일한 역할).
개별 에이전트가 다른 값이 필요하면 자기 agent.py에서 덮어쓴다.
"""

# 이 프로젝트는 OpenAI 프로바이더를 쓴다 (팀 ai/ 는 Anthropic, llm_client 만 다름)
DEFAULT_MODEL = "gpt-4o"
MODEL_MINI = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 8000

# 구조화 생성(JSON 출력) 노드는 0.0, 자연어 답변 생성 노드는 0.2~0.3
TEMPERATURE_STRUCTURED = 0.0
TEMPERATURE_GENERATIVE = 0.3

# 스키마 파싱 실패 시 재시도 횟수
MAX_RETRIES = 2

# 단일 LLM 호출 타임아웃(초)
REQUEST_TIMEOUT_SECONDS = 60
