"""Project a reviewed Research Logic model into a SIMPLE story-A page.

This is a display layer only: it never edits the scientific model. Each story
unit binds one or more original node ids, and each displayed link either cites
original relation ids or is explicitly registered as an approved narrative
inference with its own sources.

The renderer reuses render_logic.draw_scene, so arrows, endpoint retreat and
editability behave exactly like the A/B decks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

UNDIRECTED = {"parallel", "comparison", "shared_workflow"}
MIN_BODY_PT = 16.0


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate_story(model, story):
    errors = []
    nodes = {n["id"]: n for n in model["nodes"]}
    edges = {e["id"]: e for e in model["edges"]}
    units = story.get("units", [])
    # The narrative grouping is authored/reviewed by the Agent or the user; this
    # module only validates and renders it, and is not an automatic story writer.
    if not (story.get("review") or {}).get("reviewed_by"):
        errors.append("STORY_REVIEW_REQUIRED")
    if not 4 <= len(units) <= 8:
        errors.append("UNIT_COUNT_OUT_OF_RANGE:%d" % len(units))
    owner, ids = {}, set()
    for u in units:
        if not u.get("rect") or not u.get("title"):
            errors.append("UNIT_INCOMPLETE:" + str(u.get("id")))
        for nid in u.get("node_ids", []):
            if nid not in nodes:
                errors.append("UNKNOWN_NODE:" + nid)
            if nid in owner:
                errors.append("NODE_IN_TWO_UNITS:" + nid)
            owner[nid] = u["id"]
            ids.add(nid)
    omitted = set(story.get("omitted", {}).keys())
    missing = sorted(n for n in nodes if n not in ids and n not in omitted)
    if missing:
        errors.append("NODES_NOT_DISPLAYED:" + ",".join(missing))
    for l in story.get("links", []):
        rid = l.get("relation_ids") or []
        if rid:
            types = set()
            for r in rid:
                if r not in edges:
                    errors.append("UNKNOWN_RELATION:" + r)
                    continue
                e = edges[r]
                types.add(e["type"])
                if owner.get(e["from"]) != l.get("from") or owner.get(e["to"]) != l.get("to"):
                    errors.append("RELATION_UNIT_MISMATCH:" + r)
            if l.get("arrow") and (types & UNDIRECTED):
                errors.append("CAUSAL_ARROW_ON_UNDIRECTED:" + ",".join(sorted(rid)))
            # A single display link must not mix a symmetric/shared relation with
            # a directed evidence relation: one arrowhead would then claim a
            # direction for the undirected member.
            if types and (types & UNDIRECTED) and (types - UNDIRECTED):
                errors.append("MIXED_RELATION_SEMANTICS:" + ",".join(sorted(rid)))
        elif not (l.get("narrative") and l.get("basis")):
            errors.append("LINK_WITHOUT_PROVENANCE")
    return {"valid": not errors, "errors": errors,
            "unit_count": len(units), "covered_nodes": len(ids),
            "total_nodes": len(nodes)}


def _wrap(text, width_px, size, bold=False):
    """render_logic.text() does not wrap; break the string by measured width."""
    from presentation_typography import measure
    out = []
    for para in str(text).split("\n"):
        cur = ""
        for ch in para:
            if not cur or measure(cur + ch, size, bold) <= width_px - 4:
                cur += ch
            else:
                out.append(cur)
                cur = ch
        out.append(cur)
    return "\n".join(out)


def _fit_text(text, width_px, height_px, base_px, min_px=18, bold=False):
    """Largest size whose wrapped lines fit the box (renderer-tolerant)."""
    size = base_px
    while size >= min_px:
        wrapped = _wrap(text, width_px, size, bold)
        lines = wrapped.count("\n") + 1
        if lines * size * 1.28 <= height_px:
            return size, wrapped
        size -= 1
    return min_px, _wrap(text, width_px, min_px, bold)


def _text(eid, value, rect, size, bold=False, color="#18365C", align="left",
          node_ids=None):
    e = {"id": eid, "kind": "text", "position": dict(zip(
        ("left", "top", "width", "height"), rect)), "text": value,
        "font_size": size, "bold": bold, "color": color, "align": align}
    if node_ids:
        e["logic_node_id"] = node_ids[0]
        e["source_node_ids"] = list(node_ids)
    return e


def _rect(eid, rect, fill="#FFFFFF", stroke="#B8CBE6"):
    return {"id": eid, "kind": "rect", "position": dict(zip(
        ("left", "top", "width", "height"), rect)), "fill": fill, "stroke": stroke}


def build_scene(model, story):
    """Build a render_logic-compatible scene (display layer)."""
    check = validate_story(model, story)
    if not check["valid"]:
        raise ValueError("STORY_INVALID: " + json.dumps(check["errors"], ensure_ascii=False))
    canvas = story.get("canvas", {"width": 1280, "height": 622})
    W, H = canvas["width"], canvas["height"]
    nodes = {n["id"]: n for n in model["nodes"]}
    edges = {e["id"]: e for e in model["edges"]}
    els, conns = [], []

    # No full-canvas fill rect: draw_scene paints connectors BEFORE elements,
    # so a background rect here would cover every arrow.
    for u in story["units"]:
        x, y, w, h = u["rect"]
        fill = u.get("fill", "#F4F8FD")
        accent = u.get("accent", "#174994")
        els.append(_rect(u["id"] + "_card", [x, y, w, h], fill, "#D7E1F0"))
        els.append(_rect(u["id"] + "_bar", [x, y, 7, h], accent, accent))
        els.append(_text(u["id"] + "_label", u.get("label", ""), [x + 20, y + 12, w - 36, 24],
                         15, True, accent))
        t_size, t_txt = _fit_text(u["title"], w - 40, 62, u.get("title_px", 27), 20, True)
        els.append(_text(u["id"] + "_title", t_txt, [x + 20, y + 40, w - 36, 62],
                         t_size, True, "#17345E", node_ids=u["node_ids"]))
        subunits = u.get("subunits") or []
        if not subunits:
            b_size, b_txt = _fit_text(u["body"], w - 40, h - 124, u.get("body_px", 23), 18)
            els.append(_text(u["id"] + "_body", b_txt, [x + 20, y + 108, w - 36, h - 124],
                             b_size, False, "#40536B", node_ids=u["node_ids"]))
        else:
            # Unit hosts parallel sub-cards; its own body is the short caption.
            if u.get("body"):
                b_size, b_txt = _fit_text(u["body"], w - 40, 44, 20, 17)
                els.append(_text(u["id"] + "_body", b_txt, [x + 20, y + 104, w - 36, 44],
                                 b_size, False, "#40536B", node_ids=u["node_ids"]))
        for s in subunits:
            sx, sy, sw, sh = s["rect"]
            els.append(_rect(s["id"] + "_card", [sx, sy, sw, sh], "#FFFFFF", "#B8CBE6"))
            st_size, st_txt = _fit_text(s["title"], sw - 30, 30, 20, 16, True)
            els.append(_text(s["id"] + "_title", st_txt, [sx + 14, sy + 8, sw - 26, 30],
                             st_size, True, "#174994", node_ids=s["node_ids"]))
            sb_size, sb_txt = _fit_text(s["body"], sw - 30, sh - 50, s.get("body_px", 22), 17)
            els.append(_text(s["id"] + "_body", sb_txt, [sx + 14, sy + 42, sw - 26, sh - 52],
                             sb_size, False, "#40536B", node_ids=s["node_ids"]))
        if u.get("note"):
            els.append(_text(u["id"] + "_note", u["note"],
                             [x + 20, y + h - 34, w - 36, 26], 16, False, "#61748A"))
    if story.get("legend"):
        lx, ly, lw, lh = story["legend"]["rect"]
        els.append(_text(story["id"] + "_legend", story["legend"]["text"],
                         [lx, ly, lw, lh], 15, False, "#61748A"))

    for l in story.get("links", []):
        a = next(u for u in story["units"] if u["id"] == l["from"])
        b = next(u for u in story["units"] if u["id"] == l["to"])
        ax, ay, aw, ah = a["rect"]
        bx, by, bw, bh = b["rect"]
        if abs((ay + ah / 2) - (by + bh / 2)) < 60:
            x1, y1 = (ax + aw, ay + ah / 2) if bx > ax else (ax, ay + ah / 2)
            x2 = bx if bx > ax else bx + bw
            y2 = by + bh / 2
        else:
            x1, y1 = ax + aw / 2, (ay + ah if by > ay else ay)
            x2 = bx + bw / 2
            y2 = by if by > ay else by + bh
        rid = l.get("relation_ids") or []
        undirected = bool(rid) and all(edges[r]["type"] in UNDIRECTED for r in rid)
        conns.append({
            "id": l.get("id", l["from"] + "_" + l["to"]),
            "identity": l.get("identity", "SCIENTIFIC_EVIDENCE"),
            "relation_type": (edges[rid[0]]["type"] if rid else l.get("layer", "narrative")),
            "points": [[x1, y1], [x2, y2]],
            "arrow": bool(l.get("arrow")) and not undirected,
            "dashed": bool(l.get("dashed", undirected)),
            "color": l.get("color", "#8FA3BF" if undirected else "#174994"),
            "stroke_width": l.get("stroke_width", 2.2 if not undirected else 1.6),
            "source_logic_relation_id": (rid[0] if rid else None),
            "from_node": a["node_ids"][0], "to_node": b["node_ids"][0],
        })

    scene = {
        "id": story["id"], "title": story.get("title", ""), "elements": els,
        "connectors": conns,
        "coverage": {"view": "A", "scope": "story"},
        "citation": story.get("citation", ""),
        "logic_snapshot": model["snapshot"],
        "source_logic_node_ids": sorted({n for u in story["units"] for n in u["node_ids"]}),
        "source_logic_relation_ids": sorted({r for l in story.get("links", [])
                                             for r in (l.get("relation_ids") or [])}),
        "notes": {"scientific_question": story.get("title", ""),
                  "logic_source_ids": sorted({r for u in story["units"]
                                              for n in u["node_ids"]
                                              for r in nodes[n].get("source_ids", [])}),
                  "story_units": len(story["units"])},
    }
    product = {"width": W, "height": H, "kind": "story", "profile": "balanced",
               "slides": [scene]}
    scale = min(12.633 / (W / 96.0), 6.15 / (H / 96.0))
    body_pt = story["units"][0].get("body_px", 22) * 0.75 * scale
    return product, scene, {"scale": round(scale, 4), "body_pt_on_main": round(body_pt, 2),
                            "min_body_pt_ok": body_pt >= MIN_BODY_PT}


def mapping_table(model, story):
    nodes = {n["id"]: n for n in model["nodes"]}
    edges = {e["id"]: e for e in model["edges"]}
    rows = []
    for u in story["units"]:
        for nid in u["node_ids"]:
            n = nodes[nid]
            rows.append({"unit": u["id"], "unit_title": u["title"], "node": nid,
                         "node_title": n["title"], "identity": n["identity"],
                         "source_ids": n["source_ids"]})
    links = []
    for l in story.get("links", []):
        rid = l.get("relation_ids") or []
        links.append({"from": l["from"], "to": l["to"],
                      "relation_ids": rid,
                      "relation_types": [edges[r]["type"] for r in rid],
                      "layer": "registered_relation" if rid else "narrative_inference",
                      "narrative": bool(l.get("narrative")),
                      "basis": l.get("basis", []),
                      "arrow": bool(l.get("arrow"))})
    return {"story_id": story["id"], "model_snapshot": model["snapshot"],
            "unit_count": len(story["units"]), "units": rows, "links": links}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--story", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--main-pptx")
    ap.add_argument("--page", type=int)
    ap.add_argument("--main-output")
    ap.add_argument("--deck", action="store_true", help="also write a standalone story deck")
    a = ap.parse_args(argv)
    from pptx import Presentation
    from pptx.util import Inches
    import render_logic as rr

    model, story = load(a.model), load(a.story)
    product, scene, info = build_scene(model, story)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "story.plan.json").write_text(json.dumps(product, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    (out / "story_mapping.json").write_text(
        json.dumps(mapping_table(model, story), ensure_ascii=False, indent=1), encoding="utf-8")
    result = {"validation": validate_story(model, story), "render_info": info,
              "unit_count": len(story["units"]),
              "nodes_covered": len(scene["source_logic_node_ids"]),
              "relations_cited": len(scene["source_logic_relation_ids"]),
              "outdir": str(out)}
    if a.deck:
        prs = Presentation()
        prs.slide_width = Inches(product["width"] / 96)
        prs.slide_height = Inches(product["height"] / 96)
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        rr.draw_scene(sl, product, scene)
        f = out / "story_A.pptx"
        prs.save(str(f))
        result["deck"] = str(f)
    if a.main_pptx:
        if not (a.main_output and a.page):
            raise ValueError("MAIN_OUTPUT_AND_PAGE_REQUIRED")
        prs = Presentation(a.main_pptx)
        sl = prs.slides[a.page - 1]
        if any(s.shape_type == 13 for s in sl.shapes):
            raise ValueError("MAIN_LOGIC_SLOT_CONTAINS_FIGURE")
        old_title = next((s.text for s in sl.shapes
                          if s.name == "PFS_TITLE" and s.has_text_frame), "")
        for s in list(sl.shapes):
            sl.shapes._spTree.remove(s._element)
        rr.text(sl, "PFS_TITLE", story.get("title") or old_title or "",
                [Inches(.45), Inches(.15), prs.slide_width - Inches(.9), Inches(.5)], 32, True)
        rr.draw_scene(sl, product, scene,
                      (Inches(.35), Inches(.8),
                       prs.slide_width - Inches(.7), prs.slide_height - Inches(1.35)),
                      omit_scene_title=True)
        prs.save(a.main_output)
        result["main_output"] = a.main_output
    (out / "story_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
