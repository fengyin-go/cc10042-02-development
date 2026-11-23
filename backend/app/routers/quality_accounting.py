"""分区质量核算接口：登记接入任务、接收文件、发起核算、打开入湖回执、查询可领取范围。

路由层只做参数校验和异常转换，核算口径与状态流转都在
app.services.quality_accounting 里。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.quality_accounting import (
    QualityAccountingError,
    TaskNotFoundError,
    quality_accounting,
)

router = APIRouter(prefix="/api/quality-accounting", tags=["分区质量核算"])


class RowPayload(BaseModel):
    行号: int
    是否有效: bool
    失败原因: str = ""


class FilePayload(BaseModel):
    文件: str
    到达时间: str
    分区: str | None = None
    行: list[RowPayload] = Field(default_factory=list)


class TaskPayload(BaseModel):
    任务名称: str
    目标表: str
    本期: str
    入湖时间: str
    分区: str | None = None
    应交文件: list[Any] = Field(default_factory=list)
    关联接入任务: int | None = None


class AccountingPayload(BaseModel):
    触发: str = "手动核算"
    核算时刻: str | None = None


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QualityAccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks")
def register_task(payload: TaskPayload) -> dict[str, Any]:
    """登记接入任务：同一目标分区的应交文件清单与本期入湖时间。"""
    task = _guard(quality_accounting.register_task, payload.model_dump())
    return {"ok": True, "message": "接入任务已登记", "entry": task}


@router.get("/tasks")
def list_tasks() -> dict[str, Any]:
    items = quality_accounting.list_tasks()
    return {"items": items, "total": len(items)}


@router.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict[str, Any]:
    return _guard(quality_accounting.get_task, task_id)


@router.post("/tasks/{task_id}/files")
def receive_file(task_id: int, payload: FilePayload) -> dict[str, Any]:
    """接收文件行明细；补传/重试按（来源文件，行号）去重，不重复入湖。"""
    result = _guard(quality_accounting.receive_file, task_id, payload.model_dump())
    return {"ok": True, "message": "文件已接收", "entry": result}


@router.post("/tasks/{task_id}/accounting")
def run_accounting(task_id: int, payload: AccountingPayload) -> dict[str, Any]:
    """发起质量核算（到时核算/补交核算/重试核算），出具分区校验结论与入湖回执。"""
    receipt = _guard(
        quality_accounting.run_accounting, task_id, payload.触发, payload.核算时刻
    )
    return {"ok": True, "message": f"核算完成，回执号{receipt['回执号']}", "receipt": receipt}


@router.get("/tasks/{task_id}/receipt")
def open_receipt(task_id: int, receipt_no: str | None = None) -> dict[str, Any]:
    """打开入湖回执：默认最新一份，也可按回执号打开历史核算的回执。"""
    return _guard(quality_accounting.open_receipt, task_id, receipt_no)


@router.get("/tasks/{task_id}/receipts")
def list_receipts(task_id: int) -> dict[str, Any]:
    items = _guard(quality_accounting.list_receipts, task_id)
    return {"items": items, "total": len(items)}


@router.get("/tasks/{task_id}/availability")
def availability(task_id: int) -> dict[str, Any]:
    """下游当班人员视角：此刻可领取的分区范围，以及迟到文件对后续结论的影响。"""
    return _guard(quality_accounting.availability, task_id)


@router.get("/tasks/{task_id}/files")
def file_map(task_id: int) -> dict[str, Any]:
    """应交/已收文件清单，以及每份文件首次计入哪一次核算。"""
    items = _guard(quality_accounting.file_map, task_id)
    return {"items": items, "total": len(items)}
