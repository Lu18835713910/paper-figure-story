"""Registered PDF-region Figure assets. Pixel fidelity is distinct from semantic/panel review."""
import argparse,hashlib,json,math
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
VERSION='pfs-figure-assets-1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),'utf-8')
def compare(a,b):
    if a.size!=b.size:return {'valid':False,'reason':'SIZE_OR_ORIENTATION','mae':None}
    diff=ImageStat.Stat(ImageChops.difference(a.convert('RGB'),b.convert('RGB')))
    mae=sum(diff.mean)/3
    return {'valid':mae<=2.0,'reason':'SOURCE_REGION_MATCH' if mae<=2 else 'PIXEL_DRIFT','mae':mae}
def composite_embedded(doc,xref,smask=0):
    import fitz
    pix=fitz.Pixmap(doc,xref)
    if pix.colorspace and pix.colorspace.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
    if smask:pix=fitz.Pixmap(pix,fitz.Pixmap(doc,smask))
    mode='RGBA' if pix.alpha else 'RGB';im=Image.frombytes(mode,[pix.width,pix.height],pix.samples)
    if im.mode=='RGBA':
        bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);im=bg.convert('RGB')
    return im
def region(pdf,page,bbox,dpi=240,cache=None):
    import fitz
    with fitz.open(pdf) as doc:
        if type(page)!=int or not 1<=page<=len(doc):raise ValueError('FIGURE_PAGE')
        p=doc[page-1];box=list(map(float,bbox))
        if len(box)!=4 or not all(math.isfinite(v) for v in box):raise ValueError('FIGURE_CROP_BOUNDS')
        r=fitz.Rect(box)
        if r.is_empty or not p.rect.contains(r):raise ValueError('FIGURE_CROP_BOUNDS')
        method='pdf_region_render'
        # Reuse only a full-page render whose pixels actually match this PDF.
        if cache and Path(cache).is_file():
            with Image.open(cache) as opened:im=opened.convert('RGB')
            sx,sy=im.width/p.rect.width,im.height/p.rect.height
            ref=p.get_pixmap(matrix=fitz.Matrix(sx,sy),alpha=False,colorspace=fitz.csRGB)
            ri=Image.frombytes('RGB',[ref.width,ref.height],ref.samples)
            if compare(im,ri)['valid'] and min(sx,sy)*72>=dpi-.1:
                crop=[round((box[0]-p.rect.x0)*sx),round((box[1]-p.rect.y0)*sy),round((box[2]-p.rect.x0)*sx),round((box[3]-p.rect.y0)*sy)]
                return im.crop(crop),'verified_page_cache',p.rotation
        pix=p.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),clip=r,alpha=False,colorspace=fitz.csRGB)
        return Image.frombytes('RGB',[pix.width,pix.height],pix.samples),method,p.rotation
def prepare(pdf,requests,outdir,dpi=240):
    pdf=Path(pdf).resolve();out=Path(outdir);out.mkdir(parents=True,exist_ok=True);records=[]
    ids=[req['id'] for req in requests]
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_ASSET_ID')
    if any(Path(i).name!=i or i in ('.','..') for i in ids):raise ValueError('INVALID_ASSET_ID')
    if any((out/(i+'.png')).exists() for i in ids):raise ValueError('OUTPUT_EXISTS')
    for req in requests:
        if not req.get('panels') or 'all' in req['panels']:raise ValueError('EXPLICIT_PANEL_IDENTITIES_REQUIRED')
        im,method,rotation=region(pdf,req['physical_page'],req['bbox_pt'],req.get('dpi',dpi),req.get('page_cache'))
        f=out/(req['id']+'.png')
        if f.exists():raise ValueError('OUTPUT_EXISTS: '+str(f))
        im.save(f)
        records.append(dict(req, path=str(f.resolve()),sha256=sha(f),source_pdf=str(pdf),source_pdf_sha256=sha(pdf),extraction_method=method,
            dpi=req.get('dpi',dpi),rotation=rotation,pixels=list(im.size),fidelity_status='SOURCE_REGION_MATCH',
            panel_mapping_status='PENDING',visual_status='PENDING',semantic_review_status='PARTIAL',
            embedded_policy='Page-region rendering preserves SMask, color management and separate vector labels; isolated embedded extraction never proves full-panel completeness.'))
    reg=dict(version=VERSION,assets=records);save(out/'figure_assets.json',reg);return reg
def validate_asset(a):
    required=['source_pdf','source_pdf_sha256','physical_page','bbox_pt','dpi','sha256','path','panels']
    if any(k not in a for k in required):return dict(valid=False,status='UNVERIFIED',code='FIGURE_SOURCE_MAPPING_REQUIRED')
    try:
        if not a['panels'] or 'all' in a['panels']:raise ValueError('FINE_PANEL_MAPPING_REQUIRED')
        if sha(a['source_pdf'])!=a['source_pdf_sha256'] or sha(a['path'])!=a['sha256']:raise ValueError('FIGURE_INPUT_DRIFT')
        ref,_,rot=region(a['source_pdf'],a['physical_page'],a['bbox_pt'],a['dpi'],a.get('page_cache'))
        with Image.open(a['path']) as img:
            if img.mode not in ['RGB','RGBA']:raise ValueError('FIGURE_COLOR_MODE')
            if img.mode=='RGBA' and img.getextrema()[3]!=(255,255):raise ValueError('FIGURE_UNRESOLVED_ALPHA')
            result=compare(img,ref)
        if rot!=a.get('rotation',rot):raise ValueError('FIGURE_ROTATION')
        return dict(**result,status='SOURCE_REGION_MATCH' if result['valid'] else 'FAIL',code=result['reason'],panel_semantics=a.get('panel_mapping_status','PENDING'),visual_review=a.get('visual_status','PENDING'))
    except (OSError,ValueError,KeyError,TypeError) as e:return dict(valid=False,status='FAIL',code=str(e))
def validate_registry(reg):
    if reg.get('version')!=VERSION:return dict(valid=False,results=[dict(code='FIGURE_REGISTRY_VERSION')])
    ids=[a.get('id') for a in reg.get('assets',[])];results=[dict(id=a.get('id'),**validate_asset(a)) for a in reg.get('assets',[])]
    return dict(valid=bool(results) and len(ids)==len(set(ids)) and all(r['valid'] for r in results),results=results)
def validate_manifest_images(manifest,base):
    figures=[s for s in manifest.get('slides',[]) if s.get('kind')=='figure' and (s.get('images') or s.get('image'))]
    if not figures:return {'valid':True,'status':'NOT_APPLICABLE'}
    f=manifest.get('figure_assets')
    if not f:raise ValueError('FIGURE_ASSET_REGISTRY_REQUIRED')
    reg=read(Path(base)/f) if isinstance(f,str) else f
    assets={str(Path(a['path']).resolve()):a for a in reg['assets']}
    for slide in figures:
        for item in slide.get('images') or [slide['image']]:
            path=item.get('path') if isinstance(item,dict) else item
            p=str((Path(base)/path).resolve())
            if p not in assets:raise ValueError('FIGURE_ASSET_UNREGISTERED: '+p)
            check=validate_asset(assets[p])
            if not check['valid']:raise ValueError('FIGURE_FIDELITY_BLOCKED: '+str(check))
    return {'valid':True,'status':'SOURCE_REGIONS_CHECKED_SEMANTICS_SEPARATE'}
def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('prepare');q.add_argument('--pdf',required=True);q.add_argument('--requests',required=True);q.add_argument('--outdir',required=True);q.add_argument('--dpi',type=int,default=240)
    q=s.add_parser('validate');q.add_argument('registry');a=p.parse_args()
    if a.cmd=='prepare':r=prepare(a.pdf,read(a.requests)['regions'],a.outdir,a.dpi);print(json.dumps({'assets':len(r['assets'])}));return 0
    r=validate_registry(read(a.registry));print(json.dumps(r,ensure_ascii=False));return 0 if r['valid'] else 2
if __name__=='__main__':raise SystemExit(main())

