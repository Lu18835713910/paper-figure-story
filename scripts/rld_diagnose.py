#!/usr/bin/env python3
"""RLD v1.2 候选：语义归一化诊断 + PFS 干预证据核查（支持现场派生论证单元）。

与冻结 R1.15 的差异（全部在 RLD 侧，不触碰 PFS）：
1. 因果判定不再用"关键词出现在整段文本里"，而是走 rld_semantic 的语义枚举，
   只有 CAUSAL_ASSERTION 子句才可能触发因果疑点。
2. 触发前后都要查 PFS 结构：该结论的证据是否连到登记的干预实体与对照比较。
   - 有干预且连到读出 -> 不报（记录 SUPPORTED_BY_REGISTERED_INTERVENTION）
   - 有干预但未连到该结论 -> 归因 PFS_RECONSTRUCTION（重建缺口，非论文问题）
   - 模型内确无干预实体 -> 归因 PAPER_REASONING（由相关性推因果）
3. 语义未覆盖（脚本不在覆盖面/空文本）不再静默返回 0，而是显式上报
   SEMANTIC_TYPE_UNRECOGNIZED，并在 coverage 里计数。

CLI 全部走参数，不含任何论文专属的硬编码路径。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rld_semantic as sem  # noqa: E402

import rld_numeric  # 同包数值门禁（六态）
import rld_units    # 同包 PFS→RLD 论证单元派生

REQUIRED = {
    "ACTUAL_PROTOCOL_ORDER": (),
    "SHARED_PROTOCOL": (),
    "SCIENTIFIC_EVIDENCE": ("observations", "claim"),
    "AUTHOR_INTERPRETATION": ("claim", "supporting_evidence"),
    "AUTHOR_ARGUMENT": ("question", "design"),
}


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def unit_text(u, stmt=None):
    """诊断文本。

    冻结提取器把逻辑节点 label 写入 claim.value，真正的 PFS 声明语句不在里面，
    导致声明句的因果措辞对诊断不可见。这里补上 statement_ids 里 role 为
    interpretation/result 的 PFS 原文语句（仍只用 PFS 已登记文本，不新增内容）。
    """
    parts = []
    ids = (u.get("pfs_anchors") or {}).get("statement_ids") or []
    if stmt:
        for sid in ids:
            st = stmt.get(sid) or {}
            if st.get("role") in ("interpretation", "result") and st.get("text"):
                parts.append(st["text"])
    parts.append(u["claim"]["value"] or "")
    parts += u["observations"]["statements"]
    parts += u["design"]["statements"]
    seen, out = set(), []
    for x in parts:
        x = (x or "").strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return "\n".join(out)


def inbound_evidence(logic, node_id):
    nm = {n["id"]: n for n in logic["nodes"]}
    out = []
    for e in logic["edges"]:
        if e.get("to") != node_id:
            continue
        src = nm.get(e.get("from")) or {}
        if src.get("identity") == "SCIENTIFIC_EVIDENCE":
            out.append({"edge_id": e["id"], "from": e["from"], "type": e.get("type"),
                        "rationale": e.get("rationale"),
                        "entity_ids": src.get("source_entity_ids", [])})
    return out


def intervention_context(net, logic, unit, hops=2):
    """查 PFS 是否登记了与该结论相关的干预与对照。

    从该单元的证据实体出发，沿网络边（无向）走 <=hops 跳，看能否到达干预实体，
    以及该邻域内是否存在登记的对照比较边。只看结构，不看措辞。
    """
    nid = unit["pfs_anchors"]["logic_node_id"]
    nm = {n["id"]: n for n in logic["nodes"]}
    seed = set(unit["pfs_anchors"].get("entity_ids") or [])
    seed |= set((nm.get(nid) or {}).get("source_entity_ids") or [])
    for ev in inbound_evidence(logic, nid):
        seed |= set(ev.get("entity_ids") or [])

    kinds = {n["id"]: n.get("kind") for n in net["nodes"]}
    interventions = {i for i, k in kinds.items() if k == "intervention"}

    adj = {}
    edges = net.get("edges", [])
    for e in edges:
        a, b = e.get("from"), e.get("to")
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    reach, frontier = set(seed), set(seed)
    for _ in range(hops):
        nxt = set()
        for x in frontier:
            nxt |= adj.get(x, set())
        nxt -= reach
        reach |= nxt
        frontier = nxt

    inter_reach = sorted(interventions & reach)
    in_scope = sorted(interventions & seed)
    # 只有原文明确报告的对照比较才算数：协议级推断（inferred_needs_review）不计，
    # 否则"补一条推断关系"就能把因果疑点清掉，等于放宽门禁。
    compares = [e["id"] for e in edges
                if e.get("type") == "compares"
                and e.get("certainty") == "paper_reported"
                and ({e.get("from"), e.get("to")} & set(inter_reach))]
    precedes = [e["id"] for e in edges
                if e.get("type") == "experimental_precedes"
                and {e.get("from"), e.get("to")} <= (set(inter_reach) | set(seed))]
    linked_readouts = [e["id"] for e in edges
                       if e.get("type") in ("evidence_supports", "compares", "experimental_precedes",
                                            "data_depends_on")
                       and ({e.get("from"), e.get("to")} & set(inter_reach))
                       and any(kinds.get(x) == "evidence" for x in (e.get("from"), e.get("to")))]

    if inter_reach and compares and linked_readouts:
        verdict = "SUPPORTED_BY_REGISTERED_INTERVENTION"
    elif inter_reach:
        verdict = "INTERVENTION_NOT_LINKED_TO_READOUT"
    elif interventions:
        verdict = "PAPER_HAS_INTERVENTION_ELSEWHERE"
    else:
        verdict = "NO_INTERVENTION_IN_MODEL"
    return {
        "verdict": verdict,
        "interventions_in_unit_scope": in_scope,
        "interventions_reachable": inter_reach,
        "control_comparison_edges": compares,
        "protocol_edges": precedes,
        "intervention_readout_edges": linked_readouts,
        "interventions_anywhere_in_model": sorted(interventions),
        "reach_hops": hops,
    }


def chain_check(unit, identity):
    need = REQUIRED.get(identity, ())
    present = {
        "question": unit["question"]["status"] == "EXPLICIT_IN_PFS",
        "design": unit["design"]["status"] == "EXPLICIT_IN_PFS",
        "observations": unit["observations"]["status"] == "EXPLICIT_IN_PFS",
        "claim": True,
        "supporting_evidence": bool(unit.get("_inbound_evidence")),
    }
    return [k for k in need if not present[k]], list(need), identity


def finding(code, dim, sev, evidence, text, alt, missing, change, attr, action, anchors, unit_id=None):
    return {"unit_id": unit_id, "check": code, "dimension": dim, "severity": sev, "evidence": evidence,
            "finding": text, "competing_explanation": alt, "missing_evidence": missing,
            "what_would_change": change, "attribution": attr, "action": action,
            "reversible": True, "pfs_anchors": anchors}


def diagnose(net, logic, units_doc, registry=None, manifest=None, manifest_anchor=None):
    findings, summary, attr = [], {"SCIENTIFIC_LOGIC": 0, "LANGUAGE_LOGIC": 0, "EXPRESSION_LOGIC": 0}, {}
    nm = {n["id"]: n for n in logic["nodes"]}
    stmt = {s["id"]: s for s in net["statements"]}
    semantic, causal_disp, numeric, suppressed = {}, {}, {}, []

    limitation_statements = [s for s in net["statements"] if s.get("role") == "limitation"]
    lim_units = [u["unit_id"] for u in units_doc["units"]
                 if u["limits"]["status"] == "INSUFFICIENT_GRAPH_INFORMATION"]
    if lim_units:
        f = finding("LIMIT_NOT_LINKED_TO_LOGIC", "EXPRESSION_LOGIC", "MAJOR",
                    {"units_without_limits": len(lim_units),
                     "limitation_statements_in_network": len(limitation_statements)},
                    "逻辑层无节点挂 limitation 语句，而网络中存在限制语句——属重建遗漏。",
                    "限制可能属于实验层而非结论层。",
                    ["logic node -> limitation statement 的成员关系"],
                    "补齐成员关系后本条撤销。", "PFS_RECONSTRUCTION", "下阶段补边。",
                    {"logic_node_id": "*"})
        findings.append(f); summary["EXPRESSION_LOGIC"] += 1
        attr["PFS_RECONSTRUCTION"] = attr.get("PFS_RECONSTRUCTION", 0) + 1

    for u in units_doc["units"]:
        lid = u["pfs_anchors"]["logic_node_id"]
        identity = (nm.get(lid) or {}).get("identity")
        anchors = u["pfs_anchors"]
        uid = u["unit_id"]
        u["_inbound_evidence"] = inbound_evidence(logic, lid)

        # ---- 语言层归一化 ----
        s = sem.classify_text(unit_text(u, stmt))
        semantic[u["unit_id"]] = {"dominant": s["dominant"], "counts": s["counts"],
                                  "coverage": s["coverage"], "clauses": s["clauses"][:12]}

        if not s["coverage"]["assessable"]:
            findings.append({**finding(
                "SEMANTIC_TYPE_UNRECOGNIZED", "LANGUAGE_LOGIC", "MINOR",
                {"coverage": s["coverage"], "unit": u["unit_id"]},
                "该单元文本超出语义层覆盖面（脚本或空文本），因果判定未执行。"
                "这不是'没有问题'，而是'未评估'。",
                "文本可能极短或含未覆盖字符集；不影响该单元的其它维度检查。",
                ["人工阅读原文确认该单元是否存在因果断言"],
                "补充对应字符集的语义规则后本条转由常规判定处理。",
                "RLD_COVERAGE_GAP", "标记为未评估，不计入 NO_ISSUE。", anchors, uid)})
            summary["LANGUAGE_LOGIC"] += 1
            attr["RLD_COVERAGE_GAP"] = attr.get("RLD_COVERAGE_GAP", 0) + 1
            causal_disp[u["unit_id"]] = "UNASSESSED"
        else:
            ctx = intervention_context(net, logic, u)
            if s["asserted"]:
                if ctx["verdict"] == "SUPPORTED_BY_REGISTERED_INTERVENTION":
                    causal_disp[u["unit_id"]] = "ASSERTED_WITH_REGISTERED_INTERVENTION_SUPPORT"
                else:
                    # 只有"该结论自身有干预但没连到读出"才归重建缺口；
                    # 模型别处存在干预不足以替该结论开脱，否则会系统性压掉 PAPER_REASONING。
                    # 只有"模型里根本没有干预实体"才可能归到论文侧；
                    # 模型有干预但没连到该结论，只能说明重建缺边，不得据此指责论文。
                    attribution = ("PAPER_REASONING"
                                   if ctx["verdict"] == "NO_INTERVENTION_IN_MODEL"
                                   else "PFS_RECONSTRUCTION")
                    causal_disp[u["unit_id"]] = "ASSERTED_WITHOUT_INTERVENTIONAL_SUPPORT:" + ctx["verdict"]
                    txt = ("该单元存在断言型因果表述（语义枚举 " + s["dominant"] +
                           "），但 PFS 中该结论的证据未连到登记的干预与对照："
                           + ctx["verdict"] + "。")
                    if attribution == "PFS_RECONSTRUCTION":
                        alt = ("论文可能确有干预实验，只是重建时未把干预边连到该结论；"
                               "PFS 缺边不等于论文缺实验。")
                        miss = ["该结论到干预实体/对照比较的 PFS 边"]
                        act = "补干预到读出的关系边，不改编论文措辞。"
                    else:
                        alt = ("作者可能把相关性证据当作机制证据使用；此类写法在讨论段常见，"
                               "也可能原文另有未入库的干预实验。")
                        miss = ["对该变量的干预实验（敲低/过表达/中和）", "独立群体验证"]
                        act = "建议作者降级措辞；不改 PFS 模型。"
                    findings.append({**finding(
                        "CAUSAL_UPGRADE", "SCIENTIFIC_LOGIC", "MAJOR",
                        {"claim": u["claim"]["value"], "semantic": s["dominant"],
                         "asserted_clauses": [c["clause"] for c in s["clauses"]
                                              if c["type"] == "CAUSAL_ASSERTION"][:4],
                         "intervention_context": ctx},
                        txt, alt, miss,
                        "若 PFS 补上干预边，或原文该处为描述性/假说性用法，本条撤销。",
                        attribution, act, anchors, uid)})
                    summary["SCIENTIFIC_LOGIC"] += 1
                    attr[attribution] = attr.get(attribution, 0) + 1
            else:
                causal_disp[u["unit_id"]] = "NOT_ASSERTED:" + s["dominant"]
                # 旧关键词规则会在这里报因果；记录"被语义层抑制"的告警，供人工复核，不静默丢弃
                had_marker = any(c["hits"].get("causal") for c in s["clauses"])
                if had_marker and s["dominant"] in ("DESCRIPTIVE_REGULATION", "NEGATED_CAUSAL",
                                                    "CAUSAL_HYPOTHESIS", "UNCERTAIN"):
                    suppressed.append({
                        "unit_id": u["unit_id"], "semantic": s["dominant"],
                        "clauses": [c["clause"][:200] for c in s["clauses"]
                                    if c["hits"].get("causal")][:3],
                        "why_not_reported": {
                            "DESCRIPTIVE_REGULATION": "被动/无施动者的描述性用法，非因果断言",
                            "NEGATED_CAUSAL": "同一子句内已明确否定该因果",
                            "CAUSAL_HYPOTHESIS": "以假说/检验框架提出，未作断言",
                            "UNCERTAIN": "对因果的证椟性保留，未作断言",
                        }[s["dominant"]],
                        "note": "旧 R1.15 关键词规则会对该单元报 CAUSAL_UPGRADE；本条记录抑制理由，需人工判断是否接受",
                    })

        # ---- 角色感知链完整性（沿用 R1.15 语义）----
        missing, need, _ = chain_check(u, identity)
        if missing:
            findings.append({**finding(
                "CHAIN_INCOMPLETE", "EXPRESSION_LOGIC",
                "MINOR" if len(missing) <= 2 else "MAJOR",
                {"identity": identity, "required_by_identity": need, "missing": missing},
                f"{identity} 节点缺少其身份要求的环节：{', '.join(missing)}",
                "该节点可能只是论证起点，观察由下游节点承担。",
                ["把 purpose/method 语句并入相应逻辑节点"],
                "按节点身份补齐后本条撤销。",
                "PFS_RECONSTRUCTION", "在 overlay 中补对应关联。", anchors, uid)})
            summary["EXPRESSION_LOGIC"] += 1
            attr["PFS_RECONSTRUCTION"] = attr.get("PFS_RECONSTRUCTION", 0) + 1

        # ---- 比较基准 ----
        if u["comparison_conditions"]["status"] != "EXPLICIT_IN_PFS":
            hit = next((st for st in u["observations"]["statements"] + u["design"]["statements"]
                        if any(w in st.lower() for w in ("compared", "versus", "vs.", "than",
                                                         "高于", "低于", "相比", "较"))), None)
            if hit:
                findings.append({**finding(
                    "COMPARISON_BASELINE_UNSTATED", "LANGUAGE_LOGIC", "MINOR",
                    {"statement": hit[:160]},
                    "语句含比较词但该单元无比较基准字段，读者需回原文确认基准。",
                    "基准可能在同一段前一语句中，已被上文覆盖。",
                    ["binding 层的 comparator 字段提升到论证层"],
                    "把 binding 的 comparator 提升到论证单元后本条消失。",
                    "PFS_RECONSTRUCTION", "报告层引用 comparator。", anchors, uid)})
                summary["LANGUAGE_LOGIC"] += 1
                attr["PFS_RECONSTRUCTION"] = attr.get("PFS_RECONSTRUCTION", 0) + 1

        # ---- 证据角色混用 ----
        pages = sorted({r.get("physical_page") for r in u["source_refs"] if r.get("physical_page")})
        if len(pages) > 1 and u["kind"] == "NUMERIC_COMPARISON":
            findings.append({**finding(
                "EVIDENCE_ROLE_MIXING", "EXPRESSION_LOGIC", "MINOR",
                {"pages": pages, "n_statements": len(anchors["statement_ids"])},
                "同一单元同时引用作者陈述页与数据页，读者难以区分'作者说的'与'测到的'。",
                "PFS 允许实体跨页取证；页面并列本身不是错误。",
                ["报告层按 role 分组展示"],
                "按 role 分组后本条降为无需修改。",
                "PFS_RECONSTRUCTION", "报告里按 role 分组。", anchors, uid)})
            summary["EXPRESSION_LOGIC"] += 1
            attr["PFS_RECONSTRUCTION"] = attr.get("PFS_RECONSTRUCTION", 0) + 1

        numeric[u["unit_id"]] = numeric_check(u, registry, manifest, manifest_anchor)

    assessed = sum(1 for v in semantic.values() if v["coverage"]["assessable"])
    res = {
        "schema": "rld_semantic_diagnostics_v1",
        "candidate": "RLD v1.2.0-rc.2 (review candidate; NOT an official release)",
        "semantic_vocab": sem.VOCAB_VERSION,
        "mode": "logic_first" + ("_with_numeric" if registry else "_no_registry"),
        "units": len(units_doc["units"]),
        "findings": findings,
        "by_dimension": summary,
        "by_attribution": attr,
        "numeric": numeric,
        "semantic": semantic,
        "causal_disposition": causal_disp,
        "suppressed_causal": suppressed,
        "coverage": {
            "units_total": len(units_doc["units"]),
            "assessed": assessed,
            "unassessed": len(units_doc["units"]) - assessed,
            "note": "unassessed>0 表示语义层未覆盖，已显式上报 SEMANTIC_TYPE_UNRECOGNIZED，不当作 NO_ISSUE",
        },
        "no_issue_units": [u["unit_id"] for u in units_doc["units"]
                           if not any(f.get("unit_id") == u["unit_id"] for f in findings)
                           and semantic.get(u["unit_id"], {}).get("coverage", {}).get("assessable")],
        "boundary": {"scientific_accuracy": "NOT_ESTIMABLE",
                     "note": "诊断是候选意见，不是科学认证；每条均可撤销",
                     "pfs_modified": False},
    }
    for f in findings:
        if f.get("unit_id") is None:
            f["unit_id"] = "*"
    return res


def numeric_check(u, registry, manifest, anchor=None):
    """数值门禁委托给 rld_numeric.gate（六态；主张级比较在 rld_numeric.evaluate）。"""
    return rld_numeric.gate(u, registry, manifest, anchor)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--units", type=Path,
                    help="预生成的论证单元；省略时由 --index/--network/--logic 现场派生")
    ap.add_argument("--index", type=Path, help="Scientific Index（派生论证单元时必需）")
    ap.add_argument("--network", required=True, type=Path)
    ap.add_argument("--logic", required=True, type=Path)
    ap.add_argument("--registry", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--manifest-anchor",
                    help="manifest 的 SHA256，须来自本次运行之外的独立记录")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    if a.units is not None:
        units_doc = load_json(a.units)
        derivation = {"mode": "provided", "path": str(a.units)}
    else:
        if a.index is None:
            ap.error("需要 --units，或同时给 --index 以便从 PFS 工件派生论证单元")
        try:
            units_doc = rld_units.build(*rld_units.validated_inputs(a.index, a.network, a.logic))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            ap.error(str(exc))
        derivation = {"mode": rld_units.DERIVATION,
                      "units": units_doc["counts"]["units"],
                      "with_claim": units_doc["counts"]["units_with_claim"]}

    res = diagnose(load_json(a.network), load_json(a.logic), units_doc,
                   a.registry, a.manifest, a.manifest_anchor)
    res["unit_derivation"] = derivation
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("units:", res["units"], "| findings:", len(res["findings"]))
    print("by dimension:", res["by_dimension"])
    print("by attribution:", res["by_attribution"])
    print("coverage:", res["coverage"])
    print("causal disposition:", {k: v for k, v in list(res["causal_disposition"].items())[:6]})
    print("suppressed causal (needs review):", len(res["suppressed_causal"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
