"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AntiCrawlService(BaseModuleService):
    MODULE = "anti_crawl"
    ENTITY = "反爬策略"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["策略名称", "代理池来源", "请求头模板", "Cookie管理", "验证码识别方式"]
    REQUIRED_FIELDS = ["策略名称", "代理池来源", "请求头模板"]
    STATUS_ORDER = ["待生效", "已生效", "已过期"]
    ACTION_RULES = {"启用策略": "已生效", "过期策略": "已过期"}
    NEGATIVE_ACTIONS = []
