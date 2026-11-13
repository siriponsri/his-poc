#!/usr/bin/env node
/**
 * Read-only reproduction of three HIS POC v0.2.0 frontend state defects.
 * Usage: node reproduce_frontend_state.mjs /absolute/path/to/HIS_POC_Starter
 * Requires Node 24; uses only Node built-ins and the supplied starter's api.ts.
 * No browser, React renderer, dependency installation, database or real network.
 * Extracts actual App.tsx pre-render functions, strips TypeScript, and executes
 * them with minimal hook/transport doubles. This does not test React scheduling,
 * DOM interaction, focus, accessibility or layout. Exit 0 means the probe ran,
 * not that the application passed acceptance. Results name reproduced defects.
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {stripTypeScriptTypes} from 'node:module';

const rootArgument=process.argv[2];
if(!rootArgument){
  console.error('Usage: node reproduce_frontend_state.mjs /absolute/path/to/HIS_POC_Starter');
  process.exit(2);
}
const starterRoot=path.resolve(rootArgument);
const files={app:'apps/web/legacy/App.audit-fixed.tsx.txt',api:'apps/web/src/lib/api.ts',workflow:'apps/web/src/data/workflow.json',records:'apps/web/src/data/thai_records.json'};
const source=fs.readFileSync(path.join(starterRoot,files.app),'utf8');
const frozen=JSON.parse(fs.readFileSync(path.join(starterRoot,files.workflow),'utf8'));
const records=JSON.parse(fs.readFileSync(path.join(starterRoot,files.records),'utf8'));
const apiModule=await import(pathToFileURL(path.join(starterRoot,files.api)).href);
const clone=value=>JSON.parse(JSON.stringify(value));
function fixture(name){
  const row=frozen.responses.find(item=>item.name===name);
  if(!row)throw new Error('Required frozen fixture missing: '+name);
  const context=clone(row.response);
  // Keep these state probes independent of the original fixture's expiry date.
  for(const proposal of context.proposals||[])proposal.expires=Date.now()/1000+900;
  return context;
}
const startMarker='export default function App(){';
const endMarker=' const domain=domains.find';
const start=source.indexOf(startMarker),end=source.indexOf(endMarker);
if(start<0||end<=start)throw new Error('App.tsx layout changed; review the extraction markers before running.');
const actualLogic=source.slice(start+startMarker.length,end);
const exposed='mode,api,ctx,proposal,reviewBinding,reviewDraft,reviewBase,reviewDirty,pendingCommit,confirmed,error,notice,docDirty,setToken,setReviewDraft,switchMode,connect,refresh,review,commit';
const probeSource=stripTypeScriptTypes('function AppProbe(){'+actualLogic+';return {'+exposed+'};}');

function harness(initialContext){
  const state={context:clone(initialContext),handler:null,requests:[]};
  const cells=[];
  let cursor=0;
  async function fetchDouble(url,init){
    if(!url.startsWith('/api/v1/'))throw new Error('Unexpected URL; real network is not available in this probe.');
    const request={path:url.slice('/api/v1/'.length),body:init.body?JSON.parse(init.body):null};
    state.requests.push(request);
    if(state.handler){const response=await state.handler(request);if(response!==undefined)return response;}
    if(request.path==='context')return new Response(JSON.stringify(state.context));
    throw new Error('Unexpected request '+request.path);
  }
  const sandbox={
    ...apiModule,
    HisApi:class extends apiModule.HisApi{constructor(token){super(token,fetchDouble);}},
    useState(initial){
      const index=cursor++;
      if(!(index in cells))cells[index]=initial;
      return [cells[index],value=>{cells[index]=typeof value==='function'?value(cells[index]):value;}];
    },
    useRef:()=>({current:null}),useEffect:()=>{},
    location:{hash:''},window:{confirm:()=>true},records,
    fixtureAdapter:new apiModule.FixtureAdapter(frozen),states:{},
    crypto:{randomUUID:()=> 'isolated-frontend-state-retry-key'}
  };
  vm.createContext(sandbox);
  vm.runInContext(probeSource,sandbox,{filename:'App.tsx extracted pre-render functions'});
  function render(){cursor=0;return vm.runInContext('AppProbe()',sandbox);}
  return {state,render,async connect(){render().switchMode('api');render().setToken('demo-reviewer-token');await render().connect();}};
}

const rejection=harness(fixture('context_approved'));
await rejection.connect();
rejection.state.handler=request=>request.path==='commits'?new Response('{"error":"STALE_CONTEXT"}',{status:409}):undefined;
await rejection.render().commit();
const afterRejection=rejection.render();
await afterRejection.refresh();
const afterRejectionRefresh=rejection.render();

const readback=harness(fixture('context_approved'));
await readback.connect();
readback.state.handler=request=>{
  if(request.path!=='commits')return;
  const committed=fixture('context_committed');
  // Model a committed read-back response, then lose the original HTTP response.
  // No real database write is performed by this reproduction.
  readback.state.context.proposals=committed.proposals;
  readback.state.context.results=committed.results;
  throw new Error('Simulated response lost after commit');
};
await readback.render().commit();
await readback.render().refresh();
const afterReadback=readback.render();

const edit=harness(fixture('context_pending'));
await edit.connect();
edit.render().setReviewDraft('New reviewed summary — synthetic state reproduction');
let failNextContext=false;
edit.state.handler=request=>{
  if(request.path==='reviews'){
    const proposal=edit.state.context.proposals.find(item=>item.id===request.body.proposal_id);
    if(!proposal)throw new Error('Expected proposal missing');
    const action=JSON.parse(proposal.action);action.summary=request.body.edits;
    proposal.action=JSON.stringify(action);proposal.version++;proposal.action_hash='e'.repeat(64);
    failNextContext=true;
    return new Response(JSON.stringify({review_id:'isolated-edit-review',proposal}));
  }
  if(request.path==='context'&&failNextContext){failNextContext=false;throw new Error('Simulated refresh failure after successful edit response');}
};
await edit.render().review('edit');
const afterEdit=edit.render();
const approvedBinding=apiModule.bindReview(afterEdit.proposal,afterEdit.reviewBinding);

const cases=[
  {
    id:'F20-02',name:'Definitive commit rejection remains pending after refresh',
    stimulus:'POST /commits returns HTTP409 STALE_CONTEXT; subsequent GET /context succeeds.',
    expected:'Definitive rejection should lead to a recovery state that allows a fresh proposal/review, without describing the write as unknown.',
    observed:{pending_after_409:!!afterRejection.pendingCommit,pending_after_refresh:!!afterRejectionRefresh.pendingCommit,error:afterRejectionRefresh.error,notice:afterRejectionRefresh.notice,commits_sent:rejection.state.requests.filter(r=>r.path==='commits').length},
    defect_reproduced:!!afterRejection.pendingCommit&&!!afterRejectionRefresh.pendingCommit
  },
  {
    id:'F20-03',name:'Committed read-back does not resolve pending state',
    stimulus:'Commit response is lost; GET /context then supplies the matching committed proposal/result from frozen fixture data.',
    expected:'A verified matching result should reconcile the pending operation and be reflected as confirmed.',
    observed:{readback_results:afterReadback.ctx.results.length,displayed_status:afterReadback.proposal?.status,pending_still_unresolved:!!afterReadback.pendingCommit,confirmed:afterReadback.confirmed,commits_sent:readback.state.requests.filter(r=>r.path==='commits').length},
    defect_reproduced:afterReadback.ctx.results.length>0&&afterReadback.proposal?.status==='committed'&&!!afterReadback.pendingCommit&&afterReadback.confirmed===null
  },
  {
    id:'F20-01',name:'Successful edit plus failed refresh splits displayed and actionable revisions',
    stimulus:'POST /reviews edit returns a new pending version; the immediately following GET /context fails.',
    expected:'Displayed version/hash and the review action binding must stay consistent; otherwise approval must be unavailable.',
    observed:{displayed_proposal_version:afterEdit.proposal.version,displayed_hash:afterEdit.proposal.action_hash,binding_version:afterEdit.reviewBinding.version,binding_hash:afterEdit.reviewBinding.action_hash,review_draft:afterEdit.reviewDraft,review_dirty:afterEdit.reviewDirty,approval_ready:apiModule.approvalReady(afterEdit.proposal,afterEdit.reviewDirty,afterEdit.docDirty),next_approve_binding:{version:approvedBinding.version,action_hash:approvedBinding.action_hash},error:afterEdit.error},
    defect_reproduced:afterEdit.proposal.version!==afterEdit.reviewBinding.version&&afterEdit.proposal.action_hash!==afterEdit.reviewBinding.action_hash&&apiModule.approvalReady(afterEdit.proposal,afterEdit.reviewDirty,afterEdit.docDirty)
  }
];
const report={
  report_version:'1.0',generated_at:new Date().toISOString(),node_version:process.version,starter_root:starterRoot,
  method:'Actual App.tsx pre-render functions + actual HisApi/decoders + minimal state-hook and HTTP doubles; no React renderer/browser.',
  source_sha256:Object.fromEntries(Object.values(files).map(relative=>[relative,crypto.createHash('sha256').update(fs.readFileSync(path.join(starterRoot,relative))).digest('hex')])),
  fixture_transform:'Proposal expires set to current time +900 seconds in memory to isolate revision/recovery behavior; original files unchanged.',
  source_files_modified:false,real_network_calls:false,real_database_writes:false,browser_assertions:0,visual_qa:'NOT_RUN',
  cases,summary:{cases_executed:cases.length,defects_reproduced:cases.filter(item=>item.defect_reproduced).length,exit_zero_meaning:'Probe completed; this is not an application acceptance PASS.'}
};
console.log(JSON.stringify(report,null,2));

if(report.cases.some(c=>c.defect_reproduced))process.exitCode=1;
