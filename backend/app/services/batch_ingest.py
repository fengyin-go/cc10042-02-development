"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BatchIngestService(BaseModuleService):
    MODULE = "batch_ingest"
    ENTITY = "接入任务"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["任务名称", "数据来源", "文件格式", "目标表", "分区策略"]
    REQUIRED_FIELDS = ["任务名称", "数据来源", "文件格式"]
    STATUS_ORDER = ["待接入", "接入中", "已入湖", "接入失败"]
    ACTION_RULES = {"启动接入": "接入中", "重新接入": "接入中"}
    NEGATIVE_ACTIONS = []
