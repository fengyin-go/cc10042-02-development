"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ExtractionLogService(BaseModuleService):
    MODULE = "extraction_log"
    ENTITY = "执行日志"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["执行时间", "关联项目", "状态", "耗时", "出错代码行"]
    REQUIRED_FIELDS = ["执行时间", "关联项目", "状态"]
    STATUS_ORDER = ["成功", "部分成功", "执行失败", "超时"]
    ACTION_RULES = {"查看详情": "执行失败", "重试任务": "执行失败"}
    NEGATIVE_ACTIONS = []
