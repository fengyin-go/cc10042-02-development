"""运行配置：端口、跨域、运行环境。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    app_name: str = "智能网页采集与数据抽取平台"
    env: str = "local"
    port: int = 8016
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://127.0.0.1:5196",
            "http://localhost:5196",
        ]
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
