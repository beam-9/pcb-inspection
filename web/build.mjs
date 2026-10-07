import {build} from 'esbuild';
import {mkdir,copyFile,readFile,writeFile,cp,rm} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
const publicPreview=process.argv.includes('--public');
const out=publicPreview?'public-dist':'dist';
const root=path.resolve('..');
const read=async p=>JSON.parse(await readFile(path.join(root,p),'utf8'));
const hash=async p=>createHash('sha256').update(await readFile(p)).digest('hex');
await rm(out,{recursive:true,force:true});
await mkdir(out,{recursive:true});
await build({entryPoints:['src/App.jsx'],bundle:true,minify:true,format:'esm',outfile:out+'/app.js',loader:{'.woff2':'file','.woff':'file'},assetNames:'fonts/[name]-[hash]',define:{'process.env.NODE_ENV':'"production"','__PUBLIC_PREVIEW__':String(publicPreview)}});
await copyFile('index.html',out+'/index.html');
if(publicPreview){
 const config=await read('artifacts/model_v1/final_config.json');
 const receipt=await read('artifacts/model_v1/final_model_receipt.json');
 const metrics=await read('artifacts/model_v1/final_metrics.json');
 const journey=await read('content/journey.json');
 const purpose=await read('content/purpose.json');
 const index=await read('content/evidence_index.json');
 const history=await read('artifacts/productization/historical_preservation.json');
 const preserved=new Map(history.checks.map(x=>[x.path,x.preserved_at]));
 const exported=await read('artifacts/productization/public_export.json');
 for(const [p,expected] of Object.entries(receipt.artifact_identities)){
  if(await hash(path.join(root,p))!==expected)throw new Error('Frozen artifact changed: '+p);
 }
 await mkdir(out+'/metadata',{recursive:true});
 const model={name:receipt.model_name,version:receipt.version,recipe_commit:receipt.git_commit,frozen_at:receipt.freeze_timestamp,input_size:config.input_size,backbone:config.backbone,feature_layers:config.feature_layers,memory_size:config.memory.shape[0],thresholds:config.thresholds,metrics,limitations:config.limitations,config};
 await writeFile(out+'/metadata/model.json',JSON.stringify(model));
 for(const name of ['journey','examples','purpose','evidence_index'])await copyFile(path.join(root,'content/'+name+'.json'),out+'/metadata/'+name+'.json');
 await cp('assets',out+'/assets',{recursive:true});
 await mkdir(out+'/benchmarks',{recursive:true});
 for(const item of exported.checks){
  const p=path.join(root,'content/benchmark_results/'+item.id+'.json');
  if(await hash(p)!==item.sha256)throw new Error('Saved inspection changed: '+item.id);
  const result=JSON.parse(await readFile(p,'utf8'));
  if(result.model_receipt_sha256!==await hash(path.join(root,'artifacts/model_v1/final_model_receipt.json')))throw new Error('Saved model identity changed');
  await copyFile(p,out+'/benchmarks/'+item.id+'.json');
 }
 const sources=new Map();
 for(const stage of journey.stages){
  for(const item of [...stage.figures,...stage.sources,...stage.metrics.map(m=>m.source)])sources.set(item.path,item.sha256);
 }
 for(const item of purpose.sources)sources.set(item.path,item.sha256);
 for(const p of ['final_model_receipt.json','final_config.json','final_metrics.json','limitations.md','reproducibility.md','final_bank_hash.txt'])sources.set('artifacts/model_v1/'+p,null);
 for(const item of index.files)sources.set(item.path,item.sha256);
 for(const [p,expected] of sources){
  const source=path.join(root,preserved.get(p)||p);
  const target=path.resolve(out,'evidence',p);
  if(!target.startsWith(path.resolve(out,'evidence')+path.sep))throw new Error('Invalid evidence path');
  if(expected&&await hash(source)!==expected)throw new Error('Evidence changed: '+p);
  await mkdir(path.dirname(target),{recursive:true});await copyFile(source,target);
 }
 console.log('Static portfolio: verified evidence and six labelled recorded results; no live upload API.');
}
