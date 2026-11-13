#!/usr/bin/env python3
"""RLD 语义归一化层（R1.21 候选，替代 R1.15 的英文关键词判定）。

设计要点
--------
1. **枚举化，不靠加词**：先把断言切成子句，在每个子句里识别"因果载体"，
   再判定该因果是否被否定/仅作假说/仅作不确定表述，最后落到固定枚举：

       CAUSAL_ASSERTION        断言因果（"促进/导致/drives/promotes"）
       CAUSAL_HYPOTHESIS       以假说或检验框架提出（whether/may/hypothesize/是否/假设）
       NEGATED_CAUSAL          明确否定因果（did not promote/并未促进/no evidence that）
       CORRELATION_ONLY        只表述相关（associated with/呈正相关）
       DESCRIPTIVE_REGULATION  描述性"受调控"（is actively regulated / 受…调控，无施动者）
       UNCERTAIN               对已述因果的证椟性保留（suggest/appears/likely/提示）
       NO_CAUSAL_CONTENT       已评估，确无因果内容
       UNASSESSED_LANGUAGE     文本脚本或内容超出本层覆盖面，**不得**当作"无问题"

2. **否定作用域**：否定词只在同一子句内、且位于因果载体之前（回看窗口内）才生效。
   "X promotes Y, but Z was not changed" 不会把前半句误判为否定。

3. **绝不静默返回 0**：未覆盖脚本、空文本、以及"有内容但识别不出类型"的情况
   一律标 `UNASSESSED_LANGUAGE` 或 `NO_CAUSAL_CONTENT` 并显式计数，
   由诊断器决定是否作为覆盖缺口上报。

本模块只做语言层归一化，不做科学裁决；科学裁决见 rld_r121.py 的干预证据检查。
"""
from __future__ import annotations

import re

VOCAB_VERSION = "rld-semantic-vocab-1"

SEMANTIC_TYPES = (
    "CAUSAL_ASSERTION",
    "CAUSAL_HYPOTHESIS",
    "NEGATED_CAUSAL",
    "CORRELATION_ONLY",
    "DESCRIPTIVE_REGULATION",
    "UNCERTAIN",
    "NO_CAUSAL_CONTENT",
    "UNASSESSED_LANGUAGE",
)

# 判定优先级：先排否定与假说，避免"并未促进"被当成"促进"
PRIORITY = ("NEGATED_CAUSAL", "CAUSAL_HYPOTHESIS", "UNCERTAIN",
            "DESCRIPTIVE_REGULATION", "CAUSAL_ASSERTION",
            "CORRELATION_ONLY", "NO_CAUSAL_CONTENT", "UNASSESSED_LANGUAGE")

# ---- 因果载体（语言无关：中英各自的正则，归一为同一个语义标签）----
CAUSAL_PATTERNS = [
    (r"\bcaus(?:e|es|ed|ing)\b", "cause"),
    (r"\bdriv(?:e|es|en|ing)\b", "drive"),
    (r"\bpromot(?:e|es|ed|ing)\b", "promote"),
    (r"\bled\s+to\b|\bleads\s+to\b|\bleading\s+to\b", "lead_to"),
    (r"\bresults?\s+in\b|\bresulted\s+in\b|\bresulting\s+in\b", "result_in"),
    (r"\bdetermin(?:e|es|ed|ing)\b", "determine"),
    (r"\brequired\s+for\b", "required_for"),
    # 排除 "clathrin-mediated endocytosis" 这类复合定语：连字符前不是因果载体
    (r"(?<!-)\bmediat(?:e|es|ed|ing)\b", "mediate"),
    (r"(?<!-)\binduct(?:e|es|ed|ing)\b|(?<!-)\binduced\b", "induce"),
    (r"\bactivat(?:e|es|ed|ing)\b", "activate"),
    # 只收动词形态：regulation / upregulation 是名词或状态，不是因果载体
    (r"\bregulat(?:e|es|ed|ing)\b", "regulate"),
    (r"\bup-?regulat(?:e|es|ed|ing)\b|\bdown-?regulat(?:e|es|ed|ing)\b", "regulate"),
    (r"\bpromotes?\b", "promote"),
    (r"促进", "promote"),
    (r"导致|引起|造成", "cause"),
    (r"驱动", "drive"),
    (r"介导", "mediate"),
    (r"决定", "determine"),
    (r"诱导", "induce"),
    (r"激活", "activate"),
    (r"上调|下调|调控", "regulate"),
    (r"依赖于|取决于", "depend_on"),
]

# ---- 否定标记（同子句、因果载体之前、回看窗口内）----
NEG_PATTERNS_EN = [
    r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bwithout\b", r"\bcannot\b", r"\bcan't\b",
    r"\bfail(?:s|ed|ure)?\s+to\b", r"\bneither\b", r"\bnor\b", r"\black(?:s|ed)?\s+of\b",
    r"\babsence\s+of\b", r"\bunable\s+to\b", r"\bdoes\s+not\b", r"\bdid\s+not\b",
]
NEG_PATTERNS_HAN = [r"并未", r"未能", r"未", r"不能", r"不足以", r"并无", r"并非",
                    r"没有", r"无证据", r"不再", r"不"]
# 否定存在句（否定语在因果载体前较远位置）
NEG_EXISTENTIAL = [r"\bno\s+evidence\b", r"\bnot\s+sufficient\b", r"\bdoes\s+not\s+establish\b",
                   r"无证据", r"没有证据", r"不足以说明", r"不足以证明", r"不能说明"]

# ---- 假说/检验框架 ----
HYP_PATTERNS = [r"\bwhether\b", r"\bhypothesi[sz](?:e|es|ed|ing)\b", r"\bhypothesis\b",
                r"\bwe\s+(?:asked|tested|sought)\b", r"\btest(?:ed|ing)?\s+whether\b",
                r"\bmay\b", r"\bmight\b", r"\bcould\b", r"\bwould\b", r"\bpossibly\b",
                r"是否", r"假设", r"旨在检验", r"旨在验证", r"可能", r"或许", r"推测"]

# ---- 证椟性保留（对已述因果的弱化）----
UNC_PATTERNS = [r"\bsuggest(?:s|ed|ing)?\b", r"\bappears?\s+to\b", r"\blikely\b",
                r"\bimplicat(?:e|es|ed)\b", r"\bpresumably\b", r"\bseems?\s+to\b",
                r"提示", r"似乎", r"倾向于", r"有待", r"尚需"]

# ---- 相关性 ----
CORREL_PATTERNS = [r"\bassociat(?:e|es|ed|ion)\s+with\b", r"\bcorrelat(?:e|es|ed|ion)\s+with\b",
                   r"\bco-?occur\w*\b", r"\brelationship\s+between\b", r"\bpositively\s+correlated\b",
                   r"\binversely\s+correlated\b", r"\bindependent\s+of\b",
                   r"相关", r"伴随", r"关联"]

# ---- 描述性"受调控"（被动、无施动者）----
DESCRIPTIVE_REG_PATTERNS = [
    r"\b(?:is|are|was|were)\s+(?:actively\s+|tightly\s+|transcriptionally\s+|differentially\s+)?regulated\b(?!\s+by\b)",
    # 中文只收"无施动者"的被动式；"受干旱胁迫调控"含施动者，按因果断言处理
    r"受(?:严格|精细|转录后?|翻译后?|负|正|差异|共同)?调控",
]

CLAUSE_SPLIT = re.compile(r"[。！？；;!?]|(?<=[\u4e00-\u9fff])，|,(?=\s)|\n+")

_CAUSAL = [(re.compile(p, re.I), lab) for p, lab in CAUSAL_PATTERNS]
_NEG_EN = [re.compile(p, re.I) for p in NEG_PATTERNS_EN]
_NEG_HAN = [re.compile(p) for p in NEG_PATTERNS_HAN]
_NEG_EX = [re.compile(p, re.I) for p in NEG_EXISTENTIAL]
_HYP = [re.compile(p, re.I) for p in HYP_PATTERNS]
_UNC = [re.compile(p, re.I) for p in UNC_PATTERNS]
_CORREL = [re.compile(p, re.I) for p in CORREL_PATTERNS]
_DESC = [re.compile(p, re.I) for p in DESCRIPTIVE_REG_PATTERNS]


def script_coverage(text):
    """返回文本所用字符集，用于判断是否在语言覆盖面内。"""
    s = set()
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF:
            s.add("HAN")
        elif 0x3040 <= o <= 0x30FF:
            s.add("KANA")
        elif 0xAC00 <= o <= 0xD7AF:
            s.add("HANGUL")
        elif 0x0400 <= o <= 0x04FF:
            s.add("CYRILLIC")
        elif 0x0600 <= o <= 0x06FF:
            s.add("ARABIC")
        elif ch.isalpha():
            s.add("LATIN")
    return s


LOOKBACK = {"HAN": 6, "LATIN": 24}  # 字符回看窗口


def _lookback(text, pos):
    """按当前字符前后语言取回看窗口。"""
    left = text[max(0, pos - 24):pos]
    han = sum(1 for c in left if 0x4E00 <= ord(c) <= 0x9FFF)
    latin = sum(1 for c in left if c.isascii() and c.isalpha())
    w = 6 if han >= latin else 24
    return text[max(0, pos - w):pos]


def _negated(clause, pos):
    window = _lookback(clause, pos)
    for rx in _NEG_EN:
        if rx.search(window):
            return True, rx.pattern
    for rx in _NEG_HAN:
        if rx.search(window):
            return True, rx.pattern
    # 否定存在句可出现在子句更靠前的位置
    head = clause[:pos]
    for rx in _NEG_EX:
        if rx.search(head):
            return True, rx.pattern
    return False, None


def classify_clause(clause):
    """返回该子句的语义类型与命中依据。"""
    body = clause.strip()
    if not body:
        return None
    # "not only ... but also" 不是否定；中文"不仅/不同/不断"等复合词同理
    scan = re.sub(r"\bnot\s+only\b", " ", body, flags=re.I)
    scan = re.sub(r"不仅|不但|不断|不同|不少|不久|不可或缺", " ", scan)

    causal = []
    for rx, lab in _CAUSAL:
        for m in rx.finditer(scan):
            causal.append((m.start(), lab, m.group(0)))

    hits = {"causal": [c[1] for c in causal]}
    if not causal:
        if any(rx.search(scan) for rx in _CORREL):
            return {"type": "CORRELATION_ONLY", "hits": {"causal": [], "correlation": True}}
        # 无因果载体但有假说/保留语：仍属"未断言"，标为 UNCERTAIN 而非"无内容"
        if any(rx.search(scan) for rx in _HYP) or any(rx.search(scan) for rx in _UNC):
            return {"type": "UNCERTAIN", "hits": {"causal": [], "hedge": True}}
        return {"type": "NO_CAUSAL_CONTENT", "hits": hits}

    if any(rx.search(scan) for rx in _DESC) and not re.search(r"\bregulat\w*\b[^.]{0,20}\bby\b", scan, re.I):
        return {"type": "DESCRIPTIVE_REGULATION", "hits": {"causal": hits["causal"], "passive": True}}

    neg_all = True
    neg_marks = []
    for pos, lab, _ in causal:
        neg, pat = _negated(scan, pos)
        if not neg:
            neg_all = False
        else:
            neg_marks.append(pat)
    if neg_all:
        return {"type": "NEGATED_CAUSAL", "hits": {"causal": hits["causal"], "negation": neg_marks}}

    if any(rx.search(scan) for rx in _HYP):
        return {"type": "CAUSAL_HYPOTHESIS", "hits": {"causal": hits["causal"], "hypothesis": True}}
    if any(rx.search(scan) for rx in _UNC):
        return {"type": "UNCERTAIN", "hits": {"causal": hits["causal"], "hedge": True}}
    return {"type": "CAUSAL_ASSERTION", "hits": hits}


def classify_text(text):
    """把一段文本归一为语义枚举，并给出逐子句依据与覆盖状态。

    返回 dict：
      dominant       整段的主导语义类型
      clauses        [{clause, type, hits}]
      asserted       是否存在断言型因果子句（只有它为真才可判"因果升级"）
      negated/hypothesis/correlation/uncertain/descriptive  各类型子句计数
      coverage       {scripts, assessable, reason}
    """
    raw = (text or "").strip()
    scripts = script_coverage(raw)
    clauses = []
    if not raw:
        return {"dominant": "UNASSESSED_LANGUAGE", "clauses": [],
                "asserted": False, "counts": {}, "vocab": VOCAB_VERSION,
                "coverage": {"scripts": [], "assessable": False, "reason": "EMPTY_TEXT"}}

    if not scripts <= {"HAN", "LATIN"}:
        return {"dominant": "UNASSESSED_LANGUAGE", "clauses": [],
                "asserted": False, "counts": {}, "vocab": VOCAB_VERSION,
                "coverage": {"scripts": sorted(scripts), "assessable": False,
                             "reason": "SCRIPT_NOT_COVERED:" + ",".join(sorted(scripts))}}

    for piece in CLAUSE_SPLIT.split(raw):
        got = classify_clause(piece)
        if got:
            clauses.append({"clause": piece.strip()[:240], "type": got["type"], "hits": got["hits"]})

    counts = {}
    for c in clauses:
        counts[c["type"]] = counts.get(c["type"], 0) + 1

    if not clauses:
        return {"dominant": "UNASSESSED_LANGUAGE", "clauses": [], "asserted": False,
                "counts": {}, "vocab": VOCAB_VERSION,
                "coverage": {"scripts": sorted(scripts), "assessable": False, "reason": "NO_CLAUSE"}}

    order = {t: i for i, t in enumerate(PRIORITY)}
    dominant = sorted(counts, key=lambda t: (order[t], -counts[t]))[0]
    return {
        "dominant": dominant,
        "clauses": clauses,
        "asserted": counts.get("CAUSAL_ASSERTION", 0) > 0,
        "counts": counts,
        "vocab": VOCAB_VERSION,
        "coverage": {"scripts": sorted(scripts), "assessable": True, "reason": "COVERED"},
    }


def summarize(unit_text):
    """供诊断器使用的便捷包装。"""
    return classify_text(unit_text)
