"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RetryPolicyService(BaseModuleService):
    MODULE = "retry_policy"
    ENTITY = "重试规则"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["规则名称", "最大重试次数", "退避间隔", "重试条件", "降级策略"]
    REQUIRED_FIELDS = ["规则名称", "最大重试次数", "退避间隔"]
    STATUS_ORDER = ["草稿", "已启用", "已停用"]
    ACTION_RULES = {"启用规则": "已启用", "停用规则": "已停用"}
    NEGATIVE_ACTIONS = ["停用规则"]
