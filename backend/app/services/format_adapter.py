"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FormatAdapterService(BaseModuleService):
    MODULE = "format_adapter"
    ENTITY = "格式配置"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["配置名称", "输入格式", "输出格式", "Schema映射", "校验规则"]
    REQUIRED_FIELDS = ["配置名称", "输入格式", "输出格式"]
    STATUS_ORDER = ["待验证", "已验证", "已废弃"]
    ACTION_RULES = {"验证格式": "已验证", "废弃配置": "已废弃"}
    NEGATIVE_ACTIONS = []
