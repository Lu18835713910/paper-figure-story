/** Explicit RC renderer. Source plan is validated before all native-object authoring. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {inflateRawSync} from 'node:zlib';
import {spawnSync} from 'node:child_process';
import {readZip,writeZip,slideParts} from './render_adaptive_pptx.mjs';
import {humanSpeakerNotes} from './speaker_notes.mjs';
const HERE=path.dirname(fileURLToPath(import.meta.url));
const sha=b=>createHash('sha256').update(b).digest('hex');
function crc32(b){let c=0xffffffff;for(const v of b){c^=v;for(let j=0;j<8;j++)c=c&1?(c>>>1)^0xedb88320:c>>>1;}return(c^0xffffffff)>>>0;}
function xml(z,n){const e=z.get(n);return(e.method===0?e.data:inflateRawSync(e.data)).toString('utf8');}
function put(z,n,s){const b=Buffer.from(s);z.set(n,{name:n,method:0,crc:crc32(b),size:b.length,data:b,time:0,date:0,external:0});}
function args(v){const a={};for(let i=0;i<v.length;i++){if(v[i]==='--development-preview')a.preview=true;else{if(!v[i].startsWith('--')||!v[i+1])throw Error('Explicit flag/value required');a[v[i].slice(2)]=v[++i];}}return a;}
function mustRun(exe,argv){const r=spawnSync(exe,argv,{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'}});if(r.error||r.status!==0)throw Error(r.error?.message||r.stdout+'\n'+r.stderr);return r.stdout;}

async function scaffold(template,count,build){
 const bytes=await fs.readFile(template);const z=readZip(bytes),parts=slideParts(z);
 const ref=parts[Math.min(5,parts.length-1)];let page=xml(z,ref);
 page=page.replace(/<p:sp>[\s\S]*?<\/p:sp>/g,s=>{
   if(!/name="(?:PFS_LAYOUT_|DECOR_top|DECOR_titleline|DECOR_footerline)/.test(s))return '';
   const y=/name="DECOR_titleline"/.test(s)?127:/name="DECOR_footerline"/.test(s)?693:null;
   return y===null?s:s.replace(/(<a:off\b[^>]*\by=")[^"]+("\s*\/?>)/,(_m,a,b)=>a+Math.round(y*9525)+b);
 });
 const refRel=path.posix.dirname(ref)+'/_rels/'+path.posix.basename(ref)+'.rels';
 const relText=z.has(refRel)?xml(z,refRel):null;
 let root=xml(z,'ppt/presentation.xml'),rels=xml(z,'ppt/_rels/presentation.xml.rels'),types=xml(z,'[Content_Types].xml');const ids=[];
 const size=/<p:sldSz\b[^>]*\bcx="(\d+)"[^>]*\bcy="(\d+)"/.exec(root);
 for(let i=0;i<count;i++){
   const filename='pfsEvidence'+(i+1)+'.xml',n='ppt/slides/'+filename,rid='rIdEvidenceRC'+(i+1);
   put(z,n,page);if(relText)put(z,'ppt/slides/_rels/'+filename+'.rels',relText);
   rels=rels.replace('</Relationships>',`<Relationship Id="${rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/${filename}"/></Relationships>`);
   types=types.replace('</Types>',`<Override PartName="/${n}" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>`);
   ids.push(`<p:sldId id="${500+i}" r:id="${rid}"/>`);
 }
 root=root.replace(/<p:sldIdLst>[\s\S]*?<\/p:sldIdLst>/,`<p:sldIdLst>${ids.join('')}</p:sldIdLst>`);
 put(z,'ppt/presentation.xml',root);put(z,'ppt/_rels/presentation.xml.rels',rels);put(z,'[Content_Types].xml',types);
 const out=path.join(build,'scaffold.pptx');await fs.writeFile(out,writeZip(z));
 return {path:out,size:size[1]+','+size[2],templateSha:sha(bytes)};
}

export async function renderEvidenceProducts(o){
 for(const k of ['network','plan','output-dir','build-dir','python','artifact-module','presentation-skill'])if(!o[k])throw Error('Missing --'+k);
 if(!o.preview)throw Error('Independent scientific review is incomplete; explicit --development-preview required.');
 process.env.RUNTIME_NODE_MODULES ||= path.resolve(path.dirname(o['artifact-module']),'../../..');
 const net=JSON.parse(await fs.readFile(o.network,'utf8')),plan=JSON.parse(await fs.readFile(o.plan,'utf8'));
 if(plan.version!=='pfs-products-1'||plan.formal_ready!==false)throw Error('Invalid candidate plan version/review gate');
 mustRun(o.python,[path.join(HERE,'run_pfs.py'),'validate-products','--network',o.network,'--plan',o.plan,...(o.metadata?['--metadata',o.metadata]:[])]);
 const logicEdges=plan.research_logic?new Map(JSON.parse(await fs.readFile(plan.research_logic.path,'utf8')).edges.map(e=>[e.id,e])):new Map();
 const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(o['artifact-module']).href);
 const {finalizePresentation}=await import(pathToFileURL(path.join(o['presentation-skill'],'container_tools/artifact_tool_utils.mjs')).href);
 const assets=new Map(net.assets.map(a=>[a.id,a]));const orientations={};const reports=[];
 const outRoot=path.resolve(o['output-dir']),buildRoot=path.resolve(o['build-dir']);await fs.mkdir(outRoot,{recursive:true});await fs.mkdir(buildRoot,{recursive:true});
 const workspace=path.dirname(outRoot);
 function text(slide,name,value,p,size,bold=false,color='#18365C',align='left'){
   const t=slide.shapes.add({name,geometry:'textbox',position:p,fill:'none',line:{fill:'none',width:0}});t.text=value;
   t.text.style={typeface:plan.style.font_family,fontSize:size,bold,color,alignment:align,verticalAlignment:'middle',wrap:'none',autoFit:'none',insets:0};return t;
 }
 for(const product of plan.products){
   const build=path.join(buildRoot,product.kind);await fs.mkdir(build,{recursive:true});
   let deck,expected;
   if(product.kind==='main'||product.kind==='experiment_cards'){
     const base=await scaffold(plan.template.path,product.slides.length,build);
     if(base.templateSha!==plan.template.sha256)throw Error('Template fingerprint drift');
     deck=await PresentationFile.importPptx(await FileBlob.load(base.path));expected=base.size;
   }else{
     deck=Presentation.create({slideSize:{width:product.width,height:product.height}});
     for(const s of product.slides)deck.slides.add();
     expected=Math.round(product.width*9525)+','+Math.round(product.height*9525);
   }
   const machinePages=[];
   for(const [i,scene] of product.slides.entries()){
     const slide=deck.slides.items[i];
     if(product.kind==='detail'){
       slide.background.fill='#FFFFFF';
       slide.shapes.add({name:'RC_BLUE_BAR',geometry:'rect',position:{left:0,top:0,width:product.width,height:14},fill:plan.style.accent,line:{fill:'none',width:0}});
     }
     for(const e of scene.elements.filter(x=>x.kind==='image')){
       const a=assets.get(e.asset_id);if(!a)throw Error('Unknown original image '+e.asset_id);
       const b=await fs.readFile(a.path);if(sha(b)!==a.sha256)throw Error('Original Figure fingerprint drift '+a.id);
       slide.images.add({name:'RC_'+scene.id+'_'+e.id,position:e.position,blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',fit:'contain',alt:JSON.stringify({asset_id:a.id,figure_id:a.figure_id,panels:a.panels,page:a.physical_page,sha256:a.sha256,review:a.review})});
     }
     for(const e of scene.elements.filter(x=>['rect','down_arrow'].includes(x.kind)))slide.shapes.add({name:'RC_'+scene.id+'_'+e.id,geometry:e.kind==='down_arrow'?'downArrow':'rect',position:e.position,fill:e.kind==='down_arrow'?plan.style.accent:e.fill,line:{fill:e.kind==='down_arrow'?'none':(e.stroke||'none'),width:e.kind==='down_arrow'?0:1}});
     for(const a of scene.connectors||[]){
       const logical=a.source_logic_relation_id&&logicEdges.get(a.source_logic_relation_id);
       if(logical&&(logical.identity!==a.identity||logical.type!==a.relation_type))throw Error('Logic relationship identity drift');
       if(!['presentation','author_argument_candidate'].includes(a.identity)&&!a.source_relation_id&&!logical)throw Error('Scientific arrow without registered relation ID or validated logic binding');
       const points=a.points.filter((p,i,all)=>i===0||p[0]!==all[i-1][0]||p[1]!==all[i-1][1]);
       if(points.length<2)throw Error('Degenerate entire connector '+a.id);
       for(let j=1;j<points.length;j++){
         const[x,y]=points[j-1],[xx,yy]=points[j];const name='RC_EDGE_'+scene.id+'_'+a.id+'_'+j;
         orientations[name]={flipH:xx<x,flipV:yy<y};
         slide.shapes.add({name,geometry:'connector',kind:'straight',position:{left:Math.min(x,xx),top:Math.min(y,yy),width:Math.abs(xx-x),height:Math.abs(yy-y)},line:{fill:a.color||plan.style.accent,width:product.kind==='main'?1.7:2.2,style:a.dashed?'dashed':'solid'},head:{type:'none'},tail:{type:a.arrow&&j===points.length-1?'triangle':'none',width:'sm',length:'sm'}});
       }
     }
     for(const e of scene.elements.filter(x=>x.kind==='text'))text(slide,'RC_'+scene.id+'_'+e.id,e.text,e.position,e.font_size,e.bold,e.color,e.align);
     if(product.kind==='main'||product.kind==='experiment_cards'){
       text(slide,'RC_SECTION',scene.section||(scene.product==='A'?'全文科研逻辑简要版':scene.product==='B2'?'实验级信息卡 · 来源与数量审核':('逐Figure科研故事 · '+scene.figure_ids.join(' / '))),{left:60,top:28,width:770,height:24},14,true,plan.style.accent);
       text(slide,'RC_REVIEW','来源与限制见备注',{left:984,top:28,width:245,height:24},13,false,'#75808D');
       text(slide,'RC_FOOTNOTE',scene.citation,{left:60,top:699,width:1160,height:18},10,false,'#49627F');
     }else text(slide,'RC_FOOTNOTE',scene.citation,{left:60,top:product.height-65,width:product.width-120,height:38},15,false,'#49627F');
     machinePages.push({entry:'pfs-evidence-products-1',profile:plan.profile,scene_id:scene.id,product:scene.product,
       source_statement_ids:scene.source_statement_ids,source_node_ids:scene.source_node_ids,source_relation_ids:scene.source_relation_ids,
       narrative_arrows:(scene.elements||[]).filter(x=>x.kind==='down_arrow').map(x=>({id:x.id,identity:'presentation'})),
       scientific_edges_added:0,figure_ids:scene.figure_ids,coverage:scene.coverage,notes:scene.notes,formal_ready:false,
       ...(scene.logic_snapshot?{logic_snapshot:scene.logic_snapshot,source_logic_node_ids:scene.source_logic_node_ids,source_logic_relation_ids:scene.source_logic_relation_ids}: {})});
     slide.speakerNotes.text=humanSpeakerNotes(scene,net,plan.profile);
   }
   const auditRoot=path.join(workspace,'audit');await fs.mkdir(auditRoot,{recursive:true});
   await fs.writeFile(path.join(auditRoot,product.kind+'_'+plan.profile+'.json'),JSON.stringify({version:'pfs-machine-notes-1',network_snapshot:net.snapshot,inputs:net.inputs,pages:machinePages},null,2));
   const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(deck)).save(candidate);
   const z=readZip(await fs.readFile(candidate));
   for(const part of slideParts(z))put(z,part,xml(z,part).replace(/<p:cxnSp\b[\s\S]*?<\/p:cxnSp>/g,s=>{
     const name=/name="([^"]+)"/.exec(s)?.[1],v=orientations[name];if(!v)return s;
     return s.replace(/<a:xfrm\b[^>]*>/,tag=>tag.replace(/\sflip[HV]="[^"]*"/g,'').replace(/>$/,`${v.flipH?' flipH="1"':''}${v.flipV?' flipV="1"':''}>`));
   }));await fs.writeFile(candidate,writeZip(z));
   mustRun(o.python,[path.join(HERE,'apply_script_fonts.py'),candidate]);
   const final=path.join(outRoot,product.kind+'_'+plan.profile+'.pptx');
   const receipt=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath:final,pythonExecutable:o.python,
     integrityValidatorPath:path.join(o['presentation-skill'],'container_tools/inspect_presentation_package_integrity.py'),
     layoutValidatorPath:path.join(o['presentation-skill'],'container_tools/inspect_presentation_layout_geometry.py'),
     layoutArgs:['--expected-slide-size-emu',expected,'--validate-heading-fit'],explicitTotalSlideCount:product.slides.length,
     requiredNativeChartOwnerSlides:[],requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'user_request',families:['Times New Roman',plan.style.font_family],scriptFonts:{ea:plan.style.font_family,cs:'Times New Roman'}},
     verifyArtifactToolImport:true,receiptPath:path.join(build,'finalization.json')});
   reports.push({kind:product.kind,path:final,sha256:sha(await fs.readFile(final)),slides:product.slides.length,width:product.width,height:product.height,
                 package_findings:receipt.packageIntegrity.finding_count,formal_ready:false});
 }
 const report={version:'pfs-render-receipt-1',network_snapshot:net.snapshot,profile:plan.profile,files:reports,source_relations_added:0,router_used:false,formal_ready:false};
 await fs.writeFile(path.join(buildRoot,'render_receipt.json'),JSON.stringify(report,null,2));return report;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))renderEvidenceProducts(args(process.argv.slice(2))).then(r=>console.log(JSON.stringify(r))).catch(e=>{console.error(e.stack);process.exitCode=1;});
