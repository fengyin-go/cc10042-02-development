#!/usr/bin/env python3
"""分区质量核算场景演示（对应需求描述的全过程）：

  1. 把本期质量阈值设为 80%（写入数据质量校验模块的质量规则：应用表+阈值）；
  2. 接入任务登记同一目标分区的两份应交文件和本期入湖时间；
  3. 到时只收到第一份（100 条全有效）→ 到时核算 → 打开入湖回执①，
     核对下游此刻可领取的范围；
  4. 第二份迟到补交（100 条仅 10 条有效）→ 补交核算 → 打开入湖回执②，
     有效行比例被拉到阈值以下，核对下游可领取范围与迟到影响；
  5. 重传第一份，确认按（来源文件，行号）去重，不重复入湖、不重复计入比例；
  6. 附：空分区单列演示。

运行：cd backend && python3 scripts/demo_quality_accounting.py
（只依赖标准库与 app 包，不需要启动服务。）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.batch_ingest import BatchIngestService
from app.services.data_quality import DataQualityService
from app.services.quality_accounting import QualityAccountingService
from app.store import store

TABLE = "dwd_user_behavior_di"
PARTITION = "dt=2026-11-23"
PERIOD = "2026-11-23"
DEADLINE = "2026-11-23T10:00:00"  # 本期入湖时间
FILE1 = "behavior_part1.csv"
FILE2 = "behavior_part2.csv"


def make_rows(count: int, valid_upto: int) -> list[dict]:
    reasons = ["关键字段为空", "值域越界", "格式非法"]
    rows = []
    for i in range(1, count + 1):
        ok = i <= valid_upto
        rows.append({
            "行号": i,
            "是否有效": ok,
            "失败原因": "" if ok else reasons[i % len(reasons)],
        })
    return rows


def truncated(obj, key="隔离明细", keep=5):
    """打印时截断超长明细，回执本体保留全量。"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == key and isinstance(v, list) and len(v) > keep:
                out[k] = v[:keep] + [f"…… 共{len(v)}条，仅展示前{keep}条"]
            else:
                out[k] = truncated(v, key, keep)
        return out
    if isinstance(obj, list):
        return [truncated(v, key, keep) for v in obj]
    return obj


def show(title: str, obj) -> None:
    print(f"\n{'─' * 8} {title} {'─' * 8}")
    print(json.dumps(truncated(obj), ensure_ascii=False, indent=2))


def main() -> None:
    svc = QualityAccountingService()

    print("=" * 72)
    print("分区质量核算场景演示：有效行比例核算、分区校验结论与入湖回执")
    print("=" * 72)

    # ① 本期质量阈值设为 80%：走数据质量校验模块的阈值配置（质量规则=应用表+阈值）
    rule, missing = DataQualityService().create_entry({
        "规则名称": "用户行为明细-有效行比例",
        "校验维度": "有效行比例",
        "阈值": "80%",
        "应用表": TABLE,
        "最近校验结果": "—",
    })
    assert not missing, missing
    show("① 阈值配置：本期质量阈值设为 80%（质量规则）", rule)

    # ② 登记接入任务：同一目标分区的两份应交文件 + 本期入湖时间
    ingest_task, _ = BatchIngestService().create_entry({
        "任务名称": "用户行为日志批量接入",
        "数据来源": "行为日志OSS目录",
        "文件格式": "CSV",
        "目标表": TABLE,
        "分区策略": "按日分区",
    })
    task = svc.register_task({
        "任务名称": "用户行为日志批量接入",
        "目标表": TABLE,
        "本期": PERIOD,
        "入湖时间": DEADLINE,
        "分区": PARTITION,
        "应交文件": [FILE1, FILE2],
        "关联接入任务": ingest_task["id"],
    })
    show("② 登记接入任务（两份应交文件，同一目标分区，本期入湖时间 10:00）", task)
    task_id = task["id"]

    # ③ 到时前只收到第一份：100 条全有效
    recv1 = svc.receive_file(task_id, {
        "文件": FILE1, "到达时间": "2026-11-23T09:30:00", "行": make_rows(100, 100),
    })
    show("③ 到时前收到第一份（100 条全有效）", recv1)
    assert recv1["新接收行数"] == 100 and recv1["其中有效"] == 100
    assert recv1["是否迟到"] is False

    # ④ 到时核算 → 打开入湖回执①
    receipt1 = svc.run_accounting(task_id, trigger="到时核算", as_of=DEADLINE)
    show("④ 到时核算 → 入湖回执①（打开回执）", receipt1)
    p1 = receipt1["分区结论"][0]
    assert (p1["确认范围总行数"], p1["有效行数"]) == (100, 100)
    assert p1["有效行比例"] == 1.0 and p1["结论"] == "达标"
    assert p1["确认可入湖"] is True and p1["本次新增入湖行数"] == 100
    assert receipt1["批量接入确认"]["可入湖分区"] == [PARTITION]
    assert receipt1["本期质量阈值"] == 0.8 and "80%" in receipt1["核算口径"]
    avail1 = svc.availability(task_id)
    show("④ 下游当班视角（到时）：此刻可领取范围", avail1)
    assert avail1["可领取分区"] == [PARTITION], "到时：第一份单独达标，分区可领取"

    # ⑤ 第二份迟到补交：100 条仅 10 条有效
    recv2 = svc.receive_file(task_id, {
        "文件": FILE2, "到达时间": "2026-11-23T11:20:00", "行": make_rows(100, 10),
    })
    show("⑤ 第二份迟到补交（100 条仅 10 条有效）", recv2)
    assert recv2["是否迟到"] is True and recv2["其中无效"] == 90

    # ⑥ 补交核算 → 打开入湖回执②：110/200=55% < 80%，结论翻转为不达标
    receipt2 = svc.run_accounting(task_id, trigger="补交核算", as_of="2026-11-23T11:25:00")
    show("⑥ 补交核算 → 入湖回执②（打开回执）", receipt2)
    p2 = receipt2["分区结论"][0]
    assert (p2["确认范围总行数"], p2["有效行数"]) == (200, 110)
    assert p2["有效行比例"] == 0.55 and p2["结论"] == "不达标"
    assert p2["确认可入湖"] is False and p2["本次新增入湖行数"] == 0
    assert p2["累计入湖行数"] == 100, "回执①已入湖的 100 行不重复入湖"
    assert receipt2["批量接入确认"]["可入湖分区"] == []
    assert len(receipt2["隔离明细"]) == 90
    assert all(item["文件"] == FILE2 for item in receipt2["隔离明细"])
    impact = receipt2["迟到影响"][0]
    assert impact["文件"] == FILE2 and impact["剔除迟到文件后比例"] == 1.0
    # 回执可复算：按范围文件汇总应还原分子分母
    scope = receipt2["分区结论"][0]["范围文件"]
    assert sum(f["行数"] for f in scope) == 200
    assert sum(f["有效行数"] for f in scope) == 110
    avail2 = svc.availability(task_id)
    show("⑥ 下游当班视角（补交后）：此刻可领取范围与迟到影响", avail2)
    assert avail2["可领取分区"] == [], "补交后：比例被迟到文件拉到阈值以下，无可领取数据"

    # 两份文件各对应哪次核算
    fmap = svc.file_map(task_id)
    show("⑥ 两份文件各对应哪次核算", fmap)
    first_seen = {item["文件"]: item["首次计入核算"] for item in fmap}
    assert first_seen[FILE1] == 1 and first_seen[FILE2] == 2

    # ⑦ 重传第一份：按（来源文件，行号）识别已处理记录，不重复入湖、不重复计入
    recv1_again = svc.receive_file(task_id, {
        "文件": FILE1, "到达时间": "2026-11-23T11:40:00", "行": make_rows(100, 100),
    })
    show("⑦ 重传第一份（100 条原样重发）", recv1_again)
    assert recv1_again["新接收行数"] == 0 and recv1_again["重复跳过行数"] == 100
    receipt3 = svc.run_accounting(task_id, trigger="重试核算", as_of="2026-11-23T11:41:00")
    p3 = receipt3["分区结论"][0]
    show("⑦ 重试核算 → 入湖回执③（确认比例与入湖行数不变）", {
        "回执号": receipt3["回执号"],
        "分区结论": receipt3["分区结论"],
        "下游可领取": receipt3["下游可领取"],
    })
    assert (p3["确认范围总行数"], p3["有效行数"]) == (200, 110), "重传不重复计入比例"
    assert p3["有效行比例"] == 0.55
    assert p3["本次新增入湖行数"] == 0 and p3["累计入湖行数"] == 100, "重传不重复入湖"

    # ⑧ 空分区单列：另一任务（另一张应用表）登记了应交文件但到时一行未收
    rule2, _ = DataQualityService().create_entry({
        "规则名称": "店铺维度-有效行比例",
        "校验维度": "有效行比例",
        "阈值": "80%",
        "应用表": "dim_shop_di",
        "最近校验结果": "—",
    })
    assert rule2 is not None
    task2 = svc.register_task({
        "任务名称": "店铺维度批量接入",
        "目标表": "dim_shop_di",
        "本期": PERIOD,
        "入湖时间": DEADLINE,
        "应交文件": [{"文件": "dim_20261124.csv", "分区": "dt=2026-11-24"}],
    })
    receipt_empty = svc.run_accounting(task2["id"], trigger="到时核算", as_of=DEADLINE)
    show("⑧ 空分区单列（登记了应交文件但确认范围 0 行）", receipt_empty)
    assert receipt_empty["分区结论"] == []
    assert [item["分区"] for item in receipt_empty["空分区"]] == ["dt=2026-11-24"]
    assert receipt_empty["下游可领取"]["可领取分区"] == []

    # 质量规则（阈值配置）已回写最近校验结果
    rule_row = next(r for r in store.rows("data_quality") if r.get("应用表") == TABLE)
    show("⑨ 质量规则回写（应用表+阈值配置 → 最近校验结果）", rule_row)
    assert "核算#3" in rule_row["最近校验结果"] and rule_row["status"] == "未通过"

    print("\n" + "=" * 72)
    print("全部断言通过：")
    print("  · 到时：第一份 100/100=100.00% ≥ 80% → 分区达标，下游可领取", [PARTITION])
    print("  · 补交后：110/200=55.00% < 80% → 结论不达标，下游无可领取数据")
    print("  · 两份文件各对应核算：第一份→核算#1（到时核算），第二份→核算#2（补交核算）")
    print("  · 重传第一份：0 行新接收、100 行重复跳过，比例仍 55.00%，入湖仍 100 行")
    print("  · 空分区单列，不参与达标判定；核算口径与 80% 阈值已写入每份回执")
    print("=" * 72)


if __name__ == "__main__":
    main()
