"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DataSampleService(BaseModuleService):
    MODULE = "data_sample"
    ENTITY = "采样方案"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["方案名称", "采样方式", "采样比例", "数据来源", "最近采样时间"]
    REQUIRED_FIELDS = ["方案名称", "采样方式", "采样比例"]
    STATUS_ORDER = ["待采样", "已完成", "已过期"]
    ACTION_RULES = {"执行采样": "待采样", "更新方案": "待采样"}
    NEGATIVE_ACTIONS = []
