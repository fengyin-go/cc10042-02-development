"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class LogCollectorService(BaseModuleService):
    MODULE = "log_collector"
    ENTITY = "日志采集器"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["采集器名称", "日志路径", "解析模式", "输出Topic", "采集速率"]
    REQUIRED_FIELDS = ["采集器名称", "日志路径", "解析模式"]
    STATUS_ORDER = ["待启动", "运行中", "已停止", "异常"]
    ACTION_RULES = {"启动采集": "运行中", "停止采集": "已停止"}
    NEGATIVE_ACTIONS = []
