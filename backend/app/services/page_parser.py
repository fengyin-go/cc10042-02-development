"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PageParserService(BaseModuleService):
    MODULE = "page_parser"
    ENTITY = "解析规则"
    OPERATION_TERM = "解析"
    LIST_FIELDS = ["规则名称", "目标元素选择器", "字段映射", "验证表达式", "解析优先级"]
    REQUIRED_FIELDS = ["规则名称", "目标元素选择器", "字段映射"]
    STATUS_ORDER = ["草稿", "已启用", "已失效"]
    ACTION_RULES = {"启用规则": "已启用", "停用规则": "已失效"}
    NEGATIVE_ACTIONS = ["停用规则"]
