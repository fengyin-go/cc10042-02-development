"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CrawlProjectService(BaseModuleService):
    MODULE = "crawl_project"
    ENTITY = "采集项目"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["项目名称", "目标站点", "采集频率", "并发线程数", "负责人"]
    REQUIRED_FIELDS = ["项目名称", "目标站点", "采集频率"]
    STATUS_ORDER = ["草稿", "运行中", "已暂停", "已结束"]
    ACTION_RULES = {"启动采集": "运行中", "暂停采集": "已暂停", "结束项目": "已结束"}
    NEGATIVE_ACTIONS = []
