"""分区质量核算：从分区接入数据计算有效行比例，出具分区校验结论与入湖回执。

数据质量校验模块原本只有应用表和阈值配置（质量规则），本服务补齐质量核算结果：

- 接入任务登记同一目标分区的应交文件与本期入湖时间，按（来源文件，行号）接收记录；
- 核算时分子、分母取自同一确认范围，空分区单列，不参与达标判定；
- 批量接入凭分区校验结论确认可入湖分区，入湖回执关联可复算的有效行比例、
  隔离明细与核算口径，下游当班人员据此判断此刻可领取范围、提交失败行补件；
- 补传或重试按（来源文件，行号）识别已处理记录，不重复入湖、不重复计入比例。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.store import store

CALIBER_TEMPLATE = (
    "有效行比例=确认范围内有效行数÷确认范围内接入总行数；"
    "确认范围=截至核算时刻已接收、按（来源文件，行号）去重后的本分区本期记录，"
    "分子与分母取自同一确认范围；"
    "空分区（确认范围0行）单列，不参与达标判定；"
    "补传或重试按（来源文件，行号）识别已处理记录，不重复入湖、不重复计入比例；"
    "本期质量阈值={threshold}，有效行比例达到阈值即判定分区达标。"
)


class QualityAccountingError(ValueError):
    """核算入参或前置条件不满足。"""


class TaskNotFoundError(QualityAccountingError):
    """接入任务不存在。"""


def _parse_time(value: Any, field: str = "时间") -> datetime:
    try:
        return datetime.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise QualityAccountingError(
            f"{field}应为 ISO 时间，如 2026-11-23T10:00:00，收到：{value!r}"
        ) from exc


def _parse_threshold(raw: Any) -> float | None:
    """把「80%」「80」「0.8」等阈值写法统一解析成 0~1 的小数。"""
    text = str(raw or "").strip().rstrip("%").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value > 1:
        value = value / 100.0
    if not 0 <= value <= 1:
        return None
    return value


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.2%}"


def _threshold_text(value: float) -> str:
    return f"{value * 100:g}%"


class QualityAccountingService:
    """分区质量核算引擎：接收、核算、出回执，状态与平台一致留在内存。"""

    def __init__(self) -> None:
        self._tasks: dict[int, dict[str, Any]] = {}
        self._period_thresholds: dict[str, float] = {}
        self._seq = 0

    # ---------- 阈值配置 ----------
    def set_period_threshold(self, period: str, threshold: Any) -> dict[str, Any]:
        """直接设置本期质量阈值；未设置时回退到数据质量校验模块的质量规则。"""
        value = _parse_threshold(threshold)
        if value is None:
            raise QualityAccountingError(f"阈值无法识别：{threshold!r}")
        self._period_thresholds[str(period)] = value
        return {"本期": str(period), "阈值": value, "阈值文本": _threshold_text(value)}

    def _resolve_threshold(self, task: dict[str, Any]) -> float:
        if task["本期"] in self._period_thresholds:
            return self._period_thresholds[task["本期"]]
        for row in store.rows("data_quality"):
            if str(row.get("应用表", "")).strip() == task["目标表"]:
                parsed = _parse_threshold(row.get("阈值"))
                if parsed is not None:
                    return parsed
        raise QualityAccountingError(
            f"目标表「{task['目标表']}」尚未配置有效行比例阈值，"
            "请先在数据质量校验模块登记质量规则（应用表+阈值），或设置本期质量阈值"
        )

    # ---------- 任务登记 ----------
    def register_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("任务名称") or "").strip()
        table = str(payload.get("目标表") or "").strip()
        period = str(payload.get("本期") or "").strip()
        deadline_raw = str(payload.get("入湖时间") or "").strip()
        if not all([name, table, period, deadline_raw]):
            raise QualityAccountingError("任务名称、目标表、本期、入湖时间均为必填")
        deadline = _parse_time(deadline_raw, "入湖时间")
        default_partition = str(payload.get("分区") or "").strip() or None
        expected: list[dict[str, str]] = []
        seen_files: set[str] = set()
        for item in payload.get("应交文件") or []:
            if isinstance(item, str):
                fname, partition = item.strip(), default_partition
            else:
                fname = str(item.get("文件") or "").strip()
                partition = str(item.get("分区") or "").strip() or default_partition
            if not fname:
                raise QualityAccountingError("应交文件存在空文件名")
            if not partition:
                raise QualityAccountingError(
                    f"应交文件「{fname}」未指定目标分区，且任务未设默认分区"
                )
            if fname in seen_files:
                raise QualityAccountingError(f"应交文件重复登记：{fname}")
            seen_files.add(fname)
            expected.append({"文件": fname, "分区": partition})
        if not expected:
            raise QualityAccountingError("至少登记一份应交文件")
        partitions = sorted({item["分区"] for item in expected})
        self._seq += 1
        task: dict[str, Any] = {
            "id": self._seq,
            "任务名称": name,
            "目标表": table,
            "本期": period,
            "入湖时间": deadline,
            "关联接入任务": payload.get("关联接入任务"),
            "应交文件": expected,
            "分区清单": partitions,
            # 确认范围：{(来源文件, 行号): {"有效", "原因", "到达时间"}}
            "records": {partition: {} for partition in partitions},
            "files": {},
            # 已入湖记录：{(来源文件, 行号)}，保证不重复入湖
            "lake": {partition: set() for partition in partitions},
            "accountings": [],
            "receipts": [],
        }
        self._tasks[task["id"]] = task
        return self.task_view(task)

    # ---------- 文件接收（补传/重试幂等） ----------
    def receive_file(self, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._get_task(task_id)
        fname = str(payload.get("文件") or "").strip()
        if not fname:
            raise QualityAccountingError("文件名必填")
        arrived = _parse_time(payload.get("到达时间") or "", "到达时间")
        rows = payload.get("行") or []
        expected = {item["文件"]: item for item in task["应交文件"]}
        if fname in expected:
            partition = expected[fname]["分区"]
            supplementary = False
        else:
            # 未登记的文件按补件接收，用于提交失败行的补件
            partition = str(payload.get("分区") or "").strip() or task["分区清单"][0]
            supplementary = True
            if partition not in task["分区清单"]:
                task["分区清单"].append(partition)
                task["分区清单"].sort()
                task["records"][partition] = {}
                task["lake"][partition] = set()
        records = task["records"][partition]
        accepted = duplicates = valid_new = invalid_new = 0
        for row in rows:
            try:
                row_no = int(row.get("行号"))
            except (TypeError, ValueError) as exc:
                raise QualityAccountingError(f"行号应为整数：{row!r}") from exc
            key = (fname, row_no)
            if key in records:
                # 按（来源文件，行号）识别已处理记录：不重复入湖、不重复计入比例
                duplicates += 1
                continue
            valid = bool(row.get("是否有效"))
            records[key] = {
                "有效": valid,
                "原因": str(row.get("失败原因") or "").strip(),
                "到达时间": arrived,
            }
            accepted += 1
            if valid:
                valid_new += 1
            else:
                invalid_new += 1
        info = task["files"].get(fname)
        if info is None:
            info = {
                "文件": fname,
                "分区": partition,
                "首次到达时间": arrived,
                "是否迟到": arrived > task["入湖时间"],
                "是否补件": supplementary,
                "接收行数": 0,
                "有效行数": 0,
                "重复跳过行数": 0,
                "首次计入核算": None,
            }
            task["files"][fname] = info
        info["最近到达时间"] = arrived
        info["接收行数"] += accepted
        info["有效行数"] += valid_new
        info["重复跳过行数"] += duplicates
        return {
            "文件": fname,
            "分区": partition,
            "是否补件": supplementary,
            "本次到达时间": arrived.isoformat(),
            "是否迟到": info["是否迟到"],
            "新接收行数": accepted,
            "其中有效": valid_new,
            "其中无效": invalid_new,
            "重复跳过行数": duplicates,
            "提示": "全部为已处理记录，未重复入湖、未重复计入比例" if rows and accepted == 0 else "",
        }

    # ---------- 核算与回执 ----------
    def run_accounting(
        self, task_id: int, trigger: str = "手动核算", as_of: str | None = None
    ) -> dict[str, Any]:
        task = self._get_task(task_id)
        ran_at = _parse_time(as_of, "核算时刻") if as_of else datetime.now()
        threshold = self._resolve_threshold(task)
        accounting_id = len(task["accountings"]) + 1
        partition_results: list[dict[str, Any]] = []
        empty_partitions: list[dict[str, Any]] = []
        quarantine: list[dict[str, Any]] = []
        for partition in task["分区清单"]:
            records = task["records"][partition]
            total = len(records)
            if total == 0:
                empty_partitions.append({
                    "分区": partition,
                    "应交文件": [
                        item["文件"] for item in task["应交文件"] if item["分区"] == partition
                    ],
                    "说明": "确认范围0行，空分区单列，不参与达标判定",
                })
                continue
            # 分子、分母取自同一确认范围
            valid = sum(1 for item in records.values() if item["有效"])
            ratio = valid / total
            conclusion = "达标" if ratio >= threshold else "不达标"
            by_file: dict[str, dict[str, Any]] = {}
            for (fname, row_no), item in sorted(records.items()):
                slot = by_file.setdefault(fname, {"文件": fname, "行数": 0, "有效行数": 0})
                slot["行数"] += 1
                if item["有效"]:
                    slot["有效行数"] += 1
                else:
                    quarantine.append({
                        "分区": partition,
                        "文件": fname,
                        "行号": row_no,
                        "原因": item["原因"] or "未通过质量校验",
                    })
            # 批量接入凭分区校验结论确认可入湖分区；已入湖记录不重复入湖
            confirmed = conclusion == "达标"
            new_lake = 0
            if confirmed:
                lake = task["lake"][partition]
                for key, item in records.items():
                    if item["有效"] and key not in lake:
                        lake.add(key)
                        new_lake += 1
            partition_results.append({
                "分区": partition,
                "确认范围总行数": total,
                "有效行数": valid,
                "无效行数": total - valid,
                "有效行比例": round(ratio, 4),
                "有效行比例文本": _pct(ratio),
                "本期质量阈值": threshold,
                "结论": conclusion,
                "确认可入湖": confirmed,
                "本次新增入湖行数": new_lake,
                "累计入湖行数": len(task["lake"][partition]),
                "复算": f"{valid}/{total}={_pct(ratio)}",
                "范围文件": list(by_file.values()),
            })
        for info in task["files"].values():
            if info["首次计入核算"] is None and info["接收行数"] > 0:
                info["首次计入核算"] = accounting_id
        claimable = [item["分区"] for item in partition_results if item["结论"] == "达标"]
        receipt = {
            "回执号": f"RCPT-{task_id:03d}-{accounting_id:02d}",
            "任务ID": task_id,
            "任务名称": task["任务名称"],
            "目标表": task["目标表"],
            "本期": task["本期"],
            "关联接入任务": task["关联接入任务"],
            "核算批次": accounting_id,
            "触发": trigger,
            "核算时刻": ran_at.isoformat(),
            "本期质量阈值": threshold,
            "本期质量阈值文本": _threshold_text(threshold),
            "核算口径": CALIBER_TEMPLATE.format(threshold=_threshold_text(threshold)),
            "分区结论": partition_results,
            "空分区": empty_partitions,
            "隔离明细": quarantine,
            "批量接入确认": {
                "依据": "分区校验结论",
                "可入湖分区": claimable,
                "不可入湖分区": [
                    item["分区"] for item in partition_results if item["结论"] != "达标"
                ],
            },
            "下游可领取": {
                "可领取分区": claimable,
                "说明": self._claimable_note(partition_results, empty_partitions, claimable),
            },
            "文件核算对应": [self._file_view(info) for info in task["files"].values()],
            "迟到影响": self._late_impacts(task),
        }
        task["accountings"].append({
            "核算批次": accounting_id,
            "触发": trigger,
            "核算时刻": ran_at.isoformat(),
            "回执号": receipt["回执号"],
            "分区结论": {item["分区"]: item["结论"] for item in partition_results},
        })
        task["receipts"].append(receipt)
        self._sync_quality_rules(task, receipt)
        return receipt

    def open_receipt(self, task_id: int, receipt_no: str | None = None) -> dict[str, Any]:
        task = self._get_task(task_id)
        if receipt_no is None:
            if not task["receipts"]:
                raise QualityAccountingError(f"任务 {task_id} 尚未核算，暂无入湖回执")
            return task["receipts"][-1]
        for receipt in task["receipts"]:
            if receipt["回执号"] == receipt_no:
                return receipt
        raise QualityAccountingError(f"回执 {receipt_no} 不存在")

    def list_receipts(self, task_id: int) -> list[dict[str, Any]]:
        return list(self._get_task(task_id)["receipts"])

    # ---------- 下游可领取范围 ----------
    def availability(self, task_id: int) -> dict[str, Any]:
        task = self._get_task(task_id)
        base = {
            "任务ID": task_id,
            "任务名称": task["任务名称"],
            "目标表": task["目标表"],
            "本期": task["本期"],
        }
        if not task["receipts"]:
            return {
                **base,
                "最新核算批次": None,
                "可领取分区": [],
                "分区状态": [],
                "空分区": [],
                "迟到影响": self._late_impacts(task),
                "说明": "尚未核算，下游暂无可领取分区。",
            }
        latest = task["receipts"][-1]
        return {
            **base,
            "最新核算批次": latest["核算批次"],
            "最新回执号": latest["回执号"],
            "可领取分区": latest["下游可领取"]["可领取分区"],
            "分区状态": [
                {
                    "分区": item["分区"],
                    "结论": item["结论"],
                    "有效行比例": item["有效行比例"],
                    "有效行比例文本": item["有效行比例文本"],
                    "本期质量阈值": item["本期质量阈值"],
                    "可领取": item["结论"] == "达标",
                    "累计入湖行数": item["累计入湖行数"],
                }
                for item in latest["分区结论"]
            ],
            "空分区": latest["空分区"],
            "迟到影响": self._late_impacts(task),
            "说明": latest["下游可领取"]["说明"],
        }

    # ---------- 文件与核算对应 ----------
    def file_map(self, task_id: int) -> list[dict[str, Any]]:
        task = self._get_task(task_id)
        arrived = task["files"]
        items: list[dict[str, Any]] = []
        for expected in task["应交文件"]:
            info = arrived.get(expected["文件"])
            if info is None:
                items.append({
                    "文件": expected["文件"],
                    "分区": expected["分区"],
                    "状态": "未到达",
                    "首次计入核算": "—",
                })
            else:
                items.append({**self._file_view(info), "状态": "已到达"})
        expected_names = {item["文件"] for item in task["应交文件"]}
        for fname, info in arrived.items():
            if fname not in expected_names:
                items.append({**self._file_view(info), "状态": "补件"})
        return items

    # ---------- 任务视图 ----------
    def get_task(self, task_id: int) -> dict[str, Any]:
        return self.task_view(self._get_task(task_id))

    def list_tasks(self) -> list[dict[str, Any]]:
        return [self.task_view(task) for task in self._tasks.values()]

    def task_view(self, task: dict[str, Any]) -> dict[str, Any]:
        latest = task["receipts"][-1] if task["receipts"] else None
        return {
            "id": task["id"],
            "任务名称": task["任务名称"],
            "目标表": task["目标表"],
            "本期": task["本期"],
            "入湖时间": task["入湖时间"].isoformat(),
            "关联接入任务": task["关联接入任务"],
            "分区清单": list(task["分区清单"]),
            "应交文件": [dict(item) for item in task["应交文件"]],
            "已收文件": [info["文件"] for info in task["files"].values()],
            "核算次数": len(task["accountings"]),
            "最新回执号": latest["回执号"] if latest else None,
            "最新结论": (
                {item["分区"]: item["结论"] for item in latest["分区结论"]} if latest else {}
            ),
            "湖内行数": {partition: len(lake) for partition, lake in task["lake"].items()},
        }

    # ---------- 内部 ----------
    def _get_task(self, task_id: int) -> dict[str, Any]:
        task = self._tasks.get(int(task_id))
        if task is None:
            raise TaskNotFoundError(f"接入任务 {task_id} 不存在")
        return task

    @staticmethod
    def _file_view(info: dict[str, Any]) -> dict[str, Any]:
        return {
            "文件": info["文件"],
            "分区": info["分区"],
            "首次到达时间": info["首次到达时间"].isoformat(),
            "是否迟到": info["是否迟到"],
            "是否补件": info["是否补件"],
            "接收行数": info["接收行数"],
            "有效行数": info["有效行数"],
            "重复跳过行数": info["重复跳过行数"],
            "首次计入核算": (
                info["首次计入核算"] if info["首次计入核算"] is not None else "尚未计入"
            ),
        }

    @staticmethod
    def _claimable_note(
        partition_results: list[dict[str, Any]],
        empty_partitions: list[dict[str, Any]],
        claimable: list[str],
    ) -> str:
        parts = [
            f"下游当前可领取分区：{'、'.join(claimable)}"
            if claimable else
            "下游当前无可领取分区"
        ]
        for item in partition_results:
            if item["结论"] == "达标":
                continue
            note = (
                f"分区{item['分区']}最新核算{item['结论']}"
                f"（有效行比例{item['有效行比例文本']}，阈值{_threshold_text(item['本期质量阈值'])}），暂停领取"
            )
            if item["累计入湖行数"]:
                note += f"；已入湖{item['累计入湖行数']}行待补件核算达标后恢复"
            parts.append(note)
        if empty_partitions:
            parts.append("空分区单列：" + "、".join(item["分区"] for item in empty_partitions))
        return "；".join(parts) + "。"

    def _late_impacts(self, task: dict[str, Any]) -> list[dict[str, Any]]:
        impacts: list[dict[str, Any]] = []
        late_files = [
            info for info in task["files"].values()
            if info["是否迟到"] and info["接收行数"] > 0
        ]
        if not late_files:
            return impacts
        late_names_by_partition: dict[str, set[str]] = {}
        for info in late_files:
            late_names_by_partition.setdefault(info["分区"], set()).add(info["文件"])
        for info in late_files:
            partition = info["分区"]
            records = task["records"][partition]
            total = len(records)
            valid = sum(1 for item in records.values() if item["有效"])
            late_names = late_names_by_partition[partition]
            rest = {key: item for key, item in records.items() if key[0] not in late_names}
            rest_total = len(rest)
            rest_valid = sum(1 for item in rest.values() if item["有效"])
            current = valid / total if total else None
            without = rest_valid / rest_total if rest_total else None
            impacts.append({
                "文件": info["文件"],
                "分区": partition,
                "迟到行数": info["接收行数"],
                "当前有效行比例": None if current is None else round(current, 4),
                "当前有效行比例文本": _pct(current),
                "剔除迟到文件后比例": None if without is None else round(without, 4),
                "剔除迟到文件后比例文本": _pct(without),
                "说明": (
                    f"迟到文件「{info['文件']}」{info['接收行数']}行已计入确认范围，"
                    f"分区有效行比例{_pct(current)}（剔除迟到文件后{_pct(without)}）；"
                    "迟到记录将保留在确认范围参与后续每次核算，"
                    "可按隔离明细提交补件后重新核算"
                ),
            })
        return impacts

    @staticmethod
    def _sync_quality_rules(task: dict[str, Any], receipt: dict[str, Any]) -> None:
        """把核算结果回写到数据质量校验模块的质量规则（应用表+阈值配置）。"""
        summary = "；".join(
            f"{item['分区']}有效行比例{item['有效行比例文本']}{item['结论']}"
            for item in receipt["分区结论"]
        ) or "空分区，未出结论"
        for row in store.rows("data_quality"):
            if str(row.get("应用表", "")).strip() != task["目标表"]:
                continue
            row["最近校验结果"] = f"{receipt['核算时刻']} 核算#{receipt['核算批次']}：{summary}"
            conclusions = {item["结论"] for item in receipt["分区结论"]}
            if "不达标" in conclusions:
                row["status"] = "未通过"
            elif conclusions:
                row["status"] = "已通过"


quality_accounting = QualityAccountingService()
