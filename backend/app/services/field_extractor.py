"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FieldExtractorService(BaseModuleService):
    MODULE = "field_extractor"
    ENTITY = "字段模板"
    OPERATION_TERM = "清洗"
    LIST_FIELDS = ["模板名称", "源字段路径", "目标字段名", "清洗函数", "默认值"]
    REQUIRED_FIELDS = ["模板名称", "源字段路径", "目标字段名"]
    STATUS_ORDER = ["待验证", "已验证", "已废弃"]
    ACTION_RULES = {"验证字段": "已验证", "废弃模板": "已废弃"}
    NEGATIVE_ACTIONS = []
