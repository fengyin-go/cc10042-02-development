"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RateLimiterService(BaseModuleService):
    MODULE = "rate_limiter"
    ENTITY = "限速规则"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["规则名称", "最大QPS", "并发连接数", "退避策略", "生效时段"]
    REQUIRED_FIELDS = ["规则名称", "最大QPS", "并发连接数"]
    STATUS_ORDER = ["待生效", "已生效", "已停用"]
    ACTION_RULES = {"启用限速": "已生效", "停用限速": "已停用"}
    NEGATIVE_ACTIONS = ["停用限速"]
