#!/usr/bin/env python3
"""Validate knowledge 1.1 without changing the legacy PPT input or renderer.

Exit: 0 valid (warnings possible), 1 invalid model, 2 I/O/invalid schema.
No scientific extraction or claim of source verification is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / 'schemas' / 'knowledge_v1_1.schema.json'
METHOD_KINDS = {'method', 'assay', 'processing', 'model', 'evaluation'}
DATA_KINDS = {'dataset', 'sample_or_subject'}
SUPPORTED = {'$schema', '$id', '$defs', '$ref', 'title', 'description', 'type', 'properties', 'required', 'additionalProperties', 'items', 'minItems', 'uniqueItems', 'enum', 'const', 'minimum', 'maximum', 'minLength', 'pattern', 'anyOf'}

def load_json(path):
    def reject(value): raise ValueError(f'non-finite JSON number: {value}')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def finite_float(text):
        value=float(text)
        if not math.isfinite(value): raise ValueError('non-finite JSON number: '+text)
        return value
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject, parse_float=finite_float, object_pairs_hook=pairs)

def check_schema(schema):
    """Fail closed on unsupported schema keywords; this is not a general draft engine."""
    def walk(node):
        if not isinstance(node, dict): raise ValueError('schema must contain schema objects')
        unknown = set(node) - SUPPORTED
        if unknown: raise ValueError('unsupported schema keyword(s): ' + ', '.join(sorted(unknown)))
        if '$ref' in node:
            name = node['$ref'].removeprefix('#/$defs/')
            if node['$ref'] != '#/$defs/' + name or name not in schema.get('$defs', {}):
                raise ValueError('unsupported or missing local $ref: ' + node['$ref'])
        for key in ('properties', '$defs'):
            for child in node.get(key, {}).values(): walk(child)
        if 'items' in node: walk(node['items'])
        for child in node.get('anyOf', []): walk(child)
    walk(schema)

def schema_errors(value, schema):
    errors = []
    def error(path, message): errors.append({'code':'SCHEMA', 'path':path, 'message':message})
    def walk(v, spec, path):
        if isinstance(v,float) and not math.isfinite(v): error(path,'non-finite JSON number'); return
        if '$ref' in spec: spec = schema['$defs'][spec['$ref'].split('/')[-1]]
        if 'anyOf' in spec:
            for option in spec['anyOf']:
                before = len(errors); walk(v, option, path)
                good = len(errors) == before
                del errors[before:]
                if good: break
            else: error(path, 'does not match anyOf')
            return
        types = {'object':lambda x:isinstance(x, dict), 'array':lambda x:isinstance(x, list), 'string':lambda x:isinstance(x, str), 'integer':lambda x:isinstance(x, int) and not isinstance(x, bool), 'number':lambda x:isinstance(x, (int,float)) and not isinstance(x,bool) and math.isfinite(x), 'boolean':lambda x:isinstance(x,bool), 'null':lambda x:x is None}
        if 'type' in spec and not types[spec['type']](v):
            error(path, 'expected ' + spec['type']); return
        if 'const' in spec and (type(v) is not type(spec['const']) or v != spec['const']): error(path, 'incorrect constant')
        if 'enum' in spec and not any(type(v) is type(x) and v == x for x in spec['enum']): error(path, 'value outside enum')
        if isinstance(v, dict):
            for key in spec.get('required', []):
                if key not in v: error(path + '/' + key, 'required field missing')
            for key, child in v.items():
                if key in spec.get('properties', {}): walk(child, spec['properties'][key], path + '/' + key)
                elif spec.get('additionalProperties') is False: error(path + '/' + key, 'unknown field')
        if isinstance(v, list):
            if len(v) < spec.get('minItems', 0): error(path, 'too few items')
            if spec.get('uniqueItems') and len({json.dumps(x,sort_keys=True,ensure_ascii=False) for x in v}) != len(v): error(path, 'duplicate array item')
            for i, child in enumerate(v): walk(child, spec.get('items', {}), path + '/' + str(i))
        if isinstance(v, str):
            if len(v.strip()) < spec.get('minLength',0): error(path, 'empty/short text')
            if 'pattern' in spec and not re.search(spec['pattern'], v): error(path, 'pattern mismatch')
        if isinstance(v, (int,float)) and not isinstance(v, bool):
            if 'minimum' in spec and v < spec['minimum']: error(path, 'below minimum')
            if 'maximum' in spec and v > spec['maximum']: error(path, 'above maximum')
    walk(value, schema, '$')
    return errors

def validate_knowledge(model, *, schema_path=DEFAULT_SCHEMA, verify_files=False, base_dir=None):
    schema = load_json(schema_path); check_schema(schema)
    errors = schema_errors(model, schema); warnings = []
    def issue(code, path, message): errors.append({'code':code,'path':path,'message':message})
    def warn(code, path, message): warnings.append({'code':code,'path':path,'message':message})
    if errors: return {'valid':False,'errors':errors,'warnings':warnings,'engine':'stdlib-contract-subset','schema_version':'1.1'}
    collections = ['document_registry', 'entities', 'figures', 'stories', 'relations', 'relation_groups', 'relation_constraints', 'quantity_operations']
    indexes = {}
    all_ids = set()
    for collection in collections:
        index = {}; indexes[collection] = index
        for i, item in enumerate(model[collection]):
            key = item['id']
            if key in all_ids: issue('DUPLICATE_ID',f'$/{collection}/{i}/id', 'ID is not globally unique: ' + key)
            index[key] = item; all_ids.add(key)
    docs, nodes, figures, groups = (indexes[k] for k in ['document_registry','entities','figures','relation_groups'])
    def node_id(key, path):
        if key not in nodes: issue('UNKNOWN_ENTITY', path, 'unknown entity: ' + key); return False
        return True
    def source_refs(refs, path):
        for i, source in enumerate(refs):
            p = f'{path}/{i}'; doc = docs.get(source['document_id']); loc = source['locator']
            if doc is None: issue('UNKNOWN_SOURCE',p, 'unregistered source document'); continue
            if not loc or not any(k in loc for k in ('physical_page','section','paragraph','figure')): issue('SOURCE_LOCATOR',p,'a concrete page/section/paragraph/figure is required')
            if 'physical_page' in loc:
                if doc['format'] != 'pdf': issue('SOURCE_FORMAT',p,'physical_page is reserved for PDF; use section/paragraph for other formats')
                if loc['physical_page'] > doc.get('physical_page_count', float('inf')): issue('SOURCE_PAGE',p,'physical page outside registered document')
            if source['verification'] == 'secondary_only':
                if not source.get('via_locator') or not any(k in source['via_locator'] for k in ('section','paragraph','figure')): issue('SOURCE_SECONDARY',p,'secondary-only citation needs a concrete locator in the design reference')
                via = docs.get(source.get('via_document_id'))
                if via is None or via['role'] != 'design_reference' or via['availability'] != 'available': issue('SOURCE_SECONDARY',p,'secondary-only citation needs an available registered design reference')
            if source['verification'] == 'direct_checked' and doc['availability'] != 'available': issue('SOURCE_UNAVAILABLE',p,'direct_checked cannot cite an unavailable document')
    def walk_sources(value, path='$'):
        if isinstance(value, dict):
            for key, child in value.items():
                if key=='value': continue
                if key in ('source_refs','basis'): source_refs(child,path+'/'+key)
                else: walk_sources(child,path+'/'+key)
        elif isinstance(value,list):
            for i, child in enumerate(value): walk_sources(child,f'{path}/{i}')
    walk_sources(model)
    for i, d in enumerate(model['document_registry']):
        p = f'$/document_registry/{i}'
        if d['availability'] == 'available':
            if d['hash_status'] != 'verified' or d['sha256'] is None or 'path' not in d: issue('DOCUMENT_HASH',p,'available documents need path and a verified SHA256')
            elif verify_files:
                f = Path(d['path'])
                if not f.is_absolute(): f = Path(base_dir or '.') / f
                if not f.is_file(): issue('DOCUMENT_MISSING',p,'registered available file is missing: ' + str(f))
                elif hashlib.sha256(f.read_bytes()).hexdigest() != d['sha256']: issue('DOCUMENT_HASH',p,'file SHA256 differs from registry')
        else:
            if d['hash_status'] != 'unavailable' or d['sha256'] is not None: issue('DOCUMENT_HASH',p,'unavailable document must use null SHA256 and unavailable hash status')
            warn('SOURCE_NOT_AVAILABLE',p,'original source not provided; no direct scientific verification claimed')
    if not verify_files and any(d['availability']=='available' for d in docs.values()): warn('SOURCE_FILES_NOT_CHECKED','$','use --verify-files to check registered available file hashes')
    if model['model_status'] == 'manual_fixture': warn('MANUAL_FIXTURE','$','hand-curated structural fixture; this is not an automatic extraction evaluation')
    for i, n in enumerate(model['entities']):
        p=f'$/entities/{i}'
        if (n['reporting_status'] == 'paper_reported' or n['kind']=='claim') and not n['source_refs']: issue('SOURCE_REQUIRED',p,'paper_reported entity needs sources')
        if n['analysis_unit'] in ('not_applicable','not_reported') and not n.get('unit_note'): issue('UNIT_REQUIRED',p,'explain non-applicable or unreported analysis unit')
        for field in ('inputs','outputs'):
            for key in n[field]:
                if node_id(key,p+'/'+field) and nodes[key]['kind'] not in DATA_KINDS: issue('IO_KIND',p+'/'+field,'I/O must name dataset or sample entities')
        if n['source_role']=='external_reference' and not any(docs.get(s['document_id'],{}).get('role') in ('external_reference','main_paper') for s in n['source_refs']): issue('EXTERNAL_SOURCE',p,'external reference requires an identifying citation (main-paper report permitted)')
        for field in ('parameters','quantities'):
            keys=set()
            for j, item in enumerate(n[field]):
                q=f'{p}/{field}/{j}'
                if item['key'] in keys: issue('DUPLICATE_PARAMETER',q,'duplicate parameter/quantity key')
                keys.add(item['key'])
                value=item['value']; status=item['status']
                if status!='reported' and value is not None: issue('MISSING_VALUE_STATUS',q,'not_reported/not_checked/not_applicable must have null value')
                if status=='reported' and (value is None or (isinstance(value,str) and value.strip().lower() in {'未报告','待核实','unknown','not_reported','n/a',''})): issue('MISSING_VALUE_STATUS',q,'reported cannot conceal a missing value')
                if field=='quantities':
                    if item['unit'] in ('not_applicable','not_reported'): issue('QUANTITY_UNIT',q,'count quantity requires an explicit statistical unit')
                    if item['source_role'] != n['source_role']: issue('QUANTITY_SOURCE_ROLE',q,'quantity cannot change parent entity source role')
                    node_id(item['population_id'],q+'/population_id')
    for i, f in enumerate(model['figures']):
        if f['document_id'] not in docs: issue('UNKNOWN_SOURCE',f'$/figures/{i}','figure refers to unknown document')
        if any(s['document_id'] != f['document_id'] for s in f['source_refs']): issue('FIGURE_SOURCE',f'$/figures/{i}','figure source must match its registered document')
    orders=set()
    for i,s in enumerate(model['stories']):
        p=f'$/stories/{i}'
        if s['presentation_order'] in orders: issue('STORY_ORDER',p,'duplicate presentation order')
        orders.add(s['presentation_order'])
        for field,kinds in [('method_ids',METHOD_KINDS),('evidence_ids',{'evidence'})]:
            for key in s[field]:
                if node_id(key,p+'/'+field) and nodes[key]['kind'] not in kinds: issue('STORY_KIND',p+'/'+field,'wrong entity kind for ' + key)
        for key in s['figure_refs']:
            if key not in figures: issue('UNKNOWN_FIGURE',p,'unregistered figure: '+key)
    for i,g in enumerate(model['relation_groups']):
        for key in g['members']: node_id(key,f'$/relation_groups/{i}/members')
    for i,c in enumerate(model['relation_constraints']):
        node_id(c['from'],f'$/relation_constraints/{i}/from'); node_id(c['to'],f'$/relation_constraints/{i}/to')
    for i,r in enumerate(model['relations']):
        p=f'$/relations/{i}'; a=nodes.get(r['from']); b=nodes.get(r['to']); t=r['type']
        node_id(r['from'],p+'/from'); node_id(r['to'],p+'/to')
        if 'group_id' in r and r['group_id'] not in groups: issue('RELATION_GROUP',p,'unknown relation group')
        if r['from']==r['to']: issue('SELF_RELATION',p,'self relation is not allowed')
        if r['certainty']=='paper_reported' and (not r['source_refs'] or r['provenance']!='paper'): issue('SOURCE_REQUIRED',p,'paper_reported edge needs paper provenance and sources')
        if r['certainty']!='paper_reported' and r['mandatory']: issue('INFERRED_MANDATORY',p,'unverified/presentation relationship cannot be mandatory')
        if r['certainty']=='presentation_only' and r['provenance']!='presentation': issue('PRESENTATION_PROVENANCE',p,'presentation_only cannot be attributed as a paper relationship')
        if 'order_basis' in r and t!='experimental_precedes': issue('RELATION_SEMANTICS',p,'order_basis is reserved for experimental_precedes')
        if r['provenance']=='presentation' and r['certainty']!='presentation_only': issue('PRESENTATION_PROVENANCE',p,'presentation links must remain presentation_only')
        if r['provenance']=='presentation' and t!='argument_transition': issue('PRESENTATION_RELATION',p,'presentation transition cannot assert an experimental/data relationship')
        if t not in ('data_depends_on','experimental_precedes') and r['mandatory']: issue('RELATION_SEMANTICS',p,'only data or experimentally demonstrated ordering can be mandatory')
        if t=='data_depends_on':
            if not r.get('data_bindings'): issue('DATA_BINDING',p,'data dependency requires an explicit output/input correspondence')
            for bind in r.get('data_bindings',[]):
                out, inp=bind['output_id'],bind['input_id']
                node_id(out,p+'/data_bindings'); node_id(inp,p+'/data_bindings')
                if out!=inp: issue('DATA_BINDING',p,'binding must identify the same data entity at producer and consumer')
                if a and out not in a['outputs'] and not (a['kind'] in DATA_KINDS and out==a['id']): issue('DATA_OUTPUT',p,'producer does not expose this output')
                if b and inp not in b['inputs'] and not (b['kind'] in DATA_KINDS and inp==b['id']): issue('DATA_INPUT',p,'consumer does not accept this input')
                data=nodes.get(out)
                if data and data['source_role']=='external_reference' and b and b['source_role']=='primary_study' and bind['usage']!='reference': issue('EXTERNAL_AS_COHORT',p,'external reference must remain a reference input, not primary cohort filtering')
        elif 'data_bindings' in r: issue('RELATION_SEMANTICS',p,'only data_depends_on may contain data bindings')
        if t=='experimental_precedes' and (not r.get('order_basis') or r['certainty']!='paper_reported'): issue('ORDER_EVIDENCE',p,'real experimental order needs explicit sourced protocol order')
        if t in ('parallel_branch','optional_path'):
            group=groups.get(r.get('group_id'))
            expected='parallel_evidence' if t=='parallel_branch' else 'alternative_routes'
            if not group or group['type']!=expected or not {r['from'],r['to']}.issubset(group['members']): issue('RELATION_GROUP',p,'parallel/optional links require the matching group and member endpoints')
        if t in ('evidence_supports','independent_validation','integrates'):
            if not r.get('support_strength') or not r.get('limits'): issue('EVIDENCE_BOUNDARY',p,'support requires strength and explicit limits')
        if t=='evidence_supports' and b and b['kind']!='claim': issue('SUPPORT_TARGET',p,'evidence_supports must target a claim')
        if t=='independent_validation' and not r.get('independence_basis'): issue('INDEPENDENCE_BASIS',p,'explain independence rather than implying a data input')
        if r.get('support_strength')=='causal_validation':
            basis=r.get('causal_basis_ids',[])
            if not basis: issue('CAUSAL_BASIS',p,'causal validation needs sourced intervention entities')
            for key in basis:
                if node_id(key,p+'/causal_basis_ids') and (nodes[key]['kind']!='intervention' or nodes[key]['reporting_status']!='paper_reported'): issue('CAUSAL_BASIS',p,'causal basis must be a reported intervention')
        for c in model['relation_constraints']:
            if r['from']==c['from'] and r['to']==c['to'] and t in c['types'] and (not c['mandatory_only'] or r['mandatory']): issue('FORBIDDEN_RELATION',p,c['id']+': '+c['reason'])
    for i, op in enumerate(model['quantity_operations']):
        p=f'$/quantity_operations/{i}'; operands=[]
        for operand in op['operands']:
            n=nodes.get(operand['entity_id'])
            if n is None: issue('UNKNOWN_ENTITY',p,'quantity operand entity missing'); continue
            q=next((x for x in n['quantities'] if x['key']==operand['quantity_key']),None)
            if q is None: issue('UNKNOWN_QUANTITY',p,'quantity key missing'); continue
            operands.append(q)
            if q['status']!='reported': issue('QUANTITY_UNREPORTED',p,'cannot calculate using unknown counts')
        node_id(op['output_population_id'],p+'/output_population_id')
        if any(q['unit']!=op['output_unit'] for q in operands): issue('UNIT_MISMATCH',p,'counts with different statistical units cannot be subtracted/filtered')
        if any(q['population_id']!=op['output_population_id'] or q['source_role']!=op['output_source_role'] for q in operands): issue('POPULATION_MISMATCH',p,'external references and study cohorts are distinct populations')
    # Only mandatory data dependencies and demonstrated temporal order imply a DAG.
    graph={key:[] for key in nodes}
    for r in model['relations']:
        if r['type'] in ('data_depends_on','experimental_precedes') and r['mandatory'] and r['from'] in nodes and r['to'] in nodes: graph[r['from']].append(r['to'])
    visiting=set(); done=set()
    def visit(key):
        if key in visiting: return True
        if key in done: return False
        visiting.add(key)
        if any(visit(other) for other in graph[key]): return True
        visiting.remove(key); done.add(key); return False
    if any(visit(key) for key in graph): issue('DEPENDENCY_CYCLE','$/relations','mandatory scientific dependencies contain a cycle')
    return {'valid':not errors,'errors':errors,'warnings':warnings,'engine':'stdlib-contract-subset','schema_version':'1.1','counts':{k:len(model[k]) for k in collections},'scientific_verification':'not_performed_by_validator'}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('knowledge',type=Path); parser.add_argument('--schema',type=Path,default=DEFAULT_SCHEMA)
    parser.add_argument('--verify-files',action='store_true',help='check available source paths/SHA256, not citation meaning')
    parser.add_argument('--json',action='store_true',help='machine-readable report on stdout')
    parser.add_argument('--report',type=Path,help='save a JSON report')
    args=parser.parse_args(argv)
    try:
        model=load_json(args.knowledge)
        result=validate_knowledge(model,schema_path=args.schema,verify_files=args.verify_files,base_dir=args.knowledge.parent)
    except (OSError,ValueError,KeyError,RecursionError) as exc:
        result={'valid':False,'errors':[{'code':'INPUT_ERROR','path':'$','message':str(exc)}],'warnings':[]}
        code=2
    else: code=0 if result['valid'] else 1
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.json: print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(('PASS' if result['valid'] else 'FAIL')+f": {args.knowledge} ({len(result['errors'])} errors, {len(result['warnings'])} warnings)")
        for item in result['errors']+result['warnings']: print(item['code']+' '+item['path']+': '+item['message'])
    return code

if __name__=='__main__': sys.exit(main())
