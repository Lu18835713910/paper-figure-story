"""Source-bound presentation guidance, never an additional scientific fact store.

Exact statements stay in the common network. Curated shorter renderings retain
their references and PARTIAL semantic status. Layout edges cannot enter M1.
"""
from pathlib import Path
import hashlib, json, re

VERSION = 'pfs-display-guidance-1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_guidance(network, metadata):
    info = (metadata or {}).get('display_guidance')
    if not info:
        return None
    path = Path(info['path'])
    if sha(path) != info['sha256']:
        raise ValueError('GUIDANCE_DRIFT: source-bound display guidance changed')
    g = json.loads(path.read_text(encoding='utf-8-sig'))
    validate_guidance(network, g)
    g['_input'] = dict(info)
    return g

def validate_guidance(network, guidance):
    if guidance.get('version') != VERSION:
        raise ValueError('GUIDANCE_VERSION')
    if guidance.get('paper_id') != network['paper']['id']:
        raise ValueError('GUIDANCE_PAPER_MISMATCH')
    kp = next(x for x in network['inputs'] if x['kind'] == 'knowledge')
    if guidance.get('knowledge_sha256') != kp['sha256']:
        raise ValueError('GUIDANCE_KNOWLEDGE_DRIFT')
    if guidance.get('formal_ready', False):
        raise ValueError('GUIDANCE_REVIEW_PROMOTION')
    sm = {s['id']: s for s in network['statements']}
    nm = {s['id']: s for s in network['nodes']}
    records = {r['id']: r for r in guidance['records']}
    if len(records) != len(guidance['records']):
        raise ValueError('GUIDANCE_DUPLICATE_RECORD')
    caches = {Path(i['path']).resolve().parent for i in network['inputs'] if i['kind'] == 'source_cache'}
    for r in records.values():
        if r.get('semantic_review_status') != 'PARTIAL':
            raise ValueError('GUIDANCE_SEMANTIC_REVIEW: curated text requires independent review')
        if not r.get('text') or not (r.get('source_statement_ids') or r.get('source_spans')):
            raise ValueError('GUIDANCE_UNBOUND_TEXT: ' + r['id'])
        if any(s not in sm for s in r.get('source_statement_ids', [])):
            raise ValueError('GUIDANCE_UNKNOWN_STATEMENT: ' + r['id'])
        if any(n not in nm for n in r.get('source_node_ids', [])):
            raise ValueError('GUIDANCE_UNKNOWN_NODE: ' + r['id'])
        for span in r.get('source_spans', []):
            p = Path(span['path']).resolve()
            if p.parent not in caches or not re.fullmatch(r'page-\d+\.txt', p.name):
                raise ValueError('GUIDANCE_UNREGISTERED_CACHE')
            if sha(p) != span['sha256']:
                raise ValueError('GUIDANCE_SOURCE_DRIFT')
            txt = p.read_text(encoding='utf-8-sig')
            if not (0 <= span['start'] < span['end'] <= len(txt)) or txt[span['start']:span['end']] != span['text']:
                raise ValueError('GUIDANCE_EXCERPT_DRIFT')
    overview = guidance['overview']
    if overview['title_id'] not in records or overview['limit_id'] not in records:
        raise ValueError('GUIDANCE_OVERVIEW_TEXT')
    nodes = {n['id']: n for n in overview['nodes']}
    for n in nodes.values():
        if n['text_id'] not in records:
            raise ValueError('GUIDANCE_NODE_TEXT')
    relations = {r['id']: r for r in network['edges']}
    for edge in overview['edges']:
        if edge['from'] not in nodes or edge['to'] not in nodes:
            raise ValueError('GUIDANCE_EDGE_ENDPOINT')
        identity = edge.get('identity')
        if identity == 'scientific_registered':
            if edge.get('source_relation_id') not in relations:
                raise ValueError('GUIDANCE_UNREGISTERED_RELATION')
            rel = relations[edge['source_relation_id']]
            if edge['type'] != rel['type']:
                raise ValueError('GUIDANCE_RELATION_RETYPE')
            a = records[nodes[edge['from']]['text_id']]
            b = records[nodes[edge['to']]['text_id']]
            def entities(r):
                return set(r.get('source_node_ids', [])) | {e for sid in r.get('source_statement_ids', []) for e in sm[sid].get('entity_ids', [])}
            if rel['from'] not in entities(a) or rel['to'] not in entities(b):
                raise ValueError('GUIDANCE_RELATION_ENDPOINT_BINDING')
        elif identity in ['presentation', 'author_argument_candidate']:
            if edge['type'] not in ['motivates', 'compares', 'integrates', 'context', 'reading_transition', 'hypothesizes', 'argument_transition', 'parallel', 'result_presentation', 'comparison_background', 'integrative_summary']:
                raise ValueError('GUIDANCE_RELATION_ESCALATION')
            if edge.get('source_relation_id'):
                raise ValueError('GUIDANCE_PRESENTATION_AS_SCIENCE')
        else:
            raise ValueError('GUIDANCE_EDGE_IDENTITY')
    assets = {a['id']: a for a in network['assets']}
    figures = {f['id'] for f in network['figures']}
    for p in guidance.get('figure_pages', []):
        if p['figure_id'] not in figures:
            raise ValueError('GUIDANCE_UNKNOWN_FIGURE')
        for rid in [p['title_id']] + p.get('steps', []) + p.get('limit_ids', []) + p.get('notes_ids', []) + p.get('terminology_ids', []):
            if rid not in records:
                raise ValueError('GUIDANCE_PAGE_TEXT')
        for aid in p['asset_ids']:
            if aid not in assets or assets[aid]['figure_id'] != p['figure_id']:
                raise ValueError('GUIDANCE_ASSET_FIGURE')
            if assets[aid].get('known_truncation'):
                raise ValueError('GUIDANCE_TRUNCATED_ASSET')
        required=set(p.get('required_panels',[]))
        if not required or 'all' in required:
            raise ValueError('GUIDANCE_REQUIRED_PANELS: explicit fine panel scope required')
        visible={panel for aid in p['asset_ids'] for panel in assets[aid].get('panels',[]) if panel!='all'}
        if not required<=visible:
            raise ValueError('GUIDANCE_PANEL_COVERAGE: displayed asset lacks discussed panel')
    return {'valid': True, 'semantic_review_status': 'PARTIAL', 'user_acceptance': 'PENDING'}
