"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SourceRegistryService(BaseModuleService):
    MODULE = "source_registry"
    ENTITY = "数据源"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["数据源名称", "源类型", "连接配置", "认证方式", "最近连通时间"]
    REQUIRED_FIELDS = ["数据源名称", "源类型", "连接配置"]
    STATUS_ORDER = ["待验证", "已连通", "连通失败", "已停用"]
    ACTION_RULES = {"验证连通": "待验证", "停用源": "已停用"}
    NEGATIVE_ACTIONS = ["停用源"]
