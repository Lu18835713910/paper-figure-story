#!/usr/bin/env python3
"""数值核验：来源门禁 + 主张级均值比较（rc.2）。

两部分，边界不同，别混：

A. 门禁 `gate()` —— 判断"该不该核 + 登记簿是否是权威那一份"。
   六态：NOT_APPLICABLE / EVIDENCE_REQUIRED / ANCHOR_REQUIRED /
         STOP_MANIFEST_NOT_ANCHORED / STOP_REGISTRY_NOT_CANONICAL / AVAILABLE

B. 主张级比较 `evaluate()` —— 只在门禁通过后使用。
   拿调用方提供的主张规格 + 数据登记簿，按显式规则比较均值，输出 SUPPORTS / REFUTES / INSUFFICIENT。

B 的底线：
- 只比**均值**。均值差异**不是**统计显著性，更**不是**因果；每条结果都带这句边界。
- 每条结论必须能追到：指标、组、对照、期次、单位、比较方向、用到的登记簿单元格。
- 不绑定任何论文的组名/时期/路径；轴顺序与单元格键名都由调用方数据给出。
- 不猜：缺单元格就 INSUFFICIENT，不插值、不拿邻组顶替。

关于"独立锚点"：`--manifest` 由调用方提供，单凭它不足以证明登记簿没被现场替换
（否则谁都能现造一个 manifest 再宣布自己权威）。因此必须另给 `--manifest-anchor`，
即 **manifest 文件本身的 SHA256，且必须来自本次运行之外的独立记录**（冻结清单、审计回执等）。
不给锚点 → ANCHOR_REQUIRED；锚点不符 → STOP_MANIFEST_NOT_ANCHORED。
"""
from __future__ import annotations

import argparse
import hashlib
import math
import json
from pathlib import Path

SCHEMA = "rld_numeric_v2"
CLAIMS_SCHEMA = "rld_numeric_claims_v1"

BOUNDARY = ("均值比较结论；不构成统计显著性检验，也不构成因果推断。"
            "INSUFFICIENT 表示登记簿缺少所需单元格，不代表主张错误。")

PREDICATES = ("ordered_by_series", "extremum_at_last",
              "below_comparator_all_series", "above_comparator_all_series")


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------- A. 门禁
def gate(unit, registry_path=None, manifest_path=None, manifest_anchor=None):
    if (unit or {}).get("kind") != "NUMERIC_COMPARISON":
        return {"status": "NOT_APPLICABLE", "reason": "unit makes no numeric comparison"}
    if not registry_path or not manifest_path:
        return {"status": "EVIDENCE_REQUIRED", "reason": "canonical registry/manifest not supplied"}
    rp, mp = Path(registry_path), Path(manifest_path)
    if not rp.is_file() or not mp.is_file():
        return {"status": "EVIDENCE_REQUIRED", "reason": "registry or manifest file not found"}
    if not manifest_anchor:
        return {"status": "ANCHOR_REQUIRED",
                "reason": "manifest 由调用方提供，需另给独立锚点（manifest 的 SHA256），"
                          "否则无法证明登记簿未被现场替换"}
    actual_manifest = _sha(mp)
    if actual_manifest.lower() != str(manifest_anchor).strip().lower():
        return {"status": "STOP_MANIFEST_NOT_ANCHORED",
                "reason": "manifest sha256 differs from the independent anchor",
                "expected_anchor": manifest_anchor, "actual_manifest_sha256": actual_manifest}
    try:
        man = _load(mp)
    except (OSError, ValueError) as exc:
        return {"status": "STOP_REGISTRY_NOT_CANONICAL", "reason": "manifest unreadable: %s" % exc}
    expected = man.get("canonical_registry_sha256")
    if not expected:
        return {"status": "STOP_REGISTRY_NOT_CANONICAL",
                "reason": "manifest does not pin canonical_registry_sha256"}
    actual = _sha(rp)
    if actual != expected:
        return {"status": "STOP_REGISTRY_NOT_CANONICAL",
                "reason": "registry sha256 differs from canonical manifest",
                "expected": expected, "actual": actual}
    reg = _load(rp)
    return {"status": "AVAILABLE", "registry_cells": len(reg.get("cells", [])),
            "registry_sha256": actual, "manifest_sha256": actual_manifest,
            "source_pdf_sha256": reg.get("source_pdf_sha256"),
            "note": "门禁通过；主张级比较见 evaluate()"}


# ---------------------------------------------------------------- B. 主张级比较
def _cell_index(registry, keys):
    idx = {}
    for c in registry.get("cells", []):
        idx[(c.get(keys["metric"]), c.get(keys["group"]), c.get(keys["series"]))] = \
            c
    return idx


def evaluate(claims_doc, registry, tol=1e-9):
    """按主张规格逐条比较均值。返回 {"results": [...], "summary": {...}}。"""
    keys = claims_doc.get("cells_key") or {"metric": "metric", "group": "treatment",
                                           "series": "stage", "value": "value"}
    axis_cfg = claims_doc.get("axis") or {}
    idx = _cell_index(registry, keys)
    axis = axis_cfg.get("order") or sorted({k[2] for k in idx if k[2] is not None})
    results = []

    for claim in claims_doc.get("claims", []):
        metric = claim.get("metric")
        group = claim.get("group")
        pred = claim.get("predicate")
        comp_group = claim.get("comparator_group")
        used, missing = [], []

        def get(g, s):
            key = (metric, g, s)
            cell = idx.get(key)
            val = cell.get(keys["value"]) if cell else None
            if (type(val) in (int, float) and math.isfinite(val)
                    and (not claim.get("unit") or cell.get("unit") == claim["unit"])):
                used.append({**cell, "metric": metric, "group": g, "series": s, "value": val})
                return val
            missing.append("%s/%s/%s" % (metric, g, s))
            return None

        values = [get(group, s) for s in axis]
        comp_values = [get(comp_group, s) for s in axis] if comp_group else []

        rule, verdict, detail = None, "INSUFFICIENT", {}
        if pred not in PREDICATES:
            detail = {"reason": "unsupported predicate: %s" % pred}
        elif not values or any(v is None for v in values):
            detail = {"reason": "missing registry cells", "missing": missing}
        elif pred in ("below_comparator_all_series", "above_comparator_all_series"):
            if not comp_group:
                detail = {"reason": "predicate needs comparator_group"}
            elif any(v is None for v in comp_values):
                detail = {"reason": "missing comparator cells", "missing": missing}
            else:
                if pred.startswith("below"):
                    ok = all(a < b for a, b in zip(values, comp_values))
                    sign = "<"
                else:
                    ok = all(a > b for a, b in zip(values, comp_values))
                    sign = ">"
                rule = "all(v_series %s c_series) over %d series" % (sign, len(axis))
                verdict = "SUPPORTS" if ok else "REFUTES"
                detail = {"comparator_group": comp_group}
        elif pred == "ordered_by_series":
            direction = claim.get("direction", "decrease")
            if direction not in ("increase", "decrease"):
                detail = {"reason": "unsupported direction"}
            elif len(values) < 2:
                detail = {"reason": "need >=2 series points"}
            else:
                if direction == "increase":
                    ok = all(b > a for a, b in zip(values, values[1:]))
                else:
                    ok = all(b < a for a, b in zip(values, values[1:]))
                rule = "strictly %s across %d series" % (direction, len(axis))
                verdict = "SUPPORTS" if ok else "REFUTES"
        else:
            extremum = claim.get("extremum")
            if extremum not in ("min", "max"):
                detail = {"reason": "extremum must be min|max"}
            else:
                target = min(values) if extremum == "min" else max(values)
                ok = abs(values[-1] - target) <= tol
                rule = "last series value == %s of series" % extremum
                verdict = "SUPPORTS" if ok else "REFUTES"

        results.append({
            "claim_id": claim.get("claim_id"), "metric": metric, "group": group,
            "comparator_group": comp_group, "predicate": pred,
            "unit": claim.get("unit"), "direction": claim.get("direction"),
            "extremum": claim.get("extremum"),
            "axis": axis, "values": values,
            "comparator_values": comp_values or None,
            "rule": rule, "verdict": verdict, "detail": detail,
            "cells_used": used, "missing_cells": missing,
            "source": claim.get("source"),
            "boundary": BOUNDARY,
        })

    summary = {v: sum(1 for r in results if r["verdict"] == v)
               for v in ("SUPPORTS", "REFUTES", "INSUFFICIENT")}
    return {"schema": SCHEMA, "claims_schema": claims_doc.get("schema"),
            "axis": axis, "tol": tol, "summary": summary,
            "results": results, "boundary": BOUNDARY}


def main(argv=None):
    ap = argparse.ArgumentParser(description="RLD numeric gate and claim-level mean comparison.")
    ap.add_argument("--unit", type=Path, help="单元 JSON（仅做门禁）")
    ap.add_argument("--claims", type=Path, help="主张规格 JSON（做主张级比较）")
    ap.add_argument("--registry", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--manifest-anchor",
                    help="manifest 的 SHA256，须来自本次运行之外的独立记录")
    ap.add_argument("--tol", type=float, default=1e-9)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    out = {"schema": SCHEMA}
    if a.unit:
        out["gate"] = gate(_load(a.unit), a.registry, a.manifest, a.manifest_anchor)
    if a.claims:
        g = gate({"kind": "NUMERIC_COMPARISON"}, a.registry, a.manifest, a.manifest_anchor)
        out["gate"] = g
        out["evaluation"] = (evaluate(_load(a.claims), _load(a.registry), a.tol)
                             if g["status"] == "AVAILABLE"
                             else {"blocked_by_gate": g["status"]})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"gate": out.get("gate", {}).get("status"),
                      "summary": out.get("evaluation", {}).get("summary"),
                      "out": str(a.out)}, ensure_ascii=False))
    return 2 if a.claims and out["gate"]["status"] != "AVAILABLE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
