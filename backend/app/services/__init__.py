"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.crawl_project import CrawlProjectService
from app.services.page_parser import PageParserService
from app.services.field_extractor import FieldExtractorService
from app.services.anti_crawl import AntiCrawlService
from app.services.data_dedupe import DataDedupeService
from app.services.result_audit import ResultAuditService
from app.services.rate_limiter import RateLimiterService
from app.services.scheduler import SchedulerService
from app.services.rpa_workflow import RpaWorkflowService
from app.services.batch_ingest import BatchIngestService
from app.services.data_quality import DataQualityService
from app.services.log_collector import LogCollectorService
from app.services.proxy_pool import ProxyPoolService
from app.services.format_adapter import FormatAdapterService
from app.services.extraction_log import ExtractionLogService
from app.services.page_change import PageChangeService
from app.services.data_sample import DataSampleService
from app.services.export_center import ExportCenterService
from app.services.source_registry import SourceRegistryService
from app.services.retry_policy import RetryPolicyService

SERVICES: dict[str, BaseModuleService] = {
    "crawl_project": CrawlProjectService(),
    "page_parser": PageParserService(),
    "field_extractor": FieldExtractorService(),
    "anti_crawl": AntiCrawlService(),
    "data_dedupe": DataDedupeService(),
    "result_audit": ResultAuditService(),
    "rate_limiter": RateLimiterService(),
    "scheduler": SchedulerService(),
    "rpa_workflow": RpaWorkflowService(),
    "batch_ingest": BatchIngestService(),
    "data_quality": DataQualityService(),
    "log_collector": LogCollectorService(),
    "proxy_pool": ProxyPoolService(),
    "format_adapter": FormatAdapterService(),
    "extraction_log": ExtractionLogService(),
    "page_change": PageChangeService(),
    "data_sample": DataSampleService(),
    "export_center": ExportCenterService(),
    "source_registry": SourceRegistryService(),
    "retry_policy": RetryPolicyService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)
