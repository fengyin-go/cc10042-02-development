"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ResultAuditService(BaseModuleService):
    MODULE = "result_audit"
    ENTITY = "审计记录"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["采集批次", "总条数", "成功条数", "字段完整度", "异常类型"]
    REQUIRED_FIELDS = ["采集批次", "总条数", "成功条数"]
    STATUS_ORDER = ["正常", "数据缺失", "格式异常", "需要复核"]
    ACTION_RULES = {"标记需要复核": "需要复核", "批量忽略": "正常"}
    NEGATIVE_ACTIONS = []
