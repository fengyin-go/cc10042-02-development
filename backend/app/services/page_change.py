"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PageChangeService(BaseModuleService):
    MODULE = "page_change"
    ENTITY = "变更记录"
    OPERATION_TERM = "解析"
    LIST_FIELDS = ["目标页面", "监测时间", "变更类型", "变更片段", "影响规则"]
    REQUIRED_FIELDS = ["目标页面", "监测时间", "变更类型"]
    STATUS_ORDER = ["已发现", "已确认", "已忽略", "已修复"]
    ACTION_RULES = {"确认变更": "已确认", "忽略变更": "已忽略"}
    NEGATIVE_ACTIONS = ["忽略变更"]
