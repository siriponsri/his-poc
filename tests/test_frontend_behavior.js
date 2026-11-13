// Isolated execution of the real inline script with DOM/fetch doubles.
// These checks do not launch a browser or establish visual/accessibility QA.
// Run: node --test tests/test_frontend_behavior.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'web', 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const clone = value => JSON.parse(JSON.stringify(value));
const reply = (value, status = 200) => ({ok:status >= 200 && status < 300,status,json:async()=>clone(value)});
function sampleContext(proposalStatus) {
  const evidence = {encounter_version:1,document_id:'d-demo',document_version:4,document_hash:'b'.repeat(64),locator:'document.content',data_class:'synthetic'};
  const context = {
    demo:true,patient:'p-demo',encounter:{id:'e-demo',patient:'p-demo',version:1,status:'open'},
    document:{id:'d-demo',encounter:'e-demo',version:4,content:JSON.stringify({text:'Persisted edited document',author:'previous-author',signed_at:'2026-11-12T00:00:00Z'})},
    evidence,tasks:[],reviews:[],proposal_versions:[],proposals:[],results:[],runs:[],audit:[]
  };
  if(proposalStatus)context.proposals.push({id:'proposal-1',patient:'p-demo',encounter:'e-demo',version:1,action:JSON.stringify({kind:'document_completeness',summary:'Review this synthetic document',missing_fields:['signed_at']}),action_hash:'a'.repeat(64),snapshot:JSON.stringify(evidence),status:proposalStatus,expires:Date.now()/1000+900,run_id:'run-1'});
  return context;
}
function harness(context = sampleContext()) {
  const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(match=>[match[1],{value:'',textContent:'',className:'',disabled:false}]));
  elements.token.value='demo-reviewer-token';
  const buttons = [...html.matchAll(/<button[^>]*>/g)].map(match=>{
    const id=match[0].match(/id="([^"]+)"/);
    return id?elements[id[1]]:{disabled:false};
  });
  const state={context:clone(context),requests:[],handler:null};
  let keys=0;
  const sandbox={document:{getElementById:id=>elements[id],querySelectorAll:selector=>{assert.equal(selector,'button');return buttons;}},crypto:{randomUUID:()=> 'idempotency-key-'+(++keys)},fetch:async(url,options)=>{
    const request={path:url.replace('/api/v1/',''),method:options.method,body:options.body?JSON.parse(options.body):null};
    state.requests.push(request);
    if(state.handler){const response=await state.handler(request);if(response!==undefined)return response;}
    if(request.path==='context')return reply(state.context);
    throw new Error('Unexpected request '+request.path);
  }};
  vm.createContext(sandbox);vm.runInContext(script,sandbox,{filename:'web/index.html'});
  return {state,elements,buttons,run:code=>vm.runInContext(code,sandbox),value:code=>JSON.parse(vm.runInContext('JSON.stringify('+code+')',sandbox)),out:()=>JSON.parse(elements.out.textContent)};
}
function committedResult(){return {id:'result-1',proposal:'proposal-1',patient:'p-demo',encounter:'e-demo',action:{kind:'document_completeness',summary:'Review this synthetic document',missing_fields:['signed_at']},review:'review-1',demo:true};}

test('loading hydrates the editor; saving preserves document metadata and uses its version',async()=>{
  const h=harness();
  await h.run('load()');
  assert.equal(h.elements.document.value,'Persisted edited document');
  h.elements.document.value='Reviewer changed the persisted text';
  h.state.handler=request=>{
    if(request.path!=='documents')return;
    assert.equal(request.body.expected_version,4);
    assert.deepEqual(request.body.content,{text:'Reviewer changed the persisted text',author:'previous-author',signed_at:'2026-11-12T00:00:00Z'});
    h.state.context.document.content=JSON.stringify(request.body.content);
    h.state.context.document.version=5;h.state.context.evidence.document_version=5;
    return reply({version:5});
  };
  await h.run('saveDocument()');
  assert.equal(h.value('documentDraft.version'),5);
  assert.equal(h.elements.document.value,'Reviewer changed the persisted text');
  assert.equal(h.elements.save.disabled,true);
});

test('refresh preserves a dirty draft and its old write version; explicit discard loads latest',async()=>{
  const h=harness();await h.run('load()');
  h.elements.document.value='Unsaved local draft';
  h.state.context.document.version=5;h.state.context.evidence.document_version=5;
  h.state.context.document.content=JSON.stringify({text:'Newer server text',author:'other-author'});
  await h.run('load()');
  assert.equal(h.elements.document.value,'Unsaved local draft');
  assert.equal(h.value('documentDraft.version'),4);
  h.state.handler=request=>request.path==='documents'?reply({error:'STALE_DOCUMENT'},409):undefined;
  await h.run('saveDocument()');
  assert.equal(h.state.requests.find(r=>r.path==='documents').body.expected_version,4);
  assert.equal(h.out().error,'STALE_DOCUMENT');
  assert.equal(h.elements.document.value,'Unsaved local draft');
  await h.run('load(true)');
  assert.equal(h.elements.document.value,'Newer server text');
  assert.equal(h.value('documentDraft.version'),5);
});

test('a network failure replaces old success output with a visible error',async()=>{
  const h=harness();await h.run('load()');
  h.state.handler=request=>{if(request.path==='proposals')throw new Error('offline');};
  await h.run('propose()');
  assert.equal(h.out().error,'NETWORK_ERROR');
  assert.equal(h.elements.status.className,'error');
  assert.equal(h.value('busy'),false);
  assert.equal(h.elements.propose.disabled,false);
});

test('non-JSON responses are visible and do not leave controls busy',async()=>{
  const h=harness();await h.run('load()');
  h.state.handler=()=>({ok:false,status:502,json:async()=>{throw new Error('HTML gateway response');}});
  await h.run('load()');
  assert.equal(h.out().error,'INVALID_RESPONSE');
  assert.equal(h.elements.status.className,'error');
  assert.equal(h.value('busy'),false);
  assert.equal(h.elements.token.disabled,false);
});

test('commit reconciles displayed status; same-page replay keeps its original key; reload reads persistence',async()=>{
  const h=harness(sampleContext('approved'));await h.run('load()');
  let commits=0;
  h.state.handler=request=>{
    if(request.path!=='commits')return;
    h.state.context.proposals[0].status='committed';
    h.state.context.results=[committedResult()];
    return reply({result:committedResult(),replayed:commits++>0});
  };
  await h.run('commit()');
  assert.equal(h.value('current.status'),'committed');
  assert.equal(JSON.parse(h.elements.proposal.textContent).status,'committed');
  assert.equal(h.out().replayed,false);
  await h.run('commit()');
  const requests=h.state.requests.filter(r=>r.path==='commits');
  assert.deepEqual(requests[0].body,requests[1].body);
  assert.equal(h.out().replayed,true);
  const reloaded=harness(h.state.context);await reloaded.run('load()');
  assert.equal(reloaded.value('current.status'),'committed');
  assert.equal(reloaded.value('ctx.results[0].id'),'result-1');
  assert.equal(reloaded.elements.commit.disabled,true);
});

test('lost commit response retains an immutable retry payload and does not permit a new proposal',async()=>{
  const h=harness(sampleContext('approved'));await h.run('load()');
  let commits=0;
  h.state.handler=request=>{
    if(request.path!=='commits')return;
    if(commits++===0)throw new Error('response lost');
    h.state.context.proposals[0].status='committed';h.state.context.results=[committedResult()];
    return reply({result:committedResult(),replayed:true});
  };
  await h.run('commit()');
  const original=h.value('pendingCommit');
  assert.equal(h.out().error,'NETWORK_ERROR');
  assert.equal(h.elements.propose.disabled,true);
  assert.equal(h.elements.commit.disabled,false);
  await h.run('propose()');
  assert.equal(h.out().error,'COMMIT_OUTCOME_UNKNOWN');
  assert.equal(h.state.requests.filter(r=>r.path==='proposals').length,0);
  await h.run('commit()');
  const requests=h.state.requests.filter(r=>r.path==='commits');
  assert.deepEqual(requests[0].body,original);
  assert.deepEqual(requests[1].body,original);
  assert.equal(h.value('pendingCommit'),null);
  assert.equal(h.out().replayed,true);
});

test('reading a persisted result resolves an unknown commit without writing again',async()=>{
  const h=harness(sampleContext('approved'));await h.run('load()');
  h.state.handler=request=>{
    if(request.path!=='commits')return;
    h.state.context.proposals[0].status='committed';h.state.context.results=[committedResult()];
    throw new Error('response lost after commit');
  };
  await h.run('commit()');
  assert.notEqual(h.value('pendingCommit'),null);
  await h.run('load()');
  assert.equal(h.value('pendingCommit'),null);
  assert.equal(h.value('current.status'),'committed');
  assert.equal(h.state.requests.filter(r=>r.path==='commits').length,1);
});

test('double-clicking while commit is in flight sends only one mutation',async()=>{
  const h=harness(sampleContext('approved'));await h.run('load()');
  let finish;
  h.state.handler=request=>request.path==='commits'?new Promise(resolve=>{finish=()=>{h.state.context.proposals[0].status='committed';h.state.context.results=[committedResult()];resolve(reply({result:committedResult(),replayed:false}));};}):undefined;
  const first=h.run('commit()');
  assert.equal(h.elements.commit.disabled,true);
  await h.run('commit()');
  assert.equal(h.state.requests.filter(r=>r.path==='commits').length,1);
  finish();await first;
  assert.equal(h.value('current.status'),'committed');
});

test('unsaved reviewer text cannot approve the old proposal; edit creates a pending version before approval',async()=>{
  const h=harness(sampleContext('pending'));await h.run('load()');
  h.elements.edit.value='Revised summary';await h.run('updateControls()');
  assert.equal(h.elements.approve.disabled,true);
  await h.run("review('approve')");
  assert.equal(h.out().error,'UNSAVED_EDITS');
  assert.equal(h.state.requests.filter(r=>r.path==='reviews').length,0);
  h.state.handler=request=>{
    if(request.path!=='reviews')return;
    const proposal=h.state.context.proposals[0];
    if(request.body.decision==='edit'){
      proposal.version=2;proposal.action_hash='c'.repeat(64);
      const action=JSON.parse(proposal.action);action.summary=request.body.edits;proposal.action=JSON.stringify(action);
    }else{
      assert.equal(request.body.version,2);assert.equal(request.body.action_hash,'c'.repeat(64));
      assert.equal(Object.hasOwn(request.body,'edits'),false);proposal.status='approved';
    }
    return reply({review_id:'review-1',proposal});
  };
  await h.run("review('edit')");
  assert.equal(h.value('current.version'),2);assert.equal(h.value('current.status'),'pending');
  assert.equal(h.elements.approve.disabled,false);
  assert.equal(h.elements.commit.disabled,true);
  await h.run("review('approve')");
  assert.equal(h.value('current.status'),'approved');
});

test('HTTP 200 with a failed inference shows failure and does not reuse the previous proposal',async()=>{
  const h=harness(sampleContext('pending'));await h.run('load()');
  h.state.handler=request=>request.path==='proposals'?reply({demo:true,run_id:'failed-run',outcome:'failed',error:'PROVIDER_TIMEOUT',reason:null}):undefined;
  await h.run('propose()');
  assert.equal(h.out().outcome,'failed');
  assert.equal(h.value('current'),null);
  assert.equal(h.elements.status.className,'warning');
  assert.equal(h.elements.approve.disabled,true);
});

test('known commit success survives a failed follow-up refresh with a visible warning',async()=>{
  const h=harness(sampleContext('approved'));await h.run('load()');
  h.state.handler=request=>{
    if(request.path==='commits')return reply({result:committedResult(),replayed:false});
    if(request.path==='context')throw new Error('refresh unavailable');
  };
  await h.run('commit()');
  assert.equal(h.value('current.status'),'committed');
  assert.equal(h.out().result.id,'result-1');
  assert.equal(h.elements.status.className,'warning');
  assert.equal(h.value('pendingCommit'),null);
});

test('changing the demo session clears previous context, draft, proposal and retry state',async()=>{
  const h=harness(sampleContext('approved'));await h.run('load()');
  h.elements.document.value='private draft';h.elements.token.value='demo-viewer-token';
  await h.run('resetSession()');
  assert.equal(h.value('ctx'),null);assert.equal(h.value('current'),null);
  assert.equal(h.value('key'),null);assert.equal(h.value('pendingCommit'),null);
  assert.equal(h.elements.document.value,'');assert.equal(h.elements.edit.value,'');
  assert.equal(h.elements.propose.disabled,true);
  assert.equal(h.elements.context.textContent,'ยังไม่ได้โหลด');
});
