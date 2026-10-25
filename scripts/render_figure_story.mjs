/** Explicit E1 renderer. Reuses M2-D's template/native-object approach and package helpers. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {inflateRawSync} from 'node:zlib';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readZip,writeZip,slideParts} from './render_adaptive_pptx.mjs';
const HERE=path.dirname(fileURLToPath(import.meta.url));
const sha=b=>createHash('sha256').update(b).digest('hex');
function crc32(b){let c=0xffffffff;for(const x of b){c^=x;for(let j=0;j<8;j++)c=c&1?(c>>>1)^0xedb88320:c>>>1;}return(c^0xffffffff)>>>0;}
function xml(z,k){const e=z.get(k);return(e.method===0?e.data:inflateRawSync(e.data)).toString('utf8');}
function put(z,k,s){const b=Buffer.from(s);z.set(k,{name:k,method:0,crc:crc32(b),size:b.length,data:b,time:0,date:0,external:0});}
function args(v){const o={};for(let i=0;i<v.length;i++){if(v[i]==='--development-preview')o.preview=true;else o[v[i].slice(2)]=v[++i];}return o;}
async function main(o){
 if(!o.preview)throw Error('E1 scoped renderer requires explicit --development-preview');
 for(const k of ['plan','figure','output','python','artifact-module','presentation-skill','build-dir'])if(!o[k])throw Error('Missing --'+k);
 process.env.RUNTIME_NODE_MODULES ||= path.resolve(path.dirname(o['artifact-module']),'../../..');
 const plan=JSON.parse(await fs.readFile(o.plan,'utf8'));if(plan.version!=='m2e1-1'||plan.formal_ready!==false)throw Error('Unsupported E1 preview');
 const check=spawnSync(o.python,['-B',path.join(HERE,'plan_figure_story.py'),'--validate-existing',o.plan,'--development-preview'],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'}});if(check.status!==0)throw Error(check.stdout+check.stderr);
 const slides=plan.slides.filter(s=>s.figure_id===o.figure);if(!slides.length)throw Error('Figure has no story pages');
 const out=path.resolve(o.output),build=path.resolve(o['build-dir']),workspace=path.dirname(path.dirname(out));await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(out),{recursive:true});
 try{await fs.access(out);throw Error('No overwrite: '+out);}catch(e){if(e.code!=='ENOENT')throw e;}
 const z=readZip(await fs.readFile(plan.template.path)),parts=slideParts(z);let root=xml(z,'ppt/presentation.xml');const ids=[...root.matchAll(/<p:sldId\s[^>]*\/>/g)].map(m=>m[0]);
 const refs=slides.map((_,i)=>i+1);if(refs.some(i=>i>=parts.length))throw Error('Not enough distinct template slides');
 root=root.replace(/<p:sldIdLst>[\s\S]*?<\/p:sldIdLst>/,`<p:sldIdLst>${refs.map(i=>ids[i]).join('')}</p:sldIdLst>`);put(z,'ppt/presentation.xml',root);
 const size=/<p:sldSz\b[^>]*\bcx="(\d+)"[^>]*\bcy="(\d+)"/.exec(root);
 for(const i of refs)put(z,parts[i],xml(z,parts[i]).replace(/<p:sp>[\s\S]*?<\/p:sp>/g,s=>{
  if(!/name="(?:PFS_LAYOUT_|DECOR_top|DECOR_titleline|DECOR_footerline)/.test(s))return '';
  const yy=/name="DECOR_titleline"/.test(s)?127:/name="DECOR_footerline"/.test(s)?693:null;
  return yy===null?s:s.replace(/(<a:off\b[^>]*\by=")[^"]+("\s*\/?>)/,(_m,a,b)=>a+Math.round(yy*9525)+b);
 }));
 const scaffold=path.join(build,'template-scaffold.pptx');await fs.writeFile(scaffold,writeZip(z));
 const {PresentationFile,FileBlob}=await import(pathToFileURL(o['artifact-module']).href);const deck=await PresentationFile.importPptx(await FileBlob.load(scaffold));
 const font=plan.style.font_family,assets=new Map(plan.assets.map(a=>[a.id,a])),cards=new Map(plan.cards.map(c=>[c.id,c]));const orientations={};
 function text(slide,name,s,p,fsz,bold=false,color='#18365C'){const t=slide.shapes.add({name,geometry:'textbox',position:p,fill:'none',line:{fill:'none',width:0}});t.text=s;t.text.style={typeface:font,fontSize:fsz,bold,color,alignment:'left',verticalAlignment:'middle',wrap:'none',autoFit:'none',insets:0};}
 for(const [i,s] of slides.entries()){
  const slide=deck.slides.items[i];
  // Pictures first: pointers must remain visible above replaceable image assets.
  for(const e of s.elements.filter(e=>e.kind==='image')){const a=assets.get(e.asset_id),b=await fs.readFile(a.path);if(sha(b)!==a.sha256)throw Error('Asset drift');slide.images.add({name:'E1_'+e.id,position:e.position,blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',fit:'contain',alt:`${a.figure_id} ${a.panels.join(',')} p.${a.physical_page}; ${a.id}; ${a.sha256}`});}
  for(const e of s.elements.filter(e=>e.kind==='rect'))slide.shapes.add({name:'E1_'+e.id,geometry:'rect',position:e.position,fill:'none',line:{fill:e.color,width:1.6}});
  for(const a of s.arrows){for(let k=1;k<a.path.length;k++){const[x,y]=a.path[k-1],[xx,yy]=a.path[k];const name='E1_POINTER_'+s.id+'_'+a.id+'_'+k;orientations[name]={flipH:xx<x,flipV:yy<y};slide.shapes.add({name,geometry:'connector',kind:'straight',position:{left:Math.min(x,xx),top:Math.min(y,yy),width:Math.abs(xx-x),height:Math.abs(yy-y)},line:{fill:'#174994',width:1.7,style:'solid'},head:{type:'none'},tail:{type:k===a.path.length-1?'triangle':'none',width:'sm',length:'sm'}});}}
  for(const e of s.elements.filter(e=>['text','label'].includes(e.kind)))text(slide,'E1_'+e.id,e.kind==='text'?cards.get(e.card_id).text:e.text,e.position,e.font_size_px,e.bold,e.color);
  text(slide,'E1_SECTION',`CNNM4 · Fig.${o.figure.slice(-1)}逐图科研故事 · ${i+1}/${slides.length}`,{left:60,top:28,width:700,height:24},14,true,'#174994');
  text(slide,'E1_REVIEW','研发预览 · 科学审核PARTIAL',{left:938,top:28,width:290,height:24},13,false,'#75808D');
  text(slide,'E1_SOURCE',`Bai et al., Cell (2026) · Fig.${o.figure.slice(-1)}；PDF p.${o.figure.endsWith('2')?'5–6/8':'6'}；Methods p.19 · 原始图像，标注可编辑`,{left:60,top:699,width:1160,height:18},11,false,'#49627F');
  slide.speakerNotes.text=(s.speaker_notes||'')+'\n'+JSON.stringify({entry:'m2e1-1',page_id:s.id,figure_id:s.figure_id,source_rsu_ids:['CNNM4RSU2'],segments:plan.segments.filter(g=>s.segment_ids.includes(g.id)),cards:plan.cards.filter(c=>s.segment_ids.some(id=>plan.segments.find(g=>g.id===id).card_ids.includes(c.id))),arrows:s.arrows,regions:plan.regions.filter(r=>s.arrows.some(a=>a.region_id===r.id)),source_scientific_relations:plan.source_scientific_relations,coverage:plan.coverage,formal_ready:false,source_status:'PARTIAL',independent_reader_test:'NOT_TESTED',warnings:plan.warnings,conflicts:plan.conflicts},null,2);
 }
 const draft=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(deck)).save(draft);
 // Set DrawingML direction explicitly for left/up paths; editable native connectors, no router.
 const dz=readZip(await fs.readFile(draft));let patched=0;
 for(const part of slideParts(dz))put(dz,part,xml(dz,part).replace(/<p:cxnSp\b[\s\S]*?<\/p:cxnSp>/g,s=>{const name=/name="([^"]+)"/.exec(s)?.[1],v=orientations[name];if(!v)return s;patched++;return s.replace(/<a:xfrm\b[^>]*>/,tag=>tag.replace(/\sflip[HV]="[^"]*"/g,'').replace(/>$/,`${v.flipH?' flipH="1"':''}${v.flipV?' flipV="1"':''}>`));}));
 await fs.writeFile(draft,writeZip(dz));
 if(patched!==Object.keys(orientations).length)throw Error('Native connector count mismatch');
 const skill=o['presentation-skill'];const{finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
 await finalizePresentation({workspaceDir:workspace,candidatePath:draft,finalPath:out,pythonExecutable:o.python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',size[1]+','+size[2],'--validate-heading-fit'],explicitTotalSlideCount:slides.length,requiredNativeChartOwnerSlides:[],requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'design',families:[font],scriptFonts:{ea:font}},verifyArtifactToolImport:true,receiptPath:path.join(workspace,'results',o.figure+'.'+path.basename(build)+'.validation.json')});
 const report={figure:o.figure,slides:slides.length,path:out,sha256:sha(await fs.readFile(out)),plan_snapshot:plan.snapshot,native_pointer_segments:patched,router_used:false,formal_ready:false,template_reference_slides:refs.map(i=>i+1),old_entry_unchanged:true};await fs.writeFile(path.join(workspace,'results',o.figure+'.'+path.basename(build)+'.render.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}
main(args(process.argv.slice(2))).catch(e=>{console.error(e.stack);process.exitCode=1;});
