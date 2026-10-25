#!/usr/bin/env node
/**
 * Render supplied knowledge graphs as editable PowerPoint objects.
 * No scientific facts, nodes, edges, or chronology are inferred here.
 *
 * node render_adaptive_pptx.mjs --base base.pptx --plan plan.json
 *   --knowledge knowledge.json --output result.pptx
 *   [--artifact-module /absolute/path/artifact_tool.mjs]
 *   [--preview-dir /absolute/path/preview-directory]
 *
 * plan.slides maps to base slides by array position unless slide_index (zero
 * based), base_slide_index (zero based), or slide_number (one based) is supplied.
 * A framework slide supplies node_ids and relation_ids. Optional body_frame,
 * keep_ids, and clear_ids use pixels and original XML element IDs or names.
 * Entities are {id,name,kind}; relations are {id,from,to,type}. Arrows follow
 * the supplied from/to orientation, including data_depends_on.
 *
 * Artifact Tool imports the base and creates all added native objects. Only
 * those objects are transplanted into the original OPC package. Therefore
 * untouched slide XML, images, themes, masters, layouts, and Figures retain
 * their original uncompressed part bytes instead of undergoing a full rewrite.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { inflateRawSync, deflateRawSync } from 'node:zlib';
import { randomUUID } from 'node:crypto';

export const RELATION_STYLES = Object.freeze({
  data_depends_on: { label: '数据依赖', edgeLabel: '数据依赖', color: '#174994', dashed: false, directed: true },
  experimental_precedes: { label: '实验先后', edgeLabel: '实验先后', color: '#174994', dashed: false, directed: true },
  parallel_branch: { label: '并行分支', edgeLabel: '并行', color: '#087F8C', dashed: true, directed: false },
  compares: { label: '比较关系', edgeLabel: '比较', color: '#7654A3', dashed: true, directed: false },
  independent_validation: { label: '独立验证', edgeLabel: '独立验证', color: '#7654A3', dashed: true, directed: true },
  argument_transition: { label: '论证转接', edgeLabel: '论证转接', color: '#64748B', dashed: true, directed: true },
  evidence_supports: { label: '证据支持', edgeLabel: '证据支持', color: '#087F8C', dashed: false, directed: true },
  integrates: { label: '整合关系', edgeLabel: '整合', color: '#7654A3', dashed: false, directed: true },
  optional_path: { label: '可选路径', edgeLabel: '可选路径', color: '#64748B', dashed: true, directed: true },
});
const BLUE = '#174994';
const MIN_FONT_PX = 20; // 15 points at 96 DPI.
const RELATION_FONT_PX = 16; // 12pt secondary relation labels and legend.
const LEGEND_ROW_HEIGHT = 24;
const PREFIX = 'pfs_native_';
const NARRATIVE_CAPTION = '讲述顺序；科研关系见框架图';
const NS_P = 'http://schemas.openxmlformats.org/presentationml/2006/main';
const NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main';
const NS_R = 'http://schemas.openxmlformats.org/package/2006/relationships';
const OFFICE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/';
const NOTE_CT = 'application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml';
const fail = message => { throw new Error(message); };
const unique = values => [...new Set(values)];
const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const unesc = value => String(value).replaceAll('&quot;', '"').replaceAll('&apos;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&');
const attrs = tag => Object.fromEntries([...tag.matchAll(/([\w:.-]+)\s*=\s*(["'])([\s\S]*?)\2/g)].map(m => [m[1], unesc(m[3])]));
const textOf = xml => [...xml.matchAll(/<a:t(?:\s[^>]*)?>([\s\S]*?)<\/a:t>/g)].map(m => unesc(m[1])).join('');

export function validateGraph(nodes, relations) {
  if (!Array.isArray(nodes) || !Array.isArray(relations)) fail('Nodes and relations must be arrays.');
  if (nodes.length < 1 || nodes.length > 16) fail(`A framework page needs 1–16 supplied nodes; received ${nodes.length}. Split the plan before rendering.`);
  const ids = new Set();
  for (const n of nodes) {
    if (typeof n?.id !== 'string' || !n.id || typeof n?.name !== 'string' || !n.name.trim()) fail('Every selected entity needs a nonempty string id and name.');
    if (ids.has(n.id)) fail(`Duplicate entity ID: ${n.id}`);
    ids.add(n.id);
  }
  const edgeIds = new Set();
  for (const r of relations) {
    if (typeof r?.id !== 'string' || !r.id || edgeIds.has(r.id)) fail(`Missing or duplicate relation ID: ${r?.id}`);
    edgeIds.add(r.id);
    if (!RELATION_STYLES[r.type]) fail(`Unsupported relation type ${r.type} on ${r.id}.`);
    if (!ids.has(r.from) || !ids.has(r.to)) fail(`Relation ${r.id} has an endpoint outside this framework page. Supply both endpoint nodes or move this relation to another page.`);
  }
}

/** Rank from directed edges only. Nondirectional components share a rank.
 * Strongly connected components are kept together instead of inventing an order.
 */
export function rankGraph(nodes, relations) {
  validateGraph(nodes, relations);
  const ids = nodes.map(n => n.id);
  const order = new Map(ids.map((id, i) => [id, i]));
  const parent = new Map(ids.map(id => [id, id]));
  const find = id => { if (parent.get(id) !== id) parent.set(id, find(parent.get(id))); return parent.get(id); };
  const union = (a, b) => { a = find(a); b = find(b); if (a !== b) parent.set(b, a); };
  for (const r of relations) if (!RELATION_STYLES[r.type].directed) union(r.from, r.to);
  const groups = new Map();
  for (const id of ids) { const g = find(id); if (!groups.has(g)) groups.set(g, []); groups.get(g).push(id); }
  const adj = new Map([...groups.keys()].map(id => [id, new Set()]));
  for (const r of relations) if (RELATION_STYLES[r.type].directed && find(r.from) !== find(r.to)) adj.get(find(r.from)).add(find(r.to));
  let counter = 0;
  const index = new Map(), low = new Map(), stack = [], inStack = new Set(), sccs = [];
  const visit = v => {
    index.set(v, counter); low.set(v, counter++); stack.push(v); inStack.add(v);
    for (const w of adj.get(v)) {
      if (!index.has(w)) { visit(w); low.set(v, Math.min(low.get(v), low.get(w))); }
      else if (inStack.has(w)) low.set(v, Math.min(low.get(v), index.get(w)));
    }
    if (low.get(v) === index.get(v)) { const component = []; let w; do { w = stack.pop(); inStack.delete(w); component.push(w); } while (w !== v); sccs.push(component); }
  };
  for (const g of groups.keys()) if (!index.has(g)) visit(g);
  const componentOf = new Map();
  sccs.forEach((g, i) => g.forEach(v => componentOf.set(v, i)));
  const outgoing = sccs.map(() => new Set()), incoming = sccs.map(() => 0), ranks = sccs.map(() => 0);
  for (const [v, next] of adj) for (const w of next) {
    const a = componentOf.get(v), b = componentOf.get(w);
    if (a !== b && !outgoing[a].has(b)) { outgoing[a].add(b); incoming[b]++; }
  }
  const first = i => Math.min(...sccs[i].flatMap(g => groups.get(g)).map(id => order.get(id)));
  const queue = incoming.map((n, i) => n === 0 ? i : -1).filter(i => i >= 0).sort((a, b) => first(a) - first(b));
  while (queue.length) {
    const a = queue.shift();
    for (const b of outgoing[a]) { ranks[b] = Math.max(ranks[b], ranks[a] + 1); if (--incoming[b] === 0) { queue.push(b); queue.sort((x, y) => first(x) - first(y)); } }
  }
  const byRank = new Map(), rankById = new Map();
  for (const id of ids) { const rank = ranks[componentOf.get(find(id))]; rankById.set(id, rank); if (!byRank.has(rank)) byRank.set(rank, []); byRank.get(rank).push(id); }
  return { layers: [...byRank].sort((a, b) => a[0] - b[0]).map(([rank, nodeIds]) => ({ rank, nodeIds })), rankById,
    cyclic_components: sccs.filter(g => g.length > 1).map(g => g.flatMap(v => groups.get(v))) };
}

// Conservative mixed-script bounds, including wide uppercase scientific names.
// Font size is never reduced to compensate for a line that does not fit.
function weightedLength(text) {
  return [...text].reduce((n, c) => n + (/[A-Z]/.test(c) ? 0.85 : /[a-z0-9]/.test(c) ? 0.65 : /\s/u.test(c) ? 0.35 : /[^\u0000-\u00ff]/u.test(c) ? 1.05 : 0.65), 0);
}
export function scientificTextTokens(text) {
  const chars = [...String(text)], tokens = [], starts = /[A-Za-z0-9µμΑ-Ωα-ω]/u, continues = /[A-Za-z0-9µμΑ-Ωα-ω_.,+\-/:()%×^=<>±≤≥'′″]/u;
  for (let i = 0; i < chars.length;) {
    if (starts.test(chars[i])) {
      let token = chars[i++]; while (i < chars.length && continues.test(chars[i])) token += chars[i++];
      const trailing = /[.,:!?]+$/.exec(token)?.[0] ?? ''; if (trailing) token = token.slice(0, -trailing.length);
      if (token) tokens.push(token); for (const punctuation of trailing) tokens.push(punctuation);
    } else tokens.push(chars[i++]);
  }
  const combined = [];
  for (const token of tokens) {
    // Bind closing punctuation to its preceding token. For CJK this moves the
    // previous Han character together with a full stop/question mark.
    if (/^[。！？?!；;，,、：:）》」』】〕〉”’.]+$/u.test(token) && combined.length && !/^\s+$/u.test(combined.at(-1))) combined[combined.length - 1] += token;
    else combined.push(token);
  }
  return combined;
}
export function wrapLabel(text, width, fontSize = MIN_FONT_PX) {
  const capacity = Math.max(1, (width - 28) / fontSize); // 20px nominal plus 8px safety padding.
  const lines = [];
  for (const paragraph of String(text).split(/\r?\n/)) {
    let line = '';
    for (const token of scientificTextTokens(paragraph)) {
      if (weightedLength(token) > capacity) { const error = new Error(`needs_split: scientific token ${JSON.stringify(token)} requires a wider text box at the requested font size. It will not be split or reduced.`); error.code = 'NEEDS_SPLIT_TOKEN_WIDTH'; throw error; }
      if (line && weightedLength(line + token) > capacity) { lines.push(line); line = ''; }
      line += token;
    }
    lines.push(line);
  }
  return lines;
}

/** Select among semantic rank rows/columns and graph-aware 2–5 column packs.
 * Candidate selection uses label fit, page aspect, edge length and parallel
 * alignment. No fixed four-column fallback or synthetic nodes are used.
 */
export function layoutGraph(nodes, relations, frame) {
  const ranked = rankGraph(nodes, relations), layers = ranked.layers, gapX = 42, gapY = 32, candidates = [];
  const nameById = new Map(nodes.map(n => [n.id, n.name]));
  const sortedNames = [...nodes].sort((a, b) => weightedLength(a.name) - weightedLength(b.name));
  const tokenMinimumWidth = Math.max(...nodes.flatMap(n => scientificTextTokens(n.name).map(token => weightedLength(token) * MIN_FONT_PX + 28)));
  const desiredW = Math.max(tokenMinimumWidth, 185, Math.min(390, weightedLength(sortedNames[Math.floor(nodes.length * 0.7)].name) * MIN_FONT_PX / 2.1));
  const addCandidate = (mode, slots, cols, rows, semantic) => {
    const positions = new Map(), labels = new Map();
    for (const slot of slots) {
      const nodeW = Math.min(slot.width, desiredW); let lines;
      try { lines = wrapLabel(nameById.get(slot.id), nodeW); } catch (error) { if (error.code === 'NEEDS_SPLIT_TOKEN_WIDTH') return; throw error; }
      const nodeH = Math.max(58, lines.length * MIN_FONT_PX * 1.12 + 18);
      if (nodeW < 125 || nodeH > slot.height) return;
      positions.set(slot.id, { left: slot.left + (slot.width - nodeW) / 2, top: slot.top + (slot.height - nodeH) / 2, width: nodeW, height: nodeH });
      labels.set(slot.id, lines.join('\n'));
    }
    const center = box => ({ x: box.left + box.width / 2, y: box.top + box.height / 2 });
    let edgeDistance = 0, parallelPenalty = 0;
    for (const r of relations) { const a = center(positions.get(r.from)), b = center(positions.get(r.to)); edgeDistance += Math.hypot(a.x - b.x, a.y - b.y) / Math.hypot(frame.width, frame.height); if (!RELATION_STYLES[r.type].directed && Math.abs(a.x - b.x) > 2 && Math.abs(a.y - b.y) > 2) parallelPenalty++; }
    const aspectPenalty = [...positions.values()].reduce((sum, p) => sum + Math.abs(Math.log((p.width / p.height) / 2.8)), 0) / nodes.length;
    const lineCost = [...labels.values()].reduce((sum, s) => sum + s.split('\n').length, 0) / nodes.length;
    const vacant = Math.max(0, cols * rows - nodes.length) / nodes.length;
    const score = (semantic ? -0.65 : 0) + parallelPenalty * 1.4 + aspectPenalty * 0.3 + lineCost * 0.08 + edgeDistance / Math.max(1, relations.length) * 0.2 + vacant * 0.12;
    candidates.push({ positions, labels, mode, columns: cols, rows, score });
  };
  // Rank rows preserve parallel and comparison peers on one horizontal layer.
  {
    const rows = layers.length, cols = Math.max(...layers.map(l => l.nodeIds.length)), cellW = (frame.width - gapX * (cols - 1)) / cols, cellH = (frame.height - gapY * (rows - 1)) / rows;
    const slots = layers.flatMap((layer, row) => { const xStart = frame.left + (frame.width - layer.nodeIds.length * cellW - (layer.nodeIds.length - 1) * gapX) / 2; return layer.nodeIds.map((id, col) => ({ id, left: xStart + col * (cellW + gapX), top: frame.top + row * (cellH + gapY), width: cellW, height: cellH })); });
    addCandidate('rank-rows', slots, cols, rows, true);
  }
  // Rank columns keep the same peers on one vertical layer when names fit.
  {
    const cols = layers.length, rows = Math.max(...layers.map(l => l.nodeIds.length)), cellW = (frame.width - gapX * (cols - 1)) / cols, cellH = (frame.height - gapY * (rows - 1)) / rows;
    const slots = layers.flatMap((layer, col) => { const yStart = frame.top + (frame.height - layer.nodeIds.length * cellH - (layer.nodeIds.length - 1) * gapY) / 2; return layer.nodeIds.map((id, row) => ({ id, left: frame.left + col * (cellW + gapX), top: yStart + row * (cellH + gapY), width: cellW, height: cellH })); });
    addCandidate('rank-columns', slots, cols, rows, true);
  }
  for (let cols = Math.min(2, nodes.length); cols <= Math.min(5, nodes.length); cols++) {
    const assignments = []; let row = 0, col = 0;
    for (const layer of layers) {
      if (layer.nodeIds.length <= cols && col && col + layer.nodeIds.length > cols) { row++; col = 0; }
      for (const id of layer.nodeIds) { if (col === cols) { row++; col = 0; } assignments.push({ id, row, col }); col++; }
      if (layer.nodeIds.length > cols && col < cols) { row++; col = 0; }
    }
    const rows = Math.max(...assignments.map(a => a.row)) + 1, cellW = (frame.width - gapX * (cols - 1)) / cols, cellH = (frame.height - gapY * (rows - 1)) / rows;
    const slots = assignments.map(a => ({ id: a.id, left: frame.left + (a.row % 2 ? cols - 1 - a.col : a.col) * (cellW + gapX), top: frame.top + a.row * (cellH + gapY), width: cellW, height: cellH }));
    addCandidate(`rank-pack-${cols}-columns`, slots, cols, rows, false);
  }
  if (!candidates.length) fail('No adaptive layout can show the supplied node names at 15pt inside the framework body. Split this page into fewer supplied nodes or provide concise entity names; no text was omitted.');
  const selected = candidates.sort((a, b) => a.score - b.score)[0];
  return { ...selected, ranks: Object.fromEntries(ranked.rankById), cyclic_components: ranked.cyclic_components, candidate_count: candidates.length };
}

// Minimal OPC ZIP handling. Existing compressed payloads are copied unchanged.
let crcTable;
function crc32(bytes) {
  crcTable ??= Array.from({ length: 256 }, (_, n) => { for (let k = 0; k < 8; k++) n = n & 1 ? 0xedb88320 ^ (n >>> 1) : n >>> 1; return n >>> 0; });
  let crc = 0xffffffff; for (const b of bytes) crc = crcTable[(crc ^ b) & 255] ^ (crc >>> 8); return (crc ^ 0xffffffff) >>> 0;
}
export function readZip(buffer) {
  let end = -1;
  for (let p = buffer.length - 22; p >= Math.max(0, buffer.length - 65557); p--) if (buffer.readUInt32LE(p) === 0x06054b50) { end = p; break; }
  if (end < 0) fail('The PPTX is not a supported ZIP package.');
  const count = buffer.readUInt16LE(end + 10), offset = buffer.readUInt32LE(end + 16);
  if (count === 65535 || offset === 0xffffffff) fail('ZIP64 packages are not supported.');
  const entries = new Map(); let p = offset;
  for (let i = 0; i < count; i++) {
    if (buffer.readUInt32LE(p) !== 0x02014b50) fail('Invalid ZIP central directory.');
    const flags = buffer.readUInt16LE(p + 8), method = buffer.readUInt16LE(p + 10), crc = buffer.readUInt32LE(p + 16), compressedSize = buffer.readUInt32LE(p + 20), size = buffer.readUInt32LE(p + 24);
    const nameLen = buffer.readUInt16LE(p + 28), extraLen = buffer.readUInt16LE(p + 30), commentLen = buffer.readUInt16LE(p + 32), localOffset = buffer.readUInt32LE(p + 42);
    if (flags & 1) fail('Encrypted ZIP entries are not supported.');
    const name = buffer.subarray(p + 46, p + 46 + nameLen).toString('utf8');
    const localName = buffer.readUInt16LE(localOffset + 26), localExtra = buffer.readUInt16LE(localOffset + 28), start = localOffset + 30 + localName + localExtra;
    const data = buffer.subarray(start, start + compressedSize);
    entries.set(name, { name, method, crc, size, data, time: buffer.readUInt16LE(p + 12), date: buffer.readUInt16LE(p + 14), external: buffer.readUInt32LE(p + 38) });
    p += 46 + nameLen + extraLen + commentLen;
  }
  return entries;
}
function getPart(zip, name) {
  const entry = zip.get(name); if (!entry) fail(`Missing PPTX part: ${name}`);
  if (entry.method !== 0 && entry.method !== 8) fail(`Unsupported ZIP method ${entry.method}.`);
  return entry.method === 0 ? entry.data : inflateRawSync(entry.data);
}
const getXml = (zip, name) => getPart(zip, name).toString('utf8');
function putPart(zip, name, bytes) { bytes = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes, 'utf8'); zip.set(name, { name, method: 8, crc: crc32(bytes), size: bytes.length, data: deflateRawSync(bytes), time: 0, date: 0, external: 0 }); }
export function writeZip(zip) {
  const local = [], central = []; let offset = 0;
  if (zip.size >= 65535) fail('Too many ZIP entries.');
  for (const e of zip.values()) {
    const name = Buffer.from(e.name, 'utf8'), h = Buffer.alloc(30), c = Buffer.alloc(46);
    h.writeUInt32LE(0x04034b50, 0); h.writeUInt16LE(20, 4); h.writeUInt16LE(0x800, 6); h.writeUInt16LE(e.method, 8); h.writeUInt16LE(e.time ?? 0, 10); h.writeUInt16LE(e.date ?? 0, 12); h.writeUInt32LE(e.crc, 14); h.writeUInt32LE(e.data.length, 18); h.writeUInt32LE(e.size, 22); h.writeUInt16LE(name.length, 26);
    c.writeUInt32LE(0x02014b50, 0); c.writeUInt16LE(20, 4); c.writeUInt16LE(20, 6); c.writeUInt16LE(0x800, 8); c.writeUInt16LE(e.method, 10); c.writeUInt16LE(e.time ?? 0, 12); c.writeUInt16LE(e.date ?? 0, 14); c.writeUInt32LE(e.crc, 16); c.writeUInt32LE(e.data.length, 20); c.writeUInt32LE(e.size, 24); c.writeUInt16LE(name.length, 28); c.writeUInt32LE(e.external ?? 0, 38); c.writeUInt32LE(offset, 42);
    local.push(h, name, e.data); central.push(c, name); offset += h.length + name.length + e.data.length;
  }
  const centralBuffer = Buffer.concat(central), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(zip.size, 8); end.writeUInt16LE(zip.size, 10); end.writeUInt32LE(centralBuffer.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, centralBuffer, end]);
}

// Prefixes are aliases and may be redeclared on individual elements. Resolve
// element/attribute names against each element's in-scope namespace URIs.
function namespaceElements(xml, localName, namespaceUri) {
  const matches = [], scopes = [new Map([['xml', 'http://www.w3.org/XML/1998/namespace']])];
  for (const token of xml.matchAll(/<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<!\[CDATA\[[\s\S]*?\]\]>|<![^>]*>|<\/?[^>]+>/g)) {
    const tag = token[0];
    if (/^<(!|\?)/.test(tag)) continue;
    if (/^<\//.test(tag)) { if (scopes.length === 1) fail('Unbalanced XML namespace scope.'); scopes.pop(); continue; }
    const qualifiedName = /^<([\w:.-]+)/.exec(tag)?.[1]; if (!qualifiedName) continue;
    const values = attrs(tag), scope = new Map(scopes.at(-1));
    for (const [key, value] of Object.entries(values)) { if (key === 'xmlns') scope.set('', value); else if (key.startsWith('xmlns:')) scope.set(key.slice(6), value); }
    const colon = qualifiedName.indexOf(':'), prefix = colon < 0 ? '' : qualifiedName.slice(0, colon), local = colon < 0 ? qualifiedName : qualifiedName.slice(colon + 1);
    if (local === localName && scope.get(prefix) === namespaceUri) {
      const attribute = (uri, name) => {
        for (const [key, value] of Object.entries(values)) {
          if (key === 'xmlns' || key.startsWith('xmlns:')) continue;
          const split = key.indexOf(':'), attrLocal = split < 0 ? key : key.slice(split + 1), attrUri = split < 0 ? '' : scope.get(key.slice(0, split));
          if (attrLocal === name && attrUri === uri) return value;
        }
        return undefined;
      };
      matches.push({ values, attribute });
    }
    if (!/\/\s*>$/.test(tag)) scopes.push(scope);
  }
  if (scopes.length !== 1) fail('Unbalanced XML namespace scope.');
  return matches;
}
function relationships(xml) {
  const rows = namespaceElements(xml, 'Relationship', NS_R).map(element => element.values), ids = new Set();
  for (const row of rows) { if (!row.Id || !row.Type || !row.Target) fail('Malformed OPC relationship.'); if (ids.has(row.Id)) fail(`Duplicate OPC relationship ID ${row.Id}`); ids.add(row.Id); }
  return rows;
}
function resolvePart(origin, target) { return target.startsWith('/') ? target.slice(1) : path.posix.normalize(path.posix.join(path.posix.dirname(origin), target)); }
export function slideParts(zip) {
  const rels = new Map(relationships(getXml(zip, 'ppt/_rels/presentation.xml.rels')).map(r => [r.Id, r]));
  const slides = namespaceElements(getXml(zip, 'ppt/presentation.xml'), 'sldId', NS_P);
  if (!slides.length) fail('No presentation slide IDs were found in the required presentation namespace.');
  return slides.map(element => {
    const id = element.attribute(OFFICE_REL.slice(0, -1), 'id');
    if (!id) fail('Presentation slide ID lacks an office-relationships namespace ID.');
    const relation = rels.get(id); if (!relation) fail(`Missing slide relationship ${id}`);
    if (relation.Type !== OFFICE_REL + 'slide' || relation.TargetMode === 'External') fail(`Invalid slide relationship type or external target for ${id}`);
    const part = resolvePart('ppt/presentation.xml', relation.Target);
    if (!part.startsWith('ppt/') || !zip.has(part)) fail(`Missing or invalid slide part ${part}`);
    return part;
  });
}
function spTree(xml) {
  const open = /<p:spTree(?:\s[^>]*)?>/.exec(xml); if (!open) fail('Slide lacks p:spTree.');
  const start = open.index + open[0].length, end = xml.indexOf('</p:spTree>', start); if (end < 0) fail('Malformed p:spTree.');
  return { start, end, body: xml.slice(start, end) };
}
function directChildren(xml) {
  const result = []; let depth = 0, start = -1;
  for (const match of xml.matchAll(/<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<![^>]*>|<\/?[^>]+>/g)) {
    const tag = match[0]; if (/^<(!|\?)/.test(tag)) continue;
    if (/^<\//.test(tag)) { depth--; if (!depth) result.push(xml.slice(start, match.index + tag.length)); }
    else if (/\/\s*>$/.test(tag)) { if (!depth) result.push(tag); }
    else { if (!depth) start = match.index; depth++; }
  }
  if (depth) fail('Malformed XML child tree.');
  return result;
}
function nativeInfo(xml) {
  const nonvisual = /<p:cNvPr\b[^>]*>/.exec(xml), nv = attrs(nonvisual?.[0] ?? '');
  const xfrm = /<a:xfrm\b[^>]*>([\s\S]*?)<\/a:xfrm>/.exec(xml)?.[1] ?? '';
  const off = attrs(/<a:off\b[^>]*\/?\s*>/.exec(xfrm)?.[0] ?? ''), ext = attrs(/<a:ext\b[^>]*\/?\s*>/.exec(xfrm)?.[0] ?? '');
  const box = off.x !== undefined && ext.cx !== undefined ? { left: +off.x / 9525, top: +off.y / 9525, width: +ext.cx / 9525, height: +ext.cy / 9525 } : null;
  return { id: nv.id, name: nv.name ?? '', box, title: /<p:ph\b[^>]*\btype=["'](?:title|ctrTitle)["']/.test(xml), body: /<p:ph\b[^>]*\btype=["'](?:body|obj)["']/.test(xml), text: textOf(xml) };
}
function clearFrameworkBody(xml, slidePlan, body) {
  const tree = spTree(xml), removed = [], keep = new Set((slidePlan.keep_ids ?? []).map(String)), clear = new Set((slidePlan.clear_ids ?? []).map(String));
  const children = directChildren(tree.body).filter(child => {
    if (!/^<p:(sp|pic|graphicFrame|grpSp|cxnSp)\b/.test(child)) return true;
    const info = nativeInfo(child);
    if (info.name.startsWith(PREFIX)) { removed.push({ id: info.id, name: info.name }); return false; }
    if (keep.has(info.id) || keep.has(info.name) || info.title) return true;
    const forcedClear = clear.has(info.id) || clear.has(info.name);
    const fullCanvasDecoration = info.box && info.box.left <= 10 && info.box.top <= 10 && info.box.width >= body.left + body.width && info.box.height >= body.top + body.height;
    const namedDecoration = /(?:^|[ _-])(?:logo|brand|footer|decoration|watermark|page.?number)(?:$|[ _-])|页码|标志|底纹|装饰/i.test(info.name);
    if (!forcedClear && (fullCanvasDecoration || namedDecoration)) return true;
    let remove = forcedClear || info.body;
    if (info.box) { const cx = info.box.left + info.box.width / 2, cy = info.box.top + info.box.height / 2; remove ||= cx >= body.left && cx <= body.left + body.width && cy >= body.top && cy <= body.top + body.height; }
    if (remove) removed.push({ id: info.id, name: info.name });
    return !remove;
  });
  return { xml: xml.slice(0, tree.start) + children.join('') + xml.slice(tree.end), removed };
}
function addGraphObjects(originalXml, exportedXml, expectedNodes, expectedRelations) {
  const graph = directChildren(spTree(exportedXml).body).filter(c => nativeInfo(c).name.startsWith(PREFIX));
  const nodes = graph.filter(c => nativeInfo(c).name.startsWith(PREFIX + 'node_'));
  const edges = graph.filter(c => nativeInfo(c).name.startsWith(PREFIX + 'edge_'));
  if (nodes.length !== expectedNodes || edges.length !== expectedRelations) fail(`Artifact export lost graph objects: nodes ${nodes.length}/${expectedNodes}, relations ${edges.length}/${expectedRelations}. No final deck was written.`);
  let next = Math.max(0, ...[...originalXml.matchAll(/<p:cNvPr\b[^>]*\bid=["'](\d+)["']/g)].map(m => +m[1])) + 1;
  const idMap = new Map(graph.map(c => [nativeInfo(c).id, String(next++)]));
  const remapped = graph.map(c => c.replace(/(<p:cNvPr\b[^>]*\bid=)(["'])(\d+)\2/g, (_, a, q, id) => `${a}${q}${idMap.get(id)}${q}`).replace(/(<a:(?:stCxn|endCxn)\b[^>]*\bid=)(["'])(\d+)\2/g, (_, a, q, id) => { if (!idMap.has(id)) fail('Graph connector points outside supplied native graph objects.'); return `${a}${q}${idMap.get(id)}${q}`; }));
  const tree = spTree(originalXml);
  return originalXml.slice(0, tree.end) + remapped.join('') + originalXml.slice(tree.end);
}
function editableLineReport(xml) {
  const objects = directChildren(spTree(xml).body).filter(c => nativeInfo(c).name.startsWith(PREFIX));
  const relationObjects = objects.filter(c => nativeInfo(c).name.startsWith(PREFIX + 'edge_'));
  const narrativeObjects = objects.filter(c => nativeInfo(c).name.startsWith(PREFIX + 'figure_narrative_arrow_'));
  const describe = elements => ({ total: elements.length, native_cxnSp: elements.filter(c => /^<p:cxnSp\b/.test(c)).length, cxnSp_with_both_endpoint_references: elements.filter(c => /^<p:cxnSp\b/.test(c) && /<a:stCxn\b/.test(c) && /<a:endCxn\b/.test(c)).length, editable_line_sp: elements.filter(c => /^<p:sp\b/.test(c)).length });
  return { all_native_cxnSp: objects.filter(c => /^<p:cxnSp\b/.test(c)).length, framework_relations: describe(relationObjects), figure_narrative_arrows: describe(narrativeObjects), semantics: 'Line objects remain editable. No dynamic connector attachment guarantee is made. Native p:cxnSp, explicit endpoint references, and editable p:sp line shapes are counted from final XML.' };
}
export function inspectSemanticEdges(xml, relations) {
  const objects = directChildren(spTree(xml).body), results = [];
  const namesById = new Map(objects.map(c => { const n = nativeInfo(c); return [n.id, n.name]; }));
  for (const relation of relations) {
    const name = PREFIX + 'edge_' + relation.id + '__' + relation.type, object = objects.find(c => nativeInfo(c).name === name);
    if (!object) fail(`Missing exported relation object ${relation.id}.`);
    const line = /<a:ln\b[^>]*>([\s\S]*?)<\/a:ln>/.exec(object)?.[1] ?? '';
    const dash = attrs(/<a:prstDash\b[^>]*\/?\s*>/.exec(line)?.[0] ?? '').val ?? 'solid';
    const head = attrs(/<a:headEnd\b[^>]*\/?\s*>/.exec(line)?.[0] ?? '').type ?? 'none';
    const tail = attrs(/<a:tailEnd\b[^>]*\/?\s*>/.exec(line)?.[0] ?? '').type ?? 'none';
    const color = attrs(/<a:srgbClr\b[^>]*\/?\s*>/.exec(line)?.[0] ?? '').val;
    const style = RELATION_STYLES[relation.type], actualDashed = dash !== 'solid';
    if (actualDashed !== style.dashed || head !== 'none' || (style.directed ? tail !== 'triangle' : tail !== 'none') || color?.toUpperCase() !== style.color.slice(1).toUpperCase()) fail(`Relation ${relation.id} exported with incorrect semantics: dash=${dash}, head=${head}, tail=${tail}, color=${color}. No final PPTX was written.`);
    const start = attrs(/<a:stCxn\b[^>]*\/?\s*>/.exec(object)?.[0] ?? ''), end = attrs(/<a:endCxn\b[^>]*\/?\s*>/.exec(object)?.[0] ?? '');
    const nativeConnector = /^<p:cxnSp\b/.test(object), endpointsVerified = namesById.get(start.id) === PREFIX + 'node_' + relation.from && namesById.get(end.id) === PREFIX + 'node_' + relation.to;
    if (nativeConnector && !endpointsVerified) fail(`Relation ${relation.id} has incorrect exported endpoint references. No final PPTX was written.`);
    results.push({ relation_id: relation.id, type: relation.type, xml_kind: nativeConnector ? 'p:cxnSp' : 'p:sp', dash, head_end: head, tail_end: tail, color, from_node: relation.from, to_node: relation.to, start_connection_site: start.idx ?? null, end_connection_site: end.idx ?? null, endpoint_references_verified: endpointsVerified, semantic_style_verified: true });
  }
  return results;
}

function noteParagraph(text) { return `<a:p xmlns:a="${NS_A}"><a:r><a:rPr lang="zh-CN"/><a:t>${esc(text)}</a:t></a:r><a:endParaRPr lang="zh-CN"/></a:p>`; }
function bodyNoteShape(text) { return `<p:sp xmlns:p="${NS_P}" xmlns:a="${NS_A}"><p:nvSpPr><p:cNvPr id="1001" name="PFS source metadata"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>${noteParagraph(text)}</p:txBody></p:sp>`; }
function appendNotes(zip, slidePart, noteText) {
  const relPart = path.posix.join(path.posix.dirname(slidePart), '_rels', path.posix.basename(slidePart) + '.rels');
  let relXml = zip.has(relPart) ? getXml(zip, relPart) : `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="${NS_R}"></Relationships>`;
  const rels = relationships(relXml), noteRel = rels.find(r => r.Type === OFFICE_REL + 'notesSlide');
  let notePart;
  if (noteRel) {
    notePart = resolvePart(slidePart, noteRel.Target);
    let xml = getXml(zip, notePart), tree = spTree(xml), children = directChildren(tree.body), found = false;
    children = children.map(c => { if (!found && /<p:ph\b[^>]*\btype=["']body["']/.test(c)) { found = true; return c.replace('</p:txBody>', noteParagraph(noteText) + '</p:txBody>'); } return c; });
    if (!found) children.push(bodyNoteShape(noteText));
    xml = xml.slice(0, tree.start) + children.join('') + xml.slice(tree.end); putPart(zip, notePart, xml);
  } else {
    notePart = `ppt/notesSlides/notesSlide_pfs_${randomUUID().replaceAll('-', '')}.xml`;
    const rid = 'rId' + (Math.max(0, ...rels.map(r => +(r.Id.match(/\d+$/)?.[0] ?? 0))) + 1);
    const relationship = `<Relationship Id="${rid}" Type="${OFFICE_REL}notesSlide" Target="${path.posix.relative(path.posix.dirname(slidePart), notePart)}"/>`;
    relXml = relXml.replace(/<\/Relationships\s*>/, relationship + '</Relationships>'); putPart(zip, relPart, relXml);
    putPart(zip, notePart, `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:notes xmlns:a="${NS_A}" xmlns:p="${NS_P}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>${bodyNoteShape(noteText)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>`);
    putPart(zip, path.posix.join(path.posix.dirname(notePart), '_rels', path.posix.basename(notePart) + '.rels'), `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="${NS_R}"><Relationship Id="rId1" Type="${OFFICE_REL}slide" Target="${path.posix.relative(path.posix.dirname(notePart), slidePart)}"/></Relationships>`);
    let contentTypes = getXml(zip, '[Content_Types].xml');
    contentTypes = contentTypes.replace(/<\/Types\s*>/, `<Override PartName="/${notePart}" ContentType="${NOTE_CT}"/></Types>`); putPart(zip, '[Content_Types].xml', contentTypes);
  }
  return notePart;
}

function addText(slide, name, text, frame, font, options = {}) {
  const shape = slide.shapes.add({ geometry: 'textbox', name: PREFIX + name, position: frame, fill: options.fill ?? 'none', line: { fill: 'none', width: 0 } });
  shape.text = text;
  shape.text.style = { typeface: font, fontSize: MIN_FONT_PX, color: BLUE, alignment: options.alignment ?? 'left', verticalAlignment: 'middle', autoFit: 'none', wrap: 'none', insets: 0, ...options.style };
  return shape;
}
function addConnector(slide, name, source, target, style, sides) {
  const connector = slide.shapes.connect(source, target, { kind: 'elbow', fromSide: sides.fromSide, toSide: sides.toSide, line: { style: style.dashed ? 'dashed' : 'solid', fill: style.color, width: 2 }, head: { type: 'none' }, tail: { type: style.directed ? 'triangle' : 'none', width: 'sm', length: 'sm' } });
  connector.name = PREFIX + name;
  connector.sendToBack(); return connector;
}
export function frameworkRegions(width, height, typeCount, requestedBody) {
  const rows = Math.ceil(typeCount / 3), caption = { left: width * 0.045, top: height - 86, width: width * 0.91, height: 28 };
  const legendTop = caption.top - 10 - rows * LEGEND_ROW_HEIGHT, graphBottom = legendTop - 18;
  const body = { ...(requestedBody ?? { left: width * 0.045, top: height * 0.195, width: width * 0.91, height: graphBottom - height * 0.195 }) };
  body.height = Math.min(body.height, graphBottom - body.top);
  return { body, caption, legendTop, footer_safe_top: height - 50 };
}
function overlapArea(a, b) { return Math.max(0, Math.min(a.left + a.width, b.left + b.width) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.top + a.height, b.top + b.height) - Math.max(a.top, b.top)); }
function relationLabelFrame(a, b, label, body, nodeBoxes, previous, routeSide) {
  const width = weightedLength(label) * RELATION_FONT_PX + 10, height = 22;
  const ax = a.left + a.width / 2, ay = a.top + a.height / 2, bx = b.left + b.width / 2, by = b.top + b.height / 2, midX = (ax + bx) / 2, midY = (ay + by) / 2;
  const routeCandidate = routeSide === 'bottom' ? { left: midX - width / 2, top: Math.max(a.top + a.height, b.top + b.height) + 8 } : routeSide === 'top' ? { left: midX - width / 2, top: Math.min(a.top, b.top) - height - 4 } : routeSide === 'right' ? { left: Math.max(a.left + a.width, b.left + b.width) + 5, top: midY - height / 2 } : null;
  const candidates = [
    ...(routeCandidate ? [routeCandidate] : []),
    { left: midX - width / 2, top: midY - height / 2 },
    { left: midX - width / 2, top: Math.min(a.top, b.top) - height - 4 },
    { left: midX - width / 2, top: Math.max(a.top + a.height, b.top + b.height) + 4 },
    { left: midX - width / 2, top: midY - height - 6 },
    { left: midX - width / 2, top: midY + 6 },
    { left: Math.min(a.left, b.left) - width - 6, top: midY - height / 2 },
    { left: Math.max(a.left + a.width, b.left + b.width) + 6, top: midY - height / 2 },
  ].map(p => ({ ...p, width, height })).filter(p => p.left >= body.left - 5 && p.top >= body.top - 20 && p.left + p.width <= body.left + body.width + 5 && p.top + p.height <= body.top + body.height + 14);
  const score = p => nodeBoxes.reduce((n, box) => n + overlapArea(p, box), 0) * 30 + previous.reduce((n, box) => n + overlapArea(p, box), 0) * 10 + Math.hypot(p.left + width / 2 - midX, p.top + height / 2 - midY);
  return candidates.sort((x, y) => score(x) - score(y))[0] ?? { left: Math.max(body.left, Math.min(midX - width / 2, body.left + body.width - width)), top: Math.max(body.top, Math.min(midY - height / 2, body.top + body.height - height)), width, height };
}
function addFramework(slide, nodes, relations, layout, body, font, pageWidth, pageHeight) {
  const handles = new Map();
  for (const n of nodes) {
    const shape = slide.shapes.add({ geometry: 'rect', name: PREFIX + 'node_' + n.id, position: layout.positions.get(n.id), fill: '#FFFFFF', line: { style: 'solid', fill: BLUE, width: 2 } });
    shape.text = layout.labels.get(n.id); shape.text.style = { typeface: font, fontSize: MIN_FONT_PX, color: BLUE, bold: true, alignment: 'center', verticalAlignment: 'middle', autoFit: 'none', wrap: 'none', insets: { left: 8, right: 8, top: 5, bottom: 5 } }; handles.set(n.id, shape);
  }
  const edgeLabels = [], nodeBoxes = [...layout.positions.values()];
  for (const r of relations) {
    const a = layout.positions.get(r.from), b = layout.positions.get(r.to), dx = b.left - a.left, dy = b.top - a.top;
    const style = RELATION_STYLES[r.type];
    // Nondirectional and independent validation edges use another side from
    // ordinary incoming arrows, so a solid arrow cannot visually cover them.
    const separateRoute = !style.directed || r.type === 'independent_validation';
    let routeSide;
    if (separateRoute) routeSide = Math.abs(dx) >= Math.abs(dy) ? (Math.max(a.top + a.height, b.top + b.height) + 28 <= body.top + body.height + 10 ? 'bottom' : 'top') : 'right';
    const sides = routeSide ? { fromSide: routeSide, toSide: routeSide } : Math.abs(dx) > Math.abs(dy) ? { fromSide: dx >= 0 ? 'right' : 'left', toSide: dx >= 0 ? 'left' : 'right' } : { fromSide: dy >= 0 ? 'bottom' : 'top', toSide: dy >= 0 ? 'top' : 'bottom' };
    addConnector(slide, 'edge_' + r.id + '__' + r.type, handles.get(r.from), handles.get(r.to), style, sides);
    const labelFrame = relationLabelFrame(a, b, style.edgeLabel, body, nodeBoxes, edgeLabels, routeSide); edgeLabels.push(labelFrame);
    addText(slide, 'relation_type_label_' + r.id, style.edgeLabel, labelFrame, font, { fill: '#FFFFFF', alignment: 'center', style: { fontSize: RELATION_FONT_PX, color: style.color } });
  }
  const types = unique(relations.map(r => r.type)), rows = Math.ceil(types.length / 3), rowHeight = LEGEND_ROW_HEIGHT;
  const regions = frameworkRegions(pageWidth, pageHeight, types.length), legendTop = regions.legendTop, colWidth = body.width / 3;
  types.forEach((type, i) => {
    const style = RELATION_STYLES[type], left = body.left + (i % 3) * colWidth, top = legendTop + Math.floor(i / 3) * rowHeight;
    slide.shapes.add({ geometry: 'connector', name: PREFIX + 'legend_line_' + type, kind: 'straight', position: { left, top: top + 13, width: 40, height: 0 }, line: { style: style.dashed ? 'dashed' : 'solid', fill: style.color, width: 2 }, head: { type: 'none' }, tail: { type: style.directed ? 'triangle' : 'none', width: 'sm', length: 'sm' } });
    addText(slide, 'legend_label_' + type, style.label, { left: left + 50, top, width: colWidth - 58, height: 23 }, font, { style: { fontSize: RELATION_FONT_PX, color: style.color } });
  });
  addText(slide, 'relation_semantics', '箭头含义见图例，仅“实验先后”表示时间顺序', { ...regions.caption, left: body.left, width: body.width }, font);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) { const key = argv[i]; if (key === '--help' || key === '-h') { args.help = true; continue; } if (!['--base', '--plan', '--knowledge', '--output', '--artifact-module', '--preview-dir'].includes(key)) fail(`Unknown argument ${key}`); if (!argv[i + 1] || argv[i + 1].startsWith('--')) fail(`Missing value for ${key}`); args[key.slice(2)] = argv[++i]; }
  if (!args.help) for (const key of ['base', 'plan', 'knowledge', 'output']) if (!args[key]) fail(`Missing --${key}`);
  return args;
}
function selectedRecords(all, selected, label) {
  if (!Array.isArray(all) || !Array.isArray(selected)) fail(`${label} must be supplied as an array.`);
  const index = new Map(); for (const item of all) { if (index.has(item.id)) fail(`Duplicate ${label} ID ${item.id}`); index.set(item.id, item); }
  if (unique(selected).length !== selected.length) fail(`Duplicate IDs in selected ${label}.`);
  return selected.map(id => index.get(id) ?? fail(`Unknown ${label} ID ${id}`));
}
const slideIndex = (s, fallback) => s.slide_index ?? s.base_slide_index ?? (s.slide_number !== undefined ? s.slide_number - 1 : fallback);
function explicitSourceRefs(record) {
  const refs = record?.source_refs ?? record?.sources ?? record?.source_ids ?? record?.evidence_refs ?? record?.source_ref ?? [];
  return refs === null ? [] : Array.isArray(refs) ? refs : [refs];
}
function mergeSourceRefs(...lists) { const seen = new Set(); return lists.flat().filter(ref => { const key = JSON.stringify(ref); if (seen.has(key)) return false; seen.add(key); return true; }); }
function pointerSourceRefs(knowledge, pointer) {
  if (typeof pointer !== 'string' || !pointer.startsWith('/')) return [];
  const refs = []; let current = knowledge;
  for (const key of pointer.slice(1).split('/').map(k => k.replaceAll('~1', '/').replaceAll('~0', '~'))) { refs.push(...explicitSourceRefs(current)); if (!current || typeof current !== 'object' || !(key in current)) break; current = current[key]; }
  refs.push(...explicitSourceRefs(current)); return mergeSourceRefs(refs);
}
function sourceRecord(record, knowledge, inherited = []) {
  return { ...record, source_refs: mergeSourceRefs(explicitSourceRefs(record), pointerSourceRefs(knowledge, record?.knowledge_pointer), inherited) };
}
function clearFigureStory(xml) {
  const tree = spTree(xml), children = directChildren(tree.body), removed = [];
  const keep = children.filter(child => { const info = nativeInfo(child); const obsolete = /^PFS_FIGURE_STORY_|^PARALLEL/.test(info.name) || info.name.startsWith(PREFIX) || ['PFS_QUESTION', 'PFS_DESIGN', 'PFS_RESULT', 'PFS_TRANSITION', 'PFS_LIMITATION'].includes(info.name) || /^DECOR_[qdr]_label|^DECOR_div_/.test(info.name); if (obsolete) removed.push({ id: info.id, name: info.name }); return !obsolete; });
  return { xml: xml.slice(0, tree.start) + keep.join('') + xml.slice(tree.end), removed };
}
function figureCard(xml, plan) {
  const children = directChildren(spTree(xml).body).map(nativeInfo);
  const native = children.find(i => i.name === 'PFS_STORY_AREA') ?? children.find(i => i.name === 'DECOR_rightbg');
  const frame = plan.story_frame ?? native?.box;
  if (!frame) fail('Figure page needs an editable PFS_STORY_AREA/DECOR_rightbg frame or an explicit story_frame. The original image was not changed.');
  return frame;
}
export function layoutFigureStory(blocks, frame, isReview = false) {
  const labels = { question: '问题', design: isReview ? '讨论情境' : '设计', finding: isReview ? '作者论点' : '观察', inference: '解释' };
  const roleKey = role => role === 'question' ? 'question' : ['design', 'context', 'analysis', 'method'].includes(role) ? 'design' : ['finding', 'argument', 'validation', 'result'].includes(role) ? 'finding' : 'inference';
  const sections = [], limits = [];
  for (const block of blocks) {
    const text = String(block.text ?? block.content ?? block.summary ?? '').trim(); if (!text) continue;
    if (['limit', 'limitation', 'limitations'].includes(block.role ?? block.type)) { limits.push({ ...block, text }); continue; }
    const key = roleKey(block.role ?? block.type), previous = sections.at(-1);
    if (previous?.key === key) { previous.text += '\n' + text; previous.blocks.push(block); }
    else sections.push({ key, label: labels[key], text, blocks: [block] });
  }
  if (!sections.length) fail('Figure page has no supplied narrative blocks.');
  const inset = 18, bodyFont = 18, limitFont = 44 / 3, captionFont = 44 / 3, innerWidth = frame.width - inset * 2;
  const caption = { left: frame.left + inset, top: frame.top + frame.height - 27, width: innerWidth, height: 19 };
  const limitText = limits.length ? '限制：' + limits.map(b => b.text).join('\n') : '';
  const limitLines = limitText ? wrapLabel(limitText, innerWidth - 16, limitFont) : [];
  const limitHeight = limitLines.length ? limitLines.length * limitFont * 1.1 + 14 : 0;
  const limitFrame = limitHeight ? { left: frame.left + inset, top: caption.top - 9 - limitHeight, width: innerWidth, height: limitHeight } : null;
  const contentTop = frame.top + 14, contentBottom = limitFrame ? limitFrame.top - 11 : caption.top - 9, available = contentBottom - contentTop, gap = sections.length > 1 ? 23 : 0;
  let naturalTotal = 0;
  for (const section of sections) { section.lines = wrapLabel(section.label + '：' + section.text, innerWidth, bodyFont); section.height = section.lines.length * bodyFont * 1.08 + 6; naturalTotal += section.height; }
  const required = naturalTotal + (sections.length - 1) * gap;
  if (required > available) fail(`Figure story needs ${Math.ceil(required)}px at 13.5pt plus its separate limitations, but the template card provides ${Math.floor(available)}px. Split the supplied Figure story; no paragraph or limitation was omitted.`);
  const extraPerSection = Math.min(12, Math.max(0, (available - required) / sections.length)); let top = contentTop;
  for (const section of sections) { section.frame = { left: frame.left + inset, top, width: innerWidth, height: section.height + extraPerSection }; top += section.frame.height + gap; }
  return { sections, limits, limitText: limitLines.join('\n'), limitFrame, caption, bodyFont, limitFont, captionFont, card: frame };
}
function addFigureStory(slide, layout, font) {
  layout.sections.forEach((section, i) => {
    const block = addText(slide, 'figure_block_' + (i + 1) + '_' + section.key, section.lines.join('\n'), section.frame, font, { style: { fontSize: layout.bodyFont, color: '#24344D', verticalAlignment: 'middle' } });
    block.text.get(section.label + '：').bold = true;
    if (i < layout.sections.length - 1) {
      const fromY = section.frame.top + section.frame.height + 3, toY = layout.sections[i + 1].frame.top - 3;
      slide.shapes.add({ geometry: 'connector', name: PREFIX + 'figure_narrative_arrow_' + (i + 1), kind: 'straight', position: { left: layout.card.left + layout.card.width / 2, top: fromY, width: 0, height: Math.max(10, toY - fromY) }, line: { style: 'solid', fill: BLUE, width: 2 }, head: { type: 'none' }, tail: { type: 'triangle', width: 'sm', length: 'sm' } });
    }
  });
  if (layout.limitFrame) {
    const box = slide.shapes.add({ geometry: 'rect', name: PREFIX + 'figure_limitation_box', position: layout.limitFrame, fill: '#F2F4F7', line: { style: 'solid', fill: '#D7DDE5', width: 0.7 } });
    box.text = layout.limitText; box.text.style = { typeface: font, fontSize: layout.limitFont, color: '#4C5667', alignment: 'left', verticalAlignment: 'middle', autoFit: 'none', wrap: 'none', insets: { left: 8, right: 8, top: 4, bottom: 4 } };
  }
  addText(slide, 'figure_narrative_caption', NARRATIVE_CAPTION, layout.caption, font, { style: { fontSize: layout.captionFont, color: '#64748B' } });
}

export async function renderAdaptivePptx(options) {
  const base = path.resolve(options.base), output = path.resolve(options.output);
  if (base === output) fail('The output must be a new file, distinct from the base.');
  try { await fs.access(output); fail(`Refusing to overwrite existing output ${output}`); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const [baseBytes, plan, knowledge] = await Promise.all([fs.readFile(base), fs.readFile(options.plan, 'utf8').then(JSON.parse), fs.readFile(options.knowledge, 'utf8').then(JSON.parse)]);
  if (!Array.isArray(plan.slides)) fail('plan.slides must be an array.');
  const original = readZip(baseBytes), baseParts = slideParts(original), sizeAttrs = attrs(/<p:sldSz\b[^>]*>/.exec(getXml(original, 'ppt/presentation.xml'))?.[0] ?? '');
  const width = +sizeAttrs.cx / 9525, height = +sizeAttrs.cy / 9525;
  if (!(width > 0 && height > 0) || Math.abs(width / height - 16 / 9) > 0.01) fail('The base must be 16:9. The renderer preserves template geometry and will not stretch a different aspect ratio.');
  const edits = [], occupied = new Set(), plannedPages = [];
  const isReview = ['review', 'perspective', 'editorial_or_voices'].includes(knowledge.paper_type?.label);
  for (let i = 0; i < plan.slides.length; i++) {
    const s = plan.slides[i], index = slideIndex(s, i);
    if (!Number.isInteger(index) || index < 0 || index >= baseParts.length) fail(`Invalid base slide index ${index}`);
    if (occupied.has(index)) fail(`Multiple plan entries target slide ${index + 1}`); occupied.add(index);
    plannedPages.push({ index, plan: s });
    const xml = getXml(original, baseParts[index]);
    if (s.kind === 'framework') {
      const nodes = selectedRecords(knowledge.entities ?? knowledge.nodes, s.node_ids, 'entities').map(n => sourceRecord(n, knowledge)), relations = selectedRecords(knowledge.relations, s.relation_ids, 'relations').map(r => sourceRecord(r, knowledge)); validateGraph(nodes, relations);
      const types = unique(relations.map(r => r.type)), regions = frameworkRegions(width, height, types.length, s.body_frame), body = regions.body;
      for (const key of ['left', 'top', 'width', 'height']) if (!Number.isFinite(body[key])) fail(`body_frame.${key} must be finite.`);
      if (body.left < 0 || body.top < height * 0.1 || body.width < 200 || body.height < 120 || body.left + body.width > width || body.top + body.height > regions.legendTop - 18) fail('body_frame overlaps the title/footer or exceeds the slide.');
      const cleaned = clearFrameworkBody(xml, s, { ...body, height: height - body.top - 58 }), layout = layoutGraph(nodes, relations, body);
      edits.push({ kind: 'framework', index, plan: s, nodes, relations, body, regions, layout, originalXml: xml, cleanedXml: cleaned.xml, removed: cleaned.removed });
    } else {
      const figure = /figure/i.test(s.kind ?? '');
      if (figure) {
        const card = figureCard(xml, s), blocks = (s.blocks ?? []).map(b => sourceRecord(b, knowledge, explicitSourceRefs(s))), layout = layoutFigureStory(blocks, card, isReview), cleaned = clearFigureStory(xml);
        edits.push({ kind: 'figure_story', index, plan: s, blocks, layout, originalXml: xml, cleanedXml: cleaned.xml, removed: cleaned.removed });
      } else if (s.metadata?.figure_narrative && !textOf(xml).includes(NARRATIVE_CAPTION)) edits.push({ kind: 'narrative_caption', index, plan: s, originalXml: xml, cleanedXml: xml });
    }
  }
  const artifactPath = options['artifact-module'] ?? options.artifactModule ?? process.env.ARTIFACT_TOOL_MODULE;
  const artifact = await import(artifactPath ? pathToFileURL(path.resolve(artifactPath)).href : '@oai/artifact-tool');
  const { PresentationFile, FileBlob } = artifact;
  if (!PresentationFile?.importPptx || !FileBlob?.load) fail('Artifact module lacks the documented PresentationFile/FileBlob API.');
  const presentation = await PresentationFile.importPptx(await FileBlob.load(base));
  if (presentation.slides.items.length !== baseParts.length) fail('Artifact import changed the slide count.');
  const font = plan.style?.font_family ?? plan.theme?.font_family ?? 'Microsoft YaHei';
  for (const edit of edits) {
    const slide = presentation.slides.items[edit.index];
    for (const item of slide.shapes.items) if (String(item.name ?? '').startsWith(PREFIX)) item.name = 'pfs_retired_' + item.name;
    if (edit.kind === 'framework') addFramework(slide, edit.nodes, edit.relations, edit.layout, edit.body, font, width, height);
    else if (edit.kind === 'figure_story') addFigureStory(slide, edit.layout, font);
    else addText(slide, 'narrative_caption', NARRATIVE_CAPTION, edit.plan.caption_frame ?? { left: width * 0.045, top: height - 86, width: width * 0.85, height: 28 }, font);
  }
  await fs.mkdir(path.dirname(output), { recursive: true });
  const temporary = path.join(path.dirname(output), `.pfs-native-${randomUUID()}.pptx`);
  let authored;
  try { const deck = await PresentationFile.exportPptx(presentation); await deck.save(temporary); authored = readZip(await fs.readFile(temporary)); } finally { await fs.rm(temporary, { force: true }); }
  const authoredParts = slideParts(authored), report = { output, base, slide_count: baseParts.length, font, font_size_pt: 15, font_size_scope: 'Framework node body only. Secondary relation labels/legend and Figure text use the explicitly reported sizes.', font_sizes_pt: { framework_nodes: 15, relation_labels: 12, legend: 12, framework_semantics_caption: 15, figure_body: 13.5, figure_limitations: 11, figure_narrative_caption: 11 }, framework_pages: [], figure_story_pages: [], editable_line_objects: [], narrative_captions: [], notes_pages: [], unchanged_slide_parts: [], notes: 'Only experimental_precedes encodes chronology. Figure arrows encode narrative sequence only. All relation endpoints and types come from supplied JSON. Native line shape editability does not imply dynamic connector attachment; actual XML object kinds are reported per changed page.' };
  for (const edit of edits) {
    const part = baseParts[edit.index];
    const editedXml = addGraphObjects(edit.cleanedXml, getXml(authored, authoredParts[edit.index]), edit.kind === 'framework' ? edit.nodes.length : 0, edit.kind === 'framework' ? edit.relations.length : 0);
    putPart(original, part, editedXml);
    report.editable_line_objects.push({ slide_number: edit.index + 1, ...editableLineReport(editedXml), ...(edit.kind === 'framework' ? { semantic_edge_styles: inspectSemanticEdges(editedXml, edit.relations) } : {}) });
    if (edit.kind === 'framework') report.framework_pages.push({ slide_number: edit.index + 1, node_ids: edit.nodes.map(n => n.id), relation_ids: edit.relations.map(r => r.id), layout_mode: edit.layout.mode, columns: edit.layout.columns, rows: edit.layout.rows, candidate_count: edit.layout.candidate_count, ranks: edit.layout.ranks, cyclic_components: edit.layout.cyclic_components, effective_body_frame: edit.body, caption_frame: edit.regions.caption, footer_safe_top: edit.regions.footer_safe_top, relation_styles: Object.fromEntries(unique(edit.relations.map(r => r.type)).map(type => [type, RELATION_STYLES[type]])), missing_source_refs: [...edit.nodes, ...edit.relations].filter(item => !item.source_refs.length).map(item => item.id), removed_original_body_elements: edit.removed });
    else if (edit.kind === 'figure_story') { report.figure_story_pages.push({ slide_number: edit.index + 1, role_labels: edit.layout.sections.map(s => s.label), body_font_size_pt: 13.5, limitation_font_size_pt: 11, limitation_count: edit.layout.limits.length, story_card_frame: edit.layout.card, caption_frame: edit.layout.caption, removed_original_story_elements: edit.removed }); report.narrative_captions.push(edit.index + 1); }
    else report.narrative_captions.push(edit.index + 1);
  }
  // Notes cover every planned page, including pages whose visible XML is kept.
  for (const planned of plannedPages) {
    const s = planned.plan, edit = edits.find(e => e.index === planned.index), slidePlan = sourceRecord(s, knowledge);
    slidePlan.blocks = (s.blocks ?? []).map(block => sourceRecord(block, knowledge, slidePlan.source_refs));
    const metadata = { renderer: 'paper-figure-story/render_adaptive_pptx', base_slide_number: planned.index + 1, kind: s.kind, plan_metadata: plan.metadata ?? null, slide_plan: slidePlan,
      source_records: knowledge.document_registry ?? knowledge.sources ?? knowledge.source_registry ?? [],
      ...(edit?.kind === 'framework' ? { supplied_entities: edit.nodes, supplied_relations: edit.relations, layout_mode: edit.layout.mode, graph_rank: edit.layout.ranks, chronology: 'Only relations of type experimental_precedes state experimental time order.' } : {}),
      ...(edit?.kind === 'figure_story' || edit?.kind === 'narrative_caption' ? { narrative_arrow_caption: NARRATIVE_CAPTION, scientific_relations: 'No scientific relation was inferred from a Figure block role or narrative arrow.' } : {}) };
    appendNotes(original, baseParts[planned.index], '\n[PFS source metadata]\n' + JSON.stringify(metadata, null, 2)); report.notes_pages.push(planned.index + 1);
  }
  report.nativeConnectors_total = report.editable_line_objects.reduce((sum, page) => sum + page.all_native_cxnSp, 0);
  report.nativeConnectors = report.nativeConnectors_total;
  report.nativeConnectors_source = 'Count of final p:cxnSp XML elements authored by this renderer, including relation/legend connectors and Figure narrative arrows. Not a COM Shape.Type heuristic.';
  const changed = new Set(edits.map(e => e.index));
  for (let i = 0; i < baseParts.length; i++) if (!changed.has(i)) {
    if (!getPart(original, baseParts[i]).equals(getPart(readZip(baseBytes), baseParts[i]))) fail(`Unexpected modification to preserved slide ${i + 1}`);
    report.unchanged_slide_parts.push(baseParts[i]);
  }
  await fs.writeFile(output, writeZip(original), { flag: 'wx' });
  const reportPath = output.replace(/\.pptx$/i, '') + '.render-report.json';
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
  report.report_path = reportPath;
  const previewDir = options['preview-dir'] ?? options.previewDir;
  if (previewDir) {
    await fs.mkdir(previewDir, { recursive: true });
    const finalDeck = await PresentationFile.importPptx(await FileBlob.load(output));
    for (const edit of edits) { const slide = finalDeck.slides.items[edit.index], stem = 'slide-' + String(edit.index + 1).padStart(3, '0'); await fs.writeFile(path.join(previewDir, stem + '.png'), new Uint8Array(await (await finalDeck.export({ slide, format: 'png', scale: 1.5 })).arrayBuffer())); const layout = await slide.export({ format: 'layout' }); await fs.writeFile(path.join(previewDir, stem + '.layout.json'), await layout.text()); }
    report.preview_dir = path.resolve(previewDir);
  }
  return report;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) console.log('Usage: node render_adaptive_pptx.mjs --base base.pptx --plan plan.json --knowledge knowledge.json --output new.pptx [--artifact-module /absolute/artifact_tool.mjs] [--preview-dir previews]');
  else renderAdaptivePptx(args).then(report => console.log(JSON.stringify(report, null, 2))).catch(error => { console.error(error.stack ?? String(error)); process.exitCode = 1; });
}
