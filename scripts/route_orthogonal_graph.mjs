/** Generic orthogonal graph routing. No scientific content or graph edits. */
const EPS = 0.015;
const round = n => Math.round(n * 100) / 100;
const same = (a, b) => Math.abs(a.x - b.x) < EPS && Math.abs(a.y - b.y) < EPS;
const key = p => `${round(p.x)},${round(p.y)}`;
const horizontal = s => Math.abs(s.a.y - s.b.y) < EPS;
const orientation = s => horizontal(s) ? 1 : 2;
const distance = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
const segment = (a, b, extra = {}) => ({ a, b, ...extra });
const rect = b => ({ left: b.left, top: b.top, right: b.left + b.width, bottom: b.top + b.height });
const inflate = (r, amount) => ({ left: r.left - amount, top: r.top - amount, right: r.right + amount, bottom: r.bottom + amount });
const inside = (p, r) => p.x > r.left + EPS && p.x < r.right - EPS && p.y > r.top + EPS && p.y < r.bottom - EPS;
const inFrame = (p, f) => p.x >= f.left - EPS && p.x <= f.right + EPS && p.y >= f.top - EPS && p.y <= f.bottom + EPS;
const overlaps = (a, b) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > EPS && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > EPS;
function intersectsRect(s, r) {
  if (horizontal(s)) return s.a.y > r.top + EPS && s.a.y < r.bottom - EPS && Math.min(Math.max(s.a.x, s.b.x), r.right) - Math.max(Math.min(s.a.x, s.b.x), r.left) > EPS;
  return s.a.x > r.left + EPS && s.a.x < r.right - EPS && Math.min(Math.max(s.a.y, s.b.y), r.bottom) - Math.max(Math.min(s.a.y, s.b.y), r.top) > EPS;
}
function overlapLength(a, b) {
  if (orientation(a) !== orientation(b)) return 0;
  if (horizontal(a)) return Math.abs(a.a.y - b.a.y) < EPS ? Math.max(0, Math.min(Math.max(a.a.x, a.b.x), Math.max(b.a.x, b.b.x)) - Math.max(Math.min(a.a.x, a.b.x), Math.min(b.a.x, b.b.x))) : 0;
  return Math.abs(a.a.x - b.a.x) < EPS ? Math.max(0, Math.min(Math.max(a.a.y, a.b.y), Math.max(b.a.y, b.b.y)) - Math.max(Math.min(a.a.y, a.b.y), Math.min(b.a.y, b.b.y))) : 0;
}
function parallelTooClose(a, b, separation) {
  if (orientation(a) !== orientation(b)) return false;
  const offset = horizontal(a) ? Math.abs(a.a.y - b.a.y) : Math.abs(a.a.x - b.a.x);
  const projection = horizontal(a) ? Math.min(Math.max(a.a.x, a.b.x), Math.max(b.a.x, b.b.x)) - Math.max(Math.min(a.a.x, a.b.x), Math.min(b.a.x, b.b.x)) : Math.min(Math.max(a.a.y, a.b.y), Math.max(b.a.y, b.b.y)) - Math.max(Math.min(a.a.y, a.b.y), Math.min(b.a.y, b.b.y));
  return offset < separation - EPS && projection > EPS;
}
function crossing(a, b) {
  if (orientation(a) === orientation(b)) return null;
  const h = horizontal(a) ? a : b, v = horizontal(a) ? b : a, p = { x: v.a.x, y: h.a.y };
  return p.x >= Math.min(h.a.x, h.b.x) - EPS && p.x <= Math.max(h.a.x, h.b.x) + EPS && p.y >= Math.min(v.a.y, v.b.y) - EPS && p.y <= Math.max(v.a.y, v.b.y) + EPS ? p : null;
}
function onInterior(p, s) { return !same(p, s.a) && !same(p, s.b) && (horizontal(s) ? Math.abs(p.y - s.a.y) < EPS && p.x > Math.min(s.a.x, s.b.x) && p.x < Math.max(s.a.x, s.b.x) : Math.abs(p.x - s.a.x) < EPS && p.y > Math.min(s.a.y, s.b.y) && p.y < Math.max(s.a.y, s.b.y)); }
function compress(points) {
  const clean = [];
  for (const p of points) {
    if (clean.length && same(p, clean.at(-1))) continue;
    if (clean.length >= 2) { const a = clean.at(-2), b = clean.at(-1); if ((Math.abs(a.x - b.x) < EPS && Math.abs(b.x - p.x) < EPS) || (Math.abs(a.y - b.y) < EPS && Math.abs(b.y - p.y) < EPS)) clean.pop(); }
    clean.push({ x: round(p.x), y: round(p.y) });
  }
  return clean;
}
function ports(node, stub) {
  const b = rect(node.box), cx = (b.left + b.right) / 2, cy = (b.top + b.bottom) / 2;
  return [
    { side: 'top', point: { x: cx, y: b.top }, vector: { x: 0, y: -1 } },
    { side: 'right', point: { x: b.right, y: cy }, vector: { x: 1, y: 0 } },
    { side: 'bottom', point: { x: cx, y: b.bottom }, vector: { x: 0, y: 1 } },
    { side: 'left', point: { x: b.left, y: cy }, vector: { x: -1, y: 0 } },
  ].map(p => ({ ...p, point: { x: round(p.point.x), y: round(p.point.y) }, out: { x: round(p.point.x + p.vector.x * stub), y: round(p.point.y + p.vector.y * stub) }, hub: node.id + ':' + p.side }));
}
class Heap {
  data = [];
  push(value) { let i = this.data.length; this.data.push(value); while (i) { const p = (i - 1) >> 1; if (this.data[p].f <= value.f) break; this.data[i] = this.data[p]; i = p; } this.data[i] = value; }
  pop() { const first = this.data[0], last = this.data.pop(); if (this.data.length) { let i = 0; while (i * 2 + 1 < this.data.length) { let c = i * 2 + 1; if (c + 1 < this.data.length && this.data[c + 1].f < this.data[c].f) c++; if (this.data[c].f >= last.f) break; this.data[i] = this.data[c]; i = c; } this.data[i] = last; } return first; }
  get length() { return this.data.length; }
}
function routeSegments(points, fromPort, toPort, edgeId) {
  return points.slice(1).map((p, i) => segment(points[i], p, {
    edgeId,
    ...(i === 0 ? { shareKey: fromPort.hub, bHub: fromPort.hub } : {}),
    ...(i === 1 ? { aHub: fromPort.hub } : {}),
    ...(i === points.length - 3 ? { bHub: toPort.hub } : {}),
    ...(i === points.length - 2 ? { shareKey: toPort.hub, aHub: toPort.hub } : {}),
  })).filter(s => distance(s.a, s.b) > EPS);
}
function sharedTouch(p, currentHubs, previous) {
  const hub = currentHubs.get(key(p));
  return hub && ((same(p, previous.a) && previous.aHub === hub) || (same(p, previous.b) && previous.bHub === hub));
}
function stubClear(stub, obstacles, existing, frame, separation) {
  if (!inFrame(stub.a, frame) || !inFrame(stub.b, frame) || obstacles.some(r => intersectsRect(stub, r))) return false;
  for (const old of existing) if (parallelTooClose(stub, old, separation) && old.shareKey !== stub.shareKey) return false;
  return true;
}
function coordinateGrid(frame, obstacles, portPairs, existing, labels, options) {
  const xs = [frame.left, frame.right], ys = [frame.top, frame.bottom], add = (array, n, min, max) => { n = round(n); if (n >= min - EPS && n <= max + EPS) array.push(n); };
  for (const r of obstacles) { for (const x of [r.left, r.right]) add(xs, x, frame.left, frame.right); for (const y of [r.top, r.bottom]) add(ys, y, frame.top, frame.bottom); }
  for (const [a, b] of portPairs) for (const p of [a.out, b.out]) { add(xs, p.x, frame.left, frame.right); add(ys, p.y, frame.top, frame.bottom); }
  for (const s of existing) { for (const p of [s.a, s.b]) { for (const dx of [-options.laneSpacing, 0, options.laneSpacing]) add(xs, p.x + dx, frame.left, frame.right); for (const dy of [-options.laneSpacing, 0, options.laneSpacing]) add(ys, p.y + dy, frame.top, frame.bottom); } }
  const sorted = a => [...new Set(a)].sort((x, y) => x - y);
  const x = sorted(xs), y = sorted(ys);
  if (x.length * y.length > options.maxGridPoints) return null;
  const xIndex = new Map(x.map((n, i) => [n, i])), yIndex = new Map(y.map((n, i) => [n, i]));
  const points = y.flatMap(yValue => x.map(xValue => ({ x: xValue, y: yValue })));
  const blocked = points.map(p => obstacles.some(r => inside(p, r)));
  return { x, y, points, blocked, xIndex, yIndex, index: p => yIndex.get(round(p.y)) * x.length + xIndex.get(round(p.x)) };
}
function astar(grid, source, target, obstacles, existing, options) {
  const start = grid.index(source.out), goal = grid.index(target.out), width = grid.x.length;
  if (!Number.isFinite(start) || !Number.isFinite(goal) || grid.blocked[start] || grid.blocked[goal]) return null;
  const hubs = new Map([[key(source.out), source.hub], [key(target.out), target.hub]]);
  const forbiddenPoint = p => existing.some(s => (same(p, s.a) || same(p, s.b)) && !sharedTouch(p, hubs, s));
  const initialDirection = source.side === 'left' || source.side === 'right' ? 1 : 2;
  const queue = new Heap(), scores = new Map(), previous = new Map();
  const initial = start * 3 + initialDirection; scores.set(initial, 0); queue.push({ state: initial, f: distance(source.out, target.out), g: 0 });
  let visits = 0;
  while (queue.length && visits++ < options.maxVisits) {
    const current = queue.pop(); if (current.g !== scores.get(current.state)) continue;
    const index = Math.floor(current.state / 3), direction = current.state % 3, p = grid.points[index];
    if (index === goal) { const points = []; let state = current.state; while (state !== undefined) { points.push(grid.points[Math.floor(state / 3)]); state = previous.get(state); } return { points: compress(points.reverse()), score: current.g, visits }; }
    const col = index % width, row = Math.floor(index / width);
    for (const [next, nextDir] of [[col ? index - 1 : -1, 1], [col + 1 < width ? index + 1 : -1, 1], [row ? index - width : -1, 2], [row + 1 < grid.y.length ? index + width : -1, 2]]) {
      if (next < 0 || grid.blocked[next]) continue;
      const q = grid.points[next]; if (next !== goal && next !== start && forbiddenPoint(q)) continue;
      // A crossing must continue straight through an existing line, never turn
      // there and form a false T junction.
      if (direction && direction !== nextDir && existing.some(s => onInterior(p, s) && orientation(s) !== direction)) continue;
      const s = segment(p, q); if (obstacles.some(r => intersectsRect(s, r))) continue;
      if (existing.some(old => parallelTooClose(s, old, options.laneSpacing))) continue;
      let crossings = 0; for (const old of existing) { const c = crossing(s, old); if (c && !sharedTouch(c, hubs, old)) crossings++; }
      const cost = distance(p, q) + (direction && direction !== nextDir ? options.bendPenalty : 0) + crossings * options.crossingPenalty;
      const state = next * 3 + nextDir, g = current.g + cost;
      if (g >= (scores.get(state) ?? Infinity)) continue;
      scores.set(state, g); previous.set(state, current.state); queue.push({ state, g, f: g + distance(q, target.out) });
    }
  }
  return null;
}
function findLabel(points, edge, nodes, previousLabels, previousSegments, frame, options) {
  if (!edge.label || !edge.label.width || !edge.label.height) return null;
  const size = edge.label, segments = compress(points).slice(1).map((p, i, all) => segment(compress(points)[i], p)).sort((a, b) => distance(b.a, b.b) - distance(a.a, a.b));
  for (const s of segments) {
    const isH = horizontal(s), half = (isH ? size.width : size.height) / 2, lo = Math.min(isH ? s.a.x : s.a.y, isH ? s.b.x : s.b.y) + half + 5, hi = Math.max(isH ? s.a.x : s.a.y, isH ? s.b.x : s.b.y) - half - 5;
    if (lo > hi) continue;
    const positions = [(lo + hi) / 2, lo, hi];
    for (const n of nodes) { const r = inflate(rect(n.box), options.labelNodePadding + 1); for (const c of isH ? [r.left - half, r.right + half] : [r.top - half, r.bottom + half]) if (c > lo && c < hi) positions.push(c); }
    for (const center of positions) {
      const label = { left: isH ? center - size.width / 2 : s.a.x - size.width / 2, top: isH ? s.a.y - size.height / 2 : center - size.height / 2, width: size.width, height: size.height };
      const bounds = rect(label);
      if (!inFrame({ x: bounds.left, y: bounds.top }, frame) || !inFrame({ x: bounds.right, y: bounds.bottom }, frame)) continue;
      if (nodes.some(n => overlaps(bounds, inflate(rect(n.box), n.id === edge.from || n.id === edge.to ? 7 : options.labelNodePadding)))) continue;
      if (previousLabels.some(r => overlaps(bounds, inflate(rect(r), options.labelGap)))) continue;
      if (previousSegments.some(old => intersectsRect(old, inflate(bounds, 3)))) continue;
      return { ...label, segment: { from: s.a, to: s.b }, on_path: true };
    }
  }
  return null;
}
function selfIntersects(points) {
  const p = compress(points), segments = p.slice(1).map((b, i) => segment(p[i], b));
  for (let i = 0; i < segments.length; i++) for (let j = i + 2; j < segments.length; j++) if (overlapLength(segments[i], segments[j]) > EPS || crossing(segments[i], segments[j])) return true;
  return false;
}

export function routeOrthogonalGraph(input) {
  const options = { obstaclePadding: 12, endpointPadding: 6, stubLength: 10, laneSpacing: 8, bendPenalty: 22, crossingPenalty: 75, labelNodePadding: 16, labelGap: 6, maxGridPoints: 80000, maxVisits: 200000, ...input.options };
  const nodes = input.nodes.map(n => ({ id: String(n.id), box: { ...(n.box ?? n.position) } })), byId = new Map(nodes.map(n => [n.id, n])), frame = rect(input.frame);
  if (byId.size !== nodes.length || input.edges.some(e => !byId.has(e.from) || !byId.has(e.to))) throw new Error('Graph IDs/endpoints are invalid.');
  if ([frame.left, frame.top, frame.right, frame.bottom].some(n => !Number.isFinite(n)) || nodes.some(n => Object.values(n.box).some(v => !Number.isFinite(v)) || n.box.width <= 0 || n.box.height <= 0)) throw new Error('Graph geometry must be finite and positive.');
  const degree = new Map(nodes.map(n => [n.id, input.edges.filter(e => e.from === n.id || e.to === n.id).length]));
  const indexed = input.edges.map((edge, order) => ({ ...edge, order })).sort((a, b) => (b.routing_priority ?? 0) - (a.routing_priority ?? 0) || (degree.get(b.from) + degree.get(b.to)) - (degree.get(a.from) + degree.get(a.to)) || a.order - b.order);
  const routed = [], existing = [], labels = [], failures = [];
  for (const edge of indexed) {
    if (edge.from === edge.to) { failures.push({ edge_id: edge.id, code: 'needs_split', reason: 'Self-loops need an explicit reserved loop corridor.' }); continue; }
    const source = byId.get(edge.from), target = byId.get(edge.to), obstacles = nodes.map(n => inflate(rect(n.box), n.id === edge.from || n.id === edge.to ? options.endpointPadding : options.obstaclePadding));
    const portObstacle = nodes.filter(n => n.id !== edge.from && n.id !== edge.to).map(n => inflate(rect(n.box), options.obstaclePadding));
    const pairs = ports(source, options.stubLength).flatMap(a => ports(target, options.stubLength).map(b => [a, b])).filter(([a, b]) => stubClear(segment(a.point, a.out, { shareKey: a.hub }), portObstacle, existing, frame, options.laneSpacing) && stubClear(segment(b.out, b.point, { shareKey: b.hub }), portObstacle, existing, frame, options.laneSpacing)).sort((a, b) => distance(a[0].out, a[1].out) - distance(b[0].out, b[1].out));
    const allObstacles = [...obstacles, ...labels.map(r => inflate(rect(r), options.labelGap))], grid = coordinateGrid(frame, allObstacles, pairs, existing, labels, options);
    if (!grid) { failures.push({ edge_id: edge.id, code: 'needs_split', reason: 'Orthogonal routing grid exceeds its declared complexity limit.' }); continue; }
    let best;
    for (const [fromPort, toPort] of pairs) {
      const result = astar(grid, fromPort, toPort, allObstacles, existing, options); if (!result) continue;
      const points = [fromPort.point, ...result.points, toPort.point]; if (selfIntersects(points)) continue;
      const labelFrame = findLabel(points, edge, nodes, labels, existing, frame, options); if (edge.label && !labelFrame) continue;
      const score = result.score + (points.length - 2) * 2;
      if (!best || score < best.score) best = { id: edge.id, from: edge.from, to: edge.to, fromSide: fromPort.side, toSide: toPort.side, fromPort, toPort, points, labelFrame, score, order: edge.order };
    }
    if (!best) { failures.push({ edge_id: edge.id, code: 'needs_split', reason: 'No node-safe, nonoverlapping orthogonal path with an attached readable label fits the supplied frame.' }); continue; }
    const segments = routeSegments(best.points, best.fromPort, best.toPort, best.id); existing.push(...segments); if (best.labelFrame) labels.push(best.labelFrame); routed.push(best);
  }
  const crossings = new Set();
  for (let i = 0; i < existing.length; i++) for (let j = i + 1; j < existing.length; j++) if (existing[i].edgeId !== existing[j].edgeId) { const c = crossing(existing[i], existing[j]); if (c && !same(c, existing[i].a) && !same(c, existing[i].b) && !same(c, existing[j].a) && !same(c, existing[j].b)) crossings.add(key(c)); }
  return { status: failures.length ? 'needs_split' : 'ok', routes: routed.sort((a, b) => a.order - b.order), failures, diagnostics: { node_count: nodes.length, input_edge_count: input.edges.length, routed_edge_count: routed.length, obstacle_padding_px: options.obstaclePadding, endpoint_stub_px: options.stubLength, collinear_overlap_policy: 'forbidden except an identical shared node port stub', crossings: [...crossings].map(v => { const [x, y] = v.split(',').map(Number); return { x, y }; }), labels_on_own_paths: true, exhaustive_planar_layout: false } };
}

export function validateOrthogonalRoutes(input, result) {
  const violations = [], nodes = new Map(input.nodes.map(n => [n.id, n.box ?? n.position])), expected = new Map(input.edges.map(e => [e.id, e])), segments = [], labels = [];
  for (const route of result.routes) {
    const original = expected.get(route.id);
    if (!original || original.from !== route.from || original.to !== route.to) violations.push({ edge_id: route.id, code: 'changed_edge_identity_or_endpoints' });
    const source = ports({ id: route.from, box: nodes.get(route.from) }, input.options?.stubLength ?? 10).find(p => p.side === route.fromSide), target = ports({ id: route.to, box: nodes.get(route.to) }, input.options?.stubLength ?? 10).find(p => p.side === route.toSide);
    if (!source || !target || !same(source.point, route.points[0]) || !same(target.point, route.points.at(-1))) violations.push({ edge_id: route.id, code: 'endpoint_not_on_supplied_node_port' });
    const own = routeSegments(route.points, route.fromPort, route.toPort, route.id);
    for (const s of own) {
      if (Math.abs(s.a.x - s.b.x) > EPS && Math.abs(s.a.y - s.b.y) > EPS) violations.push({ edge_id: route.id, code: 'nonorthogonal' });
      for (const [id, box] of nodes) if (id !== route.from && id !== route.to && intersectsRect(s, inflate(rect(box), input.options?.obstaclePadding ?? 12))) violations.push({ edge_id: route.id, node_id: id, code: 'nonendpoint_obstacle' });
      for (const previous of segments) if (parallelTooClose(s, previous, input.options?.laneSpacing ?? 8) && (!s.shareKey || s.shareKey !== previous.shareKey)) violations.push({ edge_id: route.id, other_edge_id: previous.edgeId, code: 'collinear_overlap_or_near_overlap' });
    }
    segments.push(...own);
    if (original?.label && !route.labelFrame) violations.push({ edge_id: route.id, code: 'missing_label' });
    if (route.labelFrame) {
      const box = rect(route.labelFrame), center = { x: (box.left + box.right) / 2, y: (box.top + box.bottom) / 2 }, points = compress(route.points), line = points.slice(1).map((b, i) => segment(points[i], b));
      if (!line.some(s => same(center, s.a) || same(center, s.b) || onInterior(center, s))) violations.push({ edge_id: route.id, code: 'detached_label' });
      for (const [id, node] of nodes) if (overlaps(box, inflate(rect(node), id === route.from || id === route.to ? 7 : input.options?.labelNodePadding ?? 16))) violations.push({ edge_id: route.id, node_id: id, code: 'label_node_attribution_risk' });
      for (const old of labels) if (overlaps(box, inflate(rect(old.box), input.options?.labelGap ?? 6))) violations.push({ edge_id: route.id, other_edge_id: old.edgeId, code: 'label_overlap' });
      labels.push({ box: route.labelFrame, edgeId: route.id });
    }
  }
  for (const label of labels) for (const s of segments) if (s.edgeId !== label.edgeId && intersectsRect(s, inflate(rect(label.box), 3))) violations.push({ edge_id: label.edgeId, other_edge_id: s.edgeId, code: 'label_occludes_other_edge' });
  return { valid: violations.length === 0 && result.status === 'ok' && result.routes.length === input.edges.length, violations };
}

const XML_NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main';
export function customGeometryForPolyline(points) {
  const p = compress(points), minX = Math.min(...p.map(v => v.x)), minY = Math.min(...p.map(v => v.y)), maxX = Math.max(...p.map(v => v.x)), maxY = Math.max(...p.map(v => v.y));
  const x = Math.round(minX * 9525), y = Math.round(minY * 9525), width = Math.max(1, Math.round((maxX - minX) * 9525)), height = Math.max(1, Math.round((maxY - minY) * 9525));
  const path = p.map((v, i) => `<a:${i ? 'lnTo' : 'moveTo'}><a:pt x="${Math.round((v.x - minX) * 9525)}" y="${Math.round((v.y - minY) * 9525)}"/></a:${i ? 'lnTo' : 'moveTo'}>`).join('');
  return { xfrm: `<a:xfrm xmlns:a="${XML_NS_A}"><a:off x="${x}" y="${y}"/><a:ext cx="${width}" cy="${height}"/></a:xfrm>`, geometry: `<a:custGeom xmlns:a="${XML_NS_A}"><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="w" b="h"/><a:pathLst><a:path w="${width}" h="${height}" fill="none" stroke="1" extrusionOk="0">${path}</a:path></a:pathLst></a:custGeom>`, point_count: p.length };
}

export function patchConnectorPolylines(xml, routes, nameForRoute = route => route.id) {
  const byName = new Map(routes.map(route => [nameForRoute(route), route])), patched = new Set();
  const unescape = value => value.replaceAll('&quot;', '"').replaceAll('&apos;', "'").replaceAll('&amp;', '&').replaceAll('&lt;', '<').replaceAll('&gt;', '>');
  const result = xml.replace(/<p:cxnSp\b[\s\S]*?<\/p:cxnSp>/g, connector => {
    const name = unescape(/<p:cNvPr\b[^>]*\bname=["']([^"']*)["']/.exec(connector)?.[1] ?? ''), route = byName.get(name); if (!route) return connector;
    const beforeLine = /<a:ln\b[\s\S]*?<\/a:ln>/.exec(connector)?.[0], beforeStart = /<a:stCxn\b[^>]*>/.exec(connector)?.[0], beforeEnd = /<a:endCxn\b[^>]*>/.exec(connector)?.[0];
    const geometry = customGeometryForPolyline(route.points);
    let updated = connector.replace(/<a:xfrm\b[^>]*>[\s\S]*?<\/a:xfrm>/, geometry.xfrm).replace(/<a:(?:prstGeom|custGeom)\b[^>]*>[\s\S]*?<\/a:(?:prstGeom|custGeom)>/, geometry.geometry);
    if (!updated.includes(geometry.geometry) || (beforeLine && !updated.includes(beforeLine)) || (beforeStart && !updated.includes(beforeStart)) || (beforeEnd && !updated.includes(beforeEnd))) throw new Error('Precise route compatibility patch changed a connector style or endpoint.');
    patched.add(name); return updated;
  });
  if (patched.size !== routes.length) throw new Error('Precise route compatibility patch could not match every supplied connector.');
  return result;
}
