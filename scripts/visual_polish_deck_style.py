"""Shared typography and narrowly authorized page-chrome archival, not planning."""
from pathlib import Path
import copy,re

STYLE_PATH=Path(__file__).resolve().parents[1]/'assets/visual_polish_deck_style.json'

def style():
 import polish_presentation as v
 return v.read(STYLE_PATH)

def resolve(design):
 import polish_presentation as v
 out=copy.deepcopy(design)
 if not out.get('deck_style'):return out
 if out['deck_style']!={'version':'pfs-deck-style-1','sha256':v.digest(STYLE_PATH)}:raise v.PolishError('DECK_STYLE_DRIFT')
 cfg=style()
 for item in out.get('shapes',[]):
  role=item.get('style_role')
  if role:
   if role not in cfg['roles']:raise v.PolishError('UNKNOWN_STYLE_ROLE')
   # Layout may set alignment/margins/spans. Shared role owns typography.
   old=item.get('text_style',{})
   item['text_style']={**old,**cfg['roles'][role]}
   if role=='title':item['position']=cfg['title_box']
 return out

def valid_archive(record,item):
 if record.get('id')!=item.get('shape_id') or record.get('text')!=item.get('exact_text'):return False
 if record.get('edge') is not None or record.get('image') is not None or record.get('cells'):return False
 text=re.sub(r'\s+','',record.get('text',''))
 patterns={
  'management':r'(?:逐Figure科研故事[·・]?CNNM4F\d+|来源与限制见备注|FIGURESTORY/(?:TEXT|FIGURE)|全文科研逻辑简要版)',
  'bibliography':r'(?:Baietal\.,2026,Cell189:6097[–-]6110[·]Figure[1-9]\d*(?:[、,，]Figure[1-9]\d*)*[·]DOI10\.1016/j\.cell\.2026\.06\.039|Lu&Li[·]用户提供综述稿[·]基于正文及三份补件)'
 }
 return bool(re.fullmatch(patterns.get(item.get('kind'),r'(?!)'),text))

def archives(plan):
 return [dict(item,slide=page['slide']) for page in (plan or {}).get('pages',[]) for item in page.get('archive_chrome',[])]

def archive_records(lock,plan):
 import polish_presentation as v
 result=[]
 for item in archives(plan):
  rec=next((r for r in lock['slides'][item['slide']-1]['objects'] if r['id']==item['shape_id']),None)
  if rec is None or not valid_archive(rec,item):raise v.PolishError('SCIENTIFIC_CONTENT_CANNOT_BE_ARCHIVED')
  result.append(dict(item,original_object=rec,reason='Explicit user request: generated management label/bibliographic footer exits visible page; retained here and unchanged original notes.'))
 return result
