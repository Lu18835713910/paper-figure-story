/** Explicit M2-D R&D preview renderer. Does not call a graph router or legacy manifest. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { inflateRawSync } from 'node:zlib';
import { spawnSync } from 'node:child_process';
import { readZip, writeZip, slideParts } from './render_adaptive_pptx.mjs';
const HERE=path.dirname(fileURLToPath(import.meta.url));
const sha=async p=>(await import('node:crypto')).createHash('sha256').update(await fs.readFile(p)).digest('hex');
function argsOf(argv){const a={};for(let i=0;i<argv.length;i++){if(argv[i]==='--development-preview')a.preview=true;else{if(!argv[i].startsWith('--')||!argv[i+1])throw Error('Explicit option/value required');a[argv[i].slice(2)]=argv[++i];}}return a;}
function crc32(b){let c=0xffffffff;for(const x of b){c^=x;for(let j=0;j<8;j++)c=c&1?(c>>>1)^0xedb88320:c>>>1;}return (c^0xffffffff)>>>0;}
function xml(zip,name){const e=zip.get(name);if(!e)throw Error('Missing part '+name);return (e.method===0?e.data:inflateRawSync(e.data)).toString('utf8');}
function put(zip,name,value){const data=Buffer.from(value,'utf8');zip.set(name,{name,method:0,crc:crc32(data),size:data.length,data,time:0,date:0,external:0});}
function requireOkay(proc){if(proc.error||proc.status!==0)throw Error(proc.error?.message||proc.stdout+'\n'+proc.stderr);}
export async function renderNarrative(options){
  if(!options.preview)throw Error('This explicit prototype entry requires --development-preview; formal publishing is not implemented.');
  for(const key of ['plan','output','artifact-module','python','presentation-skill'])if(!options[key])throw Error('Missing --'+key);
  const planPath=path.resolve(options.plan),output=path.resolve(options.output),workspace=path.dirname(path.dirname(output)),build=path.resolve(options['build-dir']||path.join(workspace,'build','authoring'));
  await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(output),{recursive:true});
  try{await fs.access(output);throw Error('Refusing to overwrite output '+output);}catch(e){if(e.code!=='ENOENT')throw e;}
  const proc=spawnSync(options.python,['-B',path.join(HERE,'project_narrative_ppt.py'),'--validate-existing',planPath,'--development-preview'],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'}});requireOkay(proc);
  const plan=JSON.parse(await fs.readFile(planPath,'utf8'));
  if(plan.narrative_ppt_version!=='m2d-preview-1'||plan.render_mode!=='development_preview'||plan.formal_ready!==false)throw Error('Unsupported prototype state');
  const source=plan.inputs.template.path,zip=readZip(await fs.readFile(source)),parts=slideParts(zip);
  let root=xml(zip,'ppt/presentation.xml');const size=/<p:sldSz\b[^>]*\bcx="(\d+)"[^>]*\bcy="(\d+)"/.exec(root);if(!size)throw Error('Unknown slide dimensions');
  const ids=[...root.matchAll(/<p:sldId\s[^>]*\/>/g)].map(m=>m[0]);
  const refs=plan.slides.map(s=>s.template_reference_slide-1);if(refs.some(i=>!Number.isInteger(i)||i<0||i>=parts.length))throw Error('Invalid template page reference');
  root=root.replace(/<p:sldIdLst>[\s\S]*?<\/p:sldIdLst>/,`<p:sldIdLst>${refs.map(i=>ids[i]).join('')}</p:sldIdLst>`);put(zip,'ppt/presentation.xml',root);
  for(const i of refs){let s=xml(zip,parts[i]);s=s.replace(/<p:sp>[\s\S]*?<\/p:sp>/g,shape=>{
    const name=/<p:cNvPr\b[^>]*\bname="([^"]*)"/.exec(shape)?.[1]||'';
    const furniture=/^(PFS_GRAPH_AREA$|DECOR_figurebg$|DECOR_rightbg$)/.test(name);
    return /^(PFS_LAYOUT_|DECOR_top$|DECOR_titleline$|DECOR_footerline$)/.test(name)||(furniture&&plan.style.template_content_frames!==false)?shape:'';
  });put(zip,parts[i],s);}
  const scaffold=path.join(build,'template-scaffold.pptx');await fs.writeFile(scaffold,writeZip(zip),{flag:'wx'});
  const {PresentationFile,FileBlob}=await import(pathToFileURL(path.resolve(options['artifact-module'])).href);
  const p=await PresentationFile.importPptx(await FileBlob.load(scaffold));if(p.slides.items.length!==plan.slides.length)throw Error('Scaffold import changed slide count');
  const font=plan.style.font_family;
  for(const [i,s] of plan.slides.entries()){
    const slide=p.slides.items[i];
    for(const c of s.connectors){const [x,y]=c.start,[xx,yy]=c.end;
      slide.shapes.add({geometry:'connector',kind:'straight',name:'PFS_NARRATIVE_'+c.id,position:{left:Math.min(x,xx),top:Math.min(y,yy),width:Math.abs(xx-x),height:Math.abs(yy-y)},line:{fill:plan.style.accent,width:c.arrow?1.7:1.1,style:'solid'},head:{type:'none'},tail:{type:c.arrow?'triangle':'none',width:'sm',length:'sm'}});
    }
    for(const e of s.elements){
      const common={name:'PFS_NARRATIVE_'+e.id,position:e.position};
      if(e.kind==='image'){
        const a=plan.panel_assets.assets.find(a=>a.id===e.asset_id),bytes=await fs.readFile(a.path);
        if(await sha(a.path)!==a.sha256)throw Error('Asset drift at authoring');
        slide.images.add({...common,blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',alt:`${a.figure_id} panel ${a.panels.join(',')}; original PDF physical p.${a.physical_page}; asset ${a.id}`,fit:'contain'});
      }else{
        const shape=slide.shapes.add({...common,geometry:e.kind==='text'?'textbox':'rect',fill:e.fill||'none',line:{fill:e.stroke||'none',width:e.stroke_width_px||0}});
        if(e.kind==='text'){shape.text=e.text;shape.text.style={typeface:font,fontSize:e.font_size_px,bold:e.bold||false,color:e.color||'#18365C',alignment:e.alignment||'left',verticalAlignment:'middle',autoFit:'none',wrap:'none',insets:0};}
      }
    }
    const bindings=plan.source_map.filter(b=>b.slide_id===s.id);
    const notes={kind:'M2-D development preview',formal_ready:plan.formal_ready,source_base_snapshot:plan.source_narrative.base_snapshot,source_rsu_ids:plan.segments[i].source_rsu_ids,figure_ids:plan.segments[i].figure_ids,
      narrative_unit_ids:s.source_unit_ids,source_map:bindings,statements:plan.source_narrative.statements,resolved_bindings:plan.source_narrative.resolved_bindings,
      mandatory_limits:plan.source_narrative.mandatory_limits,conflicts:plan.source_narrative.conflicts,scientific_relations:plan.source_scientific_relations,
      presentation_arrows:'Layout/argument organization only. No experimental history or scientific causality is inferred.',panel_assets:plan.panel_assets.assets,
      source_documents:plan.source_narrative.metadata.provenance,review_warning:'M2-C PARTIAL remains unchanged. Author scoped panel inspection is not independent scientific acceptance.'};
    slide.speakerNotes.text=s.notes+'\n\n'+JSON.stringify(notes,null,2);
  }
  const candidate=path.join(build,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
  const skill=path.resolve(options['presentation-skill']);const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
  const receipt=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath:output,pythonExecutable:options.python,
    integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs:['--expected-slide-size-emu',size[1]+','+size[2],'--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:plan.slides.length,
    requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[font],scriptFonts:{ea:font}},verifyArtifactToolImport:true,
    receiptPath:path.join(workspace,'results',path.basename(build)+'.validation.json')});
  const report={version:plan.narrative_ppt_version,output,sha256:await sha(output),slide_count:plan.slides.length,formal_ready:false,template:source,template_reference_slides:refs.map(i=>i+1),source_narrative_snapshot:plan.source_narrative.base_snapshot,
    scientific_relations_added:0,router_used:false,authoring:'Artifact Tool native text/shapes/lines, embedded replaceable original panel PNGs',validation_stdout:proc.stdout,finalizer:receipt};
  await fs.writeFile(path.join(workspace,'results','render_execution.json'),JSON.stringify(report,null,2));return report;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))renderNarrative(argsOf(process.argv.slice(2))).then(r=>console.log(JSON.stringify({output:r.output,slides:r.slide_count,formal_ready:false}))).catch(e=>{console.error(e.stack);process.exitCode=1;});


