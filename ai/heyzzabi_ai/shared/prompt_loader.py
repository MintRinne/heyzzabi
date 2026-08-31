"""
shared/prompt_loader.py

각 에이전트의 prompt_builder.py 가 공통으로 쓰는 YAML 로더.
(팀 컨벤션에서는 에이전트마다 load_template() 을 중복 정의하지만,
 여기서는 한 곳에 모아 lru_cache 로 캐싱한다.)
"""

from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=64)
def load_yaml(prompts_dir: str, name: str) -> dict:
    with open(Path(prompts_dir) / name, encoding="utf-8") as f:
        return yaml.safe_load(f)
