"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DataDedupeService(BaseModuleService):
    MODULE = "data_dedupe"
    ENTITY = "去重规则"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["规则名称", "去重维度", "去重窗口", "保留策略", "命中计数"]
    REQUIRED_FIELDS = ["规则名称", "去重维度", "去重窗口"]
    STATUS_ORDER = ["草稿", "已启用", "已停用"]
    ACTION_RULES = {"启用去重": "已启用", "停用去重": "已停用"}
    NEGATIVE_ACTIONS = ["停用去重"]
