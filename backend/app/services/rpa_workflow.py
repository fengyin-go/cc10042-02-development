"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RpaWorkflowService(BaseModuleService):
    MODULE = "rpa_workflow"
    ENTITY = "工作流"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["流程名称", "操作步骤序列", "目标应用", "等待策略", "异常处理"]
    REQUIRED_FIELDS = ["流程名称", "操作步骤序列", "目标应用"]
    STATUS_ORDER = ["草稿", "已发布", "运行中", "已归档"]
    ACTION_RULES = {"发布流程": "已发布", "启动运行": "运行中"}
    NEGATIVE_ACTIONS = []
