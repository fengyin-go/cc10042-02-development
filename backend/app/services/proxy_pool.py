"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ProxyPoolService(BaseModuleService):
    MODULE = "proxy_pool"
    ENTITY = "代理节点"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["代理地址", "地理位置", "响应延迟", "可用状态", "今日使用次数"]
    REQUIRED_FIELDS = ["代理地址", "地理位置", "响应延迟"]
    STATUS_ORDER = ["可用", "不可用", "已禁用"]
    ACTION_RULES = {"检测可用": "可用", "禁用节点": "已禁用"}
    NEGATIVE_ACTIONS = []
