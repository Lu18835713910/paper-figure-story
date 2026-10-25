#!/usr/bin/env python3
"""M2-A: plan RSUs and typed framework relations from knowledge 1.1.

No PDF extraction, new scientific edges, PPT manifest or rendering is performed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter, defaultdict, deque
from pathlib import Path

import validate_knowledge as knowledge

VERSION = 'm2a-1'
REQUEST_SCHEMA = Path(__file__).resolve().parents[1] / 'schemas/planning_request_v1_1.schema.json'
FAMILIES = ('progressive', 'parallel_convergence', 'dual_branch', 'comparison_matrix', 'method_evaluation', 'knowledge_topics')
NONEXPERIMENTAL = {'review', 'perspective', 'editorial_or_voices'}
PROFILES = {
    'quick': {'context_hops': 0, 'method_details_per_unit': 0, 'review_task_limit': 0, 'detail': 'evidence_outline'},
    'balanced': {'context_hops': 1, 'method_details_per_unit': 2, 'review_task_limit': 6, 'detail': 'key_complex_methods'},
    'full': {'context_hops': None, 'method_details_per_unit': None, 'review_task_limit': None, 'detail': 'all_registered_methods'},
}


class PlanError(ValueError):
    def __init__(self, code, message, diagnostics=None):
        super().__init__(message)
        self.code = code
        self.diagnostics = diagnostics or []


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def unique(values):
    return list(dict.fromkeys(values))


def source_union(groups):
    result = {}
    for group in groups:
        for source in group:
            result.setdefault(fingerprint(source), copy.deepcopy(source))
    return list(result.values())


def resolve_pointer(model, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise PlanError('BAD_POINTER', 'Expected a JSON pointer into the knowledge snapshot')
    value = model
    try:
        for token in pointer[1:].split('/'):
            token = token.replace('~1', '/').replace('~0', '~')
            value = value[int(token)] if isinstance(value, list) else value[token]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise PlanError('BAD_POINTER', 'Unresolved knowledge pointer: ' + pointer) from exc
    return value


class ResearchPlanner:
    """Reuse one validated/indexed immutable snapshot for all depth profiles."""

    def __init__(self, model, *, verify_files=False, base_dir=None):
        report = knowledge.validate_knowledge(model, verify_files=verify_files, base_dir=base_dir)
        if not report['valid']:
            raise PlanError('INVALID_KNOWLEDGE', 'M1 knowledge validation failed', report['errors'])
        self.model = copy.deepcopy(model)
        self.knowledge_hash = fingerprint(model)
        self.validation = copy.deepcopy(report)
        self.request_schema = knowledge.load_json(REQUEST_SCHEMA)
        knowledge.check_schema(self.request_schema)
        self.stats = {'knowledge_validation_calls': 1, 'knowledge_index_builds': 1, 'pdf_parse_calls': 0, 'external_model_calls': 0, 'plan_builds': 0, 'plan_cache_hits': 0}
        self.nodes = {n['id']: n for n in self.model['entities']}
        self.stories = {s['id']: s for s in self.model['stories']}
        self.relations = {r['id']: r for r in self.model['relations']}
        self.figures = {f['id']: f for f in self.model['figures']}
        self.pointers = {}
        for collection in ('entities', 'stories', 'relations', 'figures', 'relation_groups'):
            for i, item in enumerate(self.model[collection]):
                self.pointers[item['id']] = f'/{collection}/{i}'
        self.incident = defaultdict(list)
        self.claims_for_evidence = defaultdict(list)
        for edge in self.model['relations']:
            self.incident[edge['from']].append(edge['id'])
            self.incident[edge['to']].append(edge['id'])
            if edge['type'] == 'evidence_supports':
                self.claims_for_evidence[edge['from']].append(edge['to'])
        self._cache = {}
        self._check_article_scope()

    def _check_article_scope(self):
        article_type = self.model['paper_type']['label']
        if article_type in NONEXPERIMENTAL:
            conflicts = [n['id'] for n in self.nodes.values() if n['kind'] in {'assay', 'intervention'} and n['source_role'] == 'primary_study' and n['reporting_status'] == 'paper_reported']
            if conflicts:
                raise PlanError('NONEXPERIMENTAL_CONFLICT', 'A nonexperimental article cannot attribute primary-study assays/interventions as executed research: ' + ', '.join(conflicts))
        if article_type == 'correction' and (self.model['entities'] or self.model['stories']):
            # Preserve only the input correction statements; never invent a missing parent study.
            if any(n['kind'] in {'assay', 'intervention'} and n['source_role'] == 'primary_study' for n in self.nodes.values()):
                raise PlanError('CORRECTION_SCOPE', 'Correction input contains an unsupported full experimental study')

    def _unit(self, stories, identifier):
        methods = unique(m for s in stories for m in s['method_ids'])
        evidence = unique(e for s in stories for e in s['evidence_ids'])
        figures = unique(f for s in stories for f in s['figure_refs'])
        result = {
            'id': identifier, 'source_story_ids': [s['id'] for s in stories],
            'question_refs': [self.pointers[s['id']] + '/question_or_purpose' for s in stories],
            'finding_refs': [self.pointers[s['id']] + '/finding_or_argument' for s in stories],
            'method_ids': methods, 'evidence_ids': evidence, 'figure_ids': figures,
            'claim_ids': unique(c for e in evidence for c in self.claims_for_evidence[e]),
            'original_section_order': sorted(set(o for s in stories for o in s['original_section_order'])),
            'input_presentation_orders': [s['presentation_order'] for s in stories],
            'source_refs': source_union([s['source_refs'] for s in stories]),
            'limit_refs': [self.pointers[s['id']] + '/limits' for s in stories],
            'association_scope': 'rsu_level_not_panel_specific',
            'assignment_origin': 'knowledge_stories',
        }
        return result

    def _basis(self, decision, related_story_ids):
        if not decision.get('reason', '').strip():
            raise PlanError('DECISION_BASIS', 'A regrouping/reorder decision needs a concrete reason')
        relation_ids = decision.get('basis_relation_ids', [])
        pointers = decision.get('basis_source_pointers', [])
        if not relation_ids and not pointers:
            raise PlanError('DECISION_BASIS', 'Regrouping cannot be justified by visual layout alone')
        anchors = set()
        allowed_sources = set()
        for identifier in related_story_ids:
            story = self.stories[identifier]
            anchors.update(story['method_ids'] + story['evidence_ids'])
            for i in range(len(story['source_refs'])):
                allowed_sources.add(self.pointers[identifier] + f'/source_refs/{i}')
        for identifier in list(anchors):
            node = self.nodes[identifier]
            for i in range(len(node['source_refs'])):
                allowed_sources.add(self.pointers[identifier] + f'/source_refs/{i}')
            anchors.update(self.claims_for_evidence[identifier])
        for identifier in relation_ids:
            if identifier not in self.relations:
                raise PlanError('DECISION_RELATION', 'Unknown decision relation: ' + identifier)
            r = self.relations[identifier]
            if not {r['from'], r['to']}.intersection(anchors):
                raise PlanError('DECISION_BASIS', 'Decision relation does not concern the selected stories')
            if not r['source_refs']:
                raise PlanError('DECISION_BASIS', 'A decision cannot use an unsourced transition as scientific evidence')
        for pointer in pointers:
            if pointer not in allowed_sources:
                raise PlanError('DECISION_BASIS', 'Decision must cite a source in its selected stories/methods/evidence')
            source = resolve_pointer(self.model, pointer)
            if not isinstance(source, dict) or 'document_id' not in source:
                raise PlanError('DECISION_BASIS', 'Decision pointer is not a source reference')

    def _merge_supported(self, story_ids, relation_ids):
        accepted = {'independent_validation', 'evidence_supports', 'integrates', 'compares', 'parallel_branch', 'optional_path'}
        graph = defaultdict(set)
        for identifier in relation_ids:
            edge = self.relations[identifier]
            if edge['type'] not in accepted:
                continue
            graph[edge['from']].add(edge['to'])
            graph[edge['to']].add(edge['from'])
        if not graph:
            raise PlanError('MERGE_UNSUPPORTED', 'A merge requires a relevant typed evidence relation, not only a shared method')
        anchors = [set(self.stories[s]['evidence_ids'] or self.stories[s]['method_ids']) for s in story_ids]
        common = set.intersection(*anchors)
        anchors = [a - common for a in anchors]
        if any(not a for a in anchors):
            raise PlanError('MERGE_UNSUPPORTED', 'Repeated evidence/method IDs alone do not establish a new common question')
        queue = deque(anchors[0]); reached = set(queue)
        while queue:
            for other in graph[queue.popleft()] - reached:
                reached.add(other); queue.append(other)
        if any(not reached.intersection(a) for a in anchors[1:]):
            raise PlanError('MERGE_UNSUPPORTED', 'Merge needs typed evidence/comparison/branch relations connecting the selected story evidence; shared method or Figure numbering alone is insufficient')

    def _units(self, request):
        ordered = sorted(self.model['stories'], key=lambda s: tuple(s['original_section_order']))
        units = [self._unit([s], 'U_' + s['id']) for s in ordered]
        decisions = []
        used = set()
        for op in request['operations']:
            source_ids = op['story_ids'] if op['op'] == 'merge' else [op['story_id']]
            if any(s not in self.stories for s in source_ids):
                raise PlanError('UNKNOWN_STORY', 'Regrouping names an unknown story')
            if used.intersection(source_ids):
                raise PlanError('OVERLAPPING_DECISIONS', 'Apply each original story in at most one split/merge decision')
            used.update(source_ids)
            self._basis(op, source_ids)
            target_indexes = [i for i, u in enumerate(units) if set(u['source_story_ids']).intersection(source_ids)]
            if op['op'] == 'merge':
                self._merge_supported(source_ids, op['basis_relation_ids'])
                stories = [s for s in ordered if s['id'] in source_ids]
                replacements = [self._unit(stories, op['id'])]
            else:
                story = self.stories[source_ids[0]]
                replacements = []
                for part in op['parts']:
                    u = self._unit([story], part['id'])
                    for key, field in [('method_ids', 'method_ids'), ('evidence_ids', 'evidence_ids'), ('figure_ids', 'figure_refs')]:
                        if not set(part[key]).issubset(story[field]):
                            raise PlanError('SPLIT_NEW_FACT', 'Split cannot add a method/evidence/Figure absent from its source RSU')
                        u[key] = list(part[key])
                    if not u['evidence_ids'] and not u['method_ids']:
                        raise PlanError('EMPTY_SPLIT', 'A split part needs an existing method or evidence focus')
                    u['claim_ids'] = unique(c for e in u['evidence_ids'] for c in self.claims_for_evidence[e])
                    replacements.append(u)
                for key, field in [('method_ids','method_ids'), ('evidence_ids','evidence_ids'), ('figure_ids','figure_refs')]:
                    if set(x for u in replacements for x in u[key]) != set(story[field]):
                        raise PlanError('SPLIT_COVERAGE', 'Split must retain all source RSU methods, evidence and Figure mappings')
            for u in replacements:
                u['assignment_origin'] = 'evidence_backed_presentation_request'
            first = min(target_indexes)
            units = [u for i, u in enumerate(units) if i not in target_indexes]
            units[first:first] = replacements
            decisions.append(copy.deepcopy(op))
        ids = [u['id'] for u in units]
        if len(set(ids)) != len(ids):
            raise PlanError('DUPLICATE_UNIT', 'Planned unit IDs must be unique')
        if 'reorder' in request:
            op = request['reorder']
            if len(op['unit_ids']) != len(ids) or set(op['unit_ids']) != set(ids):
                raise PlanError('ORDER_COVERAGE', 'Explicit order must name every planned unit exactly once')
            moved = [u for i, u in enumerate(units) if u['id'] != op['unit_ids'][i]]
            if not moved:
                raise PlanError('NOOP_REORDER', 'Do not submit a reorder decision when the author order is unchanged')
            self._basis(op, unique(s for u in moved for s in u['source_story_ids']))
            by_id = {u['id']:u for u in units}
            units = [by_id[i] for i in op['unit_ids']]
            decisions.append({'op':'reorder', **copy.deepcopy(op)})
        for i, u in enumerate(units, 1):
            u['presentation_order'] = i
        return units, decisions

    def _framework_choice(self):
        edges = self.model['relations']; groups = self.model['relation_groups']
        types = Counter(r['type'] for r in edges)
        article_type = self.model['paper_type']['label']
        conceptual = article_type in NONEXPERIMENTAL | {'unknown', 'correction'}
        evaluations = [n['id'] for n in self.nodes.values() if n['kind'] == 'evaluation']
        models = [n['id'] for n in self.nodes.values() if n['kind'] == 'model']
        reverse = defaultdict(set)
        for r in edges:
            if r['type'] in ('data_depends_on', 'optional_path'):
                reverse[r['to']].add(r['from'])
        upstream = set(evaluations); queue = deque(evaluations)
        while queue:
            for predecessor in reverse[queue.popleft()] - upstream:
                upstream.add(predecessor); queue.append(predecessor)
        linked_models = [m for m in models if m in upstream]
        co_referenced = [s['id'] for s in self.stories.values() if set(s['method_ids']).intersection(models) and set(s['method_ids']).intersection(evaluations)]
        dual_groups = []
        for group in groups:
            producers = unique(r['from'] for r in edges if r.get('group_id') == group['id'] and r['type'] == 'optional_path')
            if (group['type'] == 'parallel_evidence' and len(group['members']) == 2) or len(producers) == 2:
                dual_groups.append(group['id'])
        parallel_groups = [g['id'] for g in groups if g['type'] == 'parallel_evidence']
        claims = defaultdict(list)
        for r in edges:
            if r['type'] in ('evidence_supports', 'integrates'):
                claims[r['to']].append(r['id'])
        convergence_edges = unique(r for ids in claims.values() if len(ids) > 1 for r in ids)
        scores = {
            'progressive': 2 if types['data_depends_on'] or types['experimental_precedes'] else 0,
            'parallel_convergence': (5 if parallel_groups and (convergence_edges or types['independent_validation']) else 3 if parallel_groups else 0),
            'dual_branch': 4 if dual_groups else 0,
            'comparison_matrix': 5 if types['compares'] else 0,
            'method_evaluation': (6 if article_type == 'methods_or_model' and linked_models else 4 if linked_models or co_referenced else 0),
            'knowledge_topics': 10 if conceptual else 0,
        }
        if not any(scores.values()): scores['knowledge_topics'] = 1
        selected = max(FAMILIES, key=lambda f:scores[f])
        criteria = {
            'progressive': {'relation_ids':[r['id'] for r in edges if r['type'] in ('data_depends_on','experimental_precedes')], 'group_ids':[], 'entity_ids':[]},
            'parallel_convergence': {'relation_ids':unique([r['id'] for r in edges if r['type'] in ('parallel_branch','independent_validation')] + convergence_edges), 'group_ids':parallel_groups, 'entity_ids':[]},
            'dual_branch': {'relation_ids':[r['id'] for r in edges if r.get('group_id') in dual_groups], 'group_ids':dual_groups, 'entity_ids':[]},
            'comparison_matrix': {'relation_ids':[r['id'] for r in edges if r['type']=='compares'], 'group_ids':[], 'entity_ids':[]},
            'method_evaluation': {'relation_ids':[r['id'] for r in edges if r['type'] in ('data_depends_on','optional_path') and r['from'] in upstream and r['to'] in upstream], 'group_ids':[g['id'] for g in groups if g['type']=='alternative_routes'], 'entity_ids':linked_models+evaluations},
            'knowledge_topics': {'relation_ids':[r['id'] for r in edges if r['type'] in ('argument_transition','integrates')], 'group_ids':[], 'entity_ids':[]},
        }
        candidates=[]
        for family in FAMILIES:
            ids=criteria[family]
            pointers=[self.pointers[i]+'/source_refs' for key in ('relation_ids','group_ids','entity_ids') for i in ids[key]]
            candidates.append({'family':family,'score':scores[family],**ids,'basis_source_pointers':pointers,'is_layout_hint_only':True})
        return {'family':selected,'candidates':candidates,'secondary_facets':[f for f in FAMILIES if scores[f]>0 and f!=selected],
                'selection_basis':'typed_relations_and_registered_article_type; never Figure numbers or physical layout',
                'article_type_basis':copy.deepcopy(self.model['paper_type']),
                'method_evaluation_story_ids':co_referenced,
                'convergence_status':'explicit_evidence_convergence' if convergence_edges else 'no_convergence_edge_added',
                'convergence_scope':'declared evidence relations only; not every branch is inferred to converge',
                'new_scientific_edges':0,'requires_review':article_type=='unknown' or (selected=='parallel_convergence' and not convergence_edges)}

    def _node_views(self):
        result=[]
        for n in self.model['entities']:
            view={key:copy.deepcopy(value) for key,value in n.items() if key not in ('parameters','quantities')}
            pointer=self.pointers[n['id']]
            view.update(knowledge_pointer=pointer,
                        parameter_refs=[pointer+f'/parameters/{i}' for i in range(len(n['parameters']))],
                        quantity_refs=[pointer+f'/quantities/{i}' for i in range(len(n['quantities']))])
            result.append(view)
        return result

    def plan(self, profile='balanced', request=None):
        if profile not in PROFILES: raise PlanError('PROFILE','Unknown depth profile: '+str(profile))
        request=copy.deepcopy(request) if request is not None else {'request_version':VERSION,'operations':[]}
        errors=knowledge.schema_errors(request,self.request_schema)
        if errors: raise PlanError('INVALID_REQUEST','Planning request validation failed',errors)
        cache_key=(profile,fingerprint(request))
        if cache_key in self._cache:
            self.stats['plan_cache_hits']+=1
            return copy.deepcopy(self._cache[cache_key])
        self.stats['plan_builds']+=1
        units,decisions=self._units(request)
        policy=copy.deepcopy(PROFILES[profile]); article_type=self.model['paper_type']['label']
        kind='knowledge_topics' if article_type in NONEXPERIMENTAL else 'correction_only' if article_type=='correction' else 'unclassified' if article_type=='unknown' else 'research_stories'
        shared_methods=Counter(m for u in units for m in u['method_ids'])
        detail_ids=[]
        for u in units:
            methods=sorted(u['method_ids'],key=lambda m:(-(len(self.nodes[m]['parameters'])+len(self.nodes[m]['inputs'])+shared_methods[m]),self.pointers[m]))
            limit=policy['method_details_per_unit']
            u['method_detail_ids']=methods if limit is None else methods[:limit]
            detail_ids.extend(u['method_detail_ids'])
            u['method_tasks']=[{'entity_id':m,'knowledge_pointer':self.pointers[m],
                                'role':'discussed_method' if kind in ('knowledge_topics','correction_only','unclassified') else 'registered_research_task',
                                'execution_claim':'not_inferred_by_planner'} for m in u['method_ids']]
            anchors=set(u['method_ids']+u['evidence_ids']+u['claim_ids'])
            u['relation_ids']=[r['id'] for r in self.model['relations'] if {r['from'],r['to']}.intersection(anchors)]
        detail_ids=unique(detail_ids)
        if profile=='full': detail_ids=unique(detail_ids+[n['id'] for n in self.nodes.values() if n['kind'] in knowledge.METHOD_KINDS])
        method_index=[]
        for identifier in detail_ids:
            n=self.nodes[identifier]; p=self.pointers[identifier]
            method_index.append({'entity_id':identifier,'parameter_refs':[p+f'/parameters/{i}' for i in range(len(n['parameters']))],
                                 'input_ids':copy.deepcopy(n['inputs']),'output_ids':copy.deepcopy(n['outputs']),
                                 'source_pointer':p+'/source_refs','reused_by_unit_ids':[u['id'] for u in units if identifier in u['method_ids']]})
        review_queue=[]
        for n in self.nodes.values():
            for i,parameter in enumerate(n['parameters']):
                if parameter['status'] in ('not_checked','not_reported'):
                    review_queue.append({'entity_id':n['id'],'parameter_pointer':self.pointers[n['id']]+f'/parameters/{i}',
                                         'reason':parameter['status'],'action':'targeted_source_check_not_executed','source_refs':copy.deepcopy(parameter['source_refs'])})
        limit=policy['review_task_limit']; selected_reviews=review_queue if limit is None else review_queue[:limit]
        method_map=defaultdict(list); figure_map=defaultdict(list)
        for u in units:
            for m in u['method_ids']: method_map[m].append(u['id'])
            for f in u['figure_ids']: figure_map[f].append(u['id'])
        # Keep all original scientific edges even when the overview focus is smaller.
        focused=set(x for u in units for x in u['evidence_ids']+u['claim_ids'])
        if profile!='quick': focused.update(x for u in units for x in u['method_ids'])
        critical={'parallel_branch','optional_path','independent_validation','compares','experimental_precedes'}
        for r in self.model['relations']:
            if r['type'] in critical: focused.update((r['from'],r['to']))
        hops=policy['context_hops']
        if hops is None: focused=set(self.nodes)
        else:
            for _ in range(hops):
                neighbor=set()
                for identifier in focused:
                    for r_id in self.incident[identifier]:
                        r=self.relations[r_id]; neighbor.update((r['from'],r['to']))
                focused.update(neighbor)
        focused_edges=[r['id'] for r in self.model['relations'] if r['from'] in focused and r['to'] in focused]
        statistical_units=[]; shared_resources=[]
        consumers=defaultdict(list)
        for n in self.nodes.values():
            for data in n['inputs']: consumers[data].append(n['id'])
            for i,q in enumerate(n['quantities']):
                statistical_units.append({'entity_id':n['id'],'quantity_key':q['key'],'unit':q['unit'],'population_id':q['population_id'],
                                          'source_role':q['source_role'],'knowledge_pointer':self.pointers[n['id']]+f'/quantities/{i}',
                                          'aggregation':'none; not equivalent biological replicates'})
        for data,ids in consumers.items():
            if len(ids)>1:
                n=self.nodes[data]
                shared_resources.append({'entity_id':data,'consumer_ids':ids,'knowledge_pointer':self.pointers[data],
                                         'details':n.get('details'),'unit_note':n.get('unit_note'),
                                         'physical_identity':'not_established_by_shared_input','cell_pairing':'not_inferred',
                                         'source_refs':copy.deepcopy(n['source_refs'])})
        levels=set()
        def collect(value):
            if isinstance(value,dict):
                if 'verification' in value and 'document_id' in value: levels.add(value['verification'])
                for key,child in value.items():
                    if key!='value':collect(child)
            elif isinstance(value,list):
                for child in value:collect(child)
        collect(self.model)
        common={'plan_version':VERSION,'knowledge_schema_version':'1.1','knowledge_sha256':self.knowledge_hash,'profile':profile,
                'planning_request':request,'paper_type':copy.deepcopy(self.model['paper_type']),
                'source_status':{'model_status':self.model['model_status'],'verification_levels':sorted(levels),
                                 'unavailable_document_ids':[d['id'] for d in self.model['document_registry'] if d['availability']=='not_provided'],
                                 'scientific_extraction_evaluated':False},
                'diagnostics':copy.deepcopy(self.validation['warnings'])}
        if kind=='unclassified': common['diagnostics'].append({'code':'ARTICLE_TYPE_REVIEW','path':'/paper_type','message':'Article type unresolved; no experimental-story inference made'})
        if kind=='correction_only': common['diagnostics'].append({'code':'CORRECTION_ONLY','path':'/paper_type','message':'Only supplied correction statements are planned; missing original study is not reconstructed'})
        policy.update({'all_registered_rsus_retained':True,'all_registered_relations_retained':True,'pdf_parse_calls':0,'external_model_calls':0,
                       'index_policy':'one validated knowledge snapshot reused across profiles; no source-text parsing',
                       'review_tasks_executed':0,'review_tasks_pending':len(review_queue),'review_tasks_selected':len(selected_reviews),
                       'review_tasks_deferred':len(review_queue)-len(selected_reviews)})
        story_plan={**copy.deepcopy(common),'artifact_kind':'story_plan','planning_kind':kind,'units':units,
                    'order_policy':'author_section_order_default; explicit sourced decisions recorded separately; no experimental-order inference',
                    'decisions':decisions,'method_to_units':dict(method_map),'figure_to_units':dict(figure_map),
                    'method_detail_ids':detail_ids,'method_detail_index':method_index,'review_tasks':selected_reviews,'depth_policy':policy,
                    'coverage':{'source_story_ids':list(self.stories),'mapped_story_ids':unique(s for u in units for s in u['source_story_ids']),
                                'mapped_figure_ids':unique(f for u in units for f in u['figure_ids']),
                                'unmapped_registered_figure_ids':[f for f in self.figures if f not in figure_map],
                                'unmapped_entity_ids':[n for n in self.nodes if n not in {x for u in units for x in u['method_ids']+u['evidence_ids']+u['claim_ids']}],
                                'unmapped_means_not_assigned_to_rsu_not_omitted_from_framework':True}}
        framework_plan={**copy.deepcopy(common),'artifact_kind':'framework_plan','structure':self._framework_choice(),
                        'nodes':self._node_views(),
                        'edges':[{**copy.deepcopy(r),'knowledge_pointer':self.pointers[r['id']]} for r in self.model['relations']],
                        'relation_groups':[{**copy.deepcopy(g),'knowledge_pointer':self.pointers[g['id']]} for g in self.model['relation_groups']],
                        'story_unit_ids':[u['id'] for u in units], 'statistical_units':statistical_units,'shared_resource_notes':shared_resources,
                        'focus_view':{'node_ids':[n for n in self.nodes if n in focused],'edge_ids':focused_edges,'omitted_edges_not_collapsed_into_shortcuts':True},
                        'fact_policy':'read_only_view_bound_to_knowledge_sha256; no new edges or physical-pairing assumptions',
                        'rendering_implemented':False}
        result={'story_plan':story_plan,'framework_plan':framework_plan}
        self._cache[cache_key]=copy.deepcopy(result)
        return result

    def plan_all(self, request=None):
        return {profile:self.plan(profile,request=request) for profile in PROFILES}


def plan_research(model, *, profile='balanced', request=None, verify_files=False, base_dir=None):
    return ResearchPlanner(model,verify_files=verify_files,base_dir=base_dir).plan(profile,request=request)


def validate_plans(model, story_plan, framework_plan):
    """Validate derived artifacts against their sole fact source; reject view tampering."""
    errors=[]
    try:
        if not isinstance(story_plan,dict) or not isinstance(framework_plan,dict):
            raise PlanError('PLAN_FORMAT','Both plan artifacts must be JSON objects')
        if story_plan.get('profile') != framework_plan.get('profile') or story_plan.get('planning_request') != framework_plan.get('planning_request'):
            raise PlanError('PLAN_BINDING','Two artifacts must share the profile and request')
        expected=plan_research(model,profile=story_plan.get('profile'),request=story_plan.get('planning_request'))
        # --verify-files affects diagnostics only. No scientific source state may be changed.
        for key,actual in [('story_plan',story_plan),('framework_plan',framework_plan)]:
            comparison=copy.deepcopy(actual)
            reference=copy.deepcopy(expected[key])
            for artifact in (comparison, reference):
                artifact['diagnostics']=[d for d in artifact.get('diagnostics',[]) if d.get('code')!='SOURCE_FILES_NOT_CHECKED']
            if comparison!=reference:errors.append({'code':'PLAN_DRIFT','path':'/'+key,'message':'Artifact differs from the deterministic projection of its bound knowledge/request'})
    except (PlanError,ValueError,TypeError,KeyError) as exc:
        errors.append({'code':getattr(exc,'code','PLAN_FORMAT'),'path':'/','message':str(exc)})
    return {'valid':not errors,'errors':errors,'scientific_fact_verification':'not_performed'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('knowledge',type=Path)
    parser.add_argument('--outdir',type=Path,required=True)
    parser.add_argument('--profile',choices=[*PROFILES,'all'],default='balanced')
    parser.add_argument('--request',type=Path)
    parser.add_argument('--verify-files',action='store_true')
    args=parser.parse_args(argv)
    try:
        model=knowledge.load_json(args.knowledge)
        request=knowledge.load_json(args.request) if args.request else None
        planner=ResearchPlanner(model,verify_files=args.verify_files,base_dir=args.knowledge.parent)
        plans=planner.plan_all(request=request) if args.profile=='all' else {args.profile:planner.plan(args.profile,request=request)}
        # Compute all artifacts before any output; never pass these files to build_pptx.py.
        args.outdir.mkdir(parents=True,exist_ok=True)
        outputs=[]
        for profile,bundle in plans.items():
            for kind,artifact in bundle.items():
                path=args.outdir/f'{kind}.{profile}.json'
                if path.resolve()==args.knowledge.resolve() or (args.request and path.resolve()==args.request.resolve()):
                    raise PlanError('OUTPUT_COLLISION','Refusing to overwrite planner inputs')
                path.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                outputs.append(str(path))
        print(json.dumps({'valid':True,'outputs':outputs,'stats':planner.stats,'scientific_extraction_evaluated':False},ensure_ascii=False))
        return 0
    except (PlanError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'valid':False,'code':getattr(exc,'code','INPUT_ERROR'),'message':str(exc),'diagnostics':getattr(exc,'diagnostics',[])},ensure_ascii=False))
        return 1 if isinstance(exc,PlanError) else 2


if __name__=='__main__': raise SystemExit(main())
