"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ExportCenterService(BaseModuleService):
    MODULE = "export_center"
    ENTITY = "导出任务"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["导出范围", "目标格式", "导出时间", "文件大小", "导出状态"]
    REQUIRED_FIELDS = ["导出范围", "目标格式", "导出时间"]
    STATUS_ORDER = ["排队中", "导出中", "已完成", "导出失败"]
    ACTION_RULES = {"开始导出": "导出中", "重新导出": "导出中"}
    NEGATIVE_ACTIONS = []
