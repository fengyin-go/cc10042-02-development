"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DataQualityService(BaseModuleService):
    MODULE = "data_quality"
    ENTITY = "质量规则"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["规则名称", "校验维度", "阈值", "应用表", "最近校验结果"]
    REQUIRED_FIELDS = ["规则名称", "校验维度", "阈值"]
    STATUS_ORDER = ["待校验", "已通过", "未通过", "已忽略"]
    ACTION_RULES = {"执行校验": "待校验", "忽略规则": "已忽略"}
    NEGATIVE_ACTIONS = ["忽略规则"]
