"""业务路由汇总：质量核算等专用路由在前，通用资源路由兜底。"""
from __future__ import annotations

from app.routers import quality_accounting, resource

ROUTERS = [quality_accounting, resource]
