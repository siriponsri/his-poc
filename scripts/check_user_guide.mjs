// Validate authored guide coverage and exact screenshot provenance; no application requests.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import {GUIDE_CHAPTERS,GUIDE_DOMAINS} from '../apps/web/src/data/user-guide-content.ts'
import {GUIDE_MEDIA} from '../apps/web/src/data/user-guide-media.ts'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const canonical=JSON.parse(readFileSync(path.join(root,'apps/web/src/data/full-domains.json'),'utf8'))
assert.equal(GUIDE_DOMAINS.length,38)
assert.equal(new Set(GUIDE_DOMAINS.map(item=>item.id)).size,38)
for(const item of canonical){const entry=GUIDE_DOMAINS.find(row=>row.id===item.id);assert.ok(entry,item.id);assert.equal(entry.name,item.name_th);assert.ok(entry.roles.length&&entry.steps.length&&entry.completion&&entry.limits)}
assert.equal(new Set(GUIDE_CHAPTERS.map(item=>item.id)).size,GUIDE_CHAPTERS.length)
const used=new Set()
for(const chapter of GUIDE_CHAPTERS){
 assert.ok(chapter.title&&chapter.summary&&chapter.roles.length&&chapter.prerequisites.length&&chapter.steps.length&&chapter.completion.length&&chapter.troubleshooting.length,chapter.id)
 assert.ok(chapter.domains.every(id=>GUIDE_DOMAINS.some(item=>item.id===id)),chapter.id)
 for(const step of chapter.steps){assert.ok(step.title&&step.paragraphs.length&&step.paragraphs.every(Boolean));if(step.screenshot){assert.ok(GUIDE_MEDIA[step.screenshot],step.screenshot);used.add(step.screenshot)}}
}
const provenance=JSON.parse(readFileSync(path.join(root,'docs/USER_GUIDE_MEDIA.json'),'utf8'))
for(const [id,media] of Object.entries(GUIDE_MEDIA)){
 assert.ok(used.has(id),'Unreferenced media '+id)
 assert.ok(media.alt&&media.caption&&media.width>0&&media.height>0)
 assert.match(media.src,/^\/guide\/[A-Za-z]+\.jpg$/)
 const bytes=readFileSync(path.join(root,'apps/web/public',media.src))
 assert.equal(createHash('sha256').update(bytes).digest('hex'),provenance.screenshots.find(item=>item.id===id)?.sha256)
 for(const step of media.tour||[]){const {x,y,width,height}=step.rect;assert.ok(step.label&&step.description&&[x,y,width,height].every(Number.isFinite)&&x>=0&&y>=0&&width>0&&height>0&&x+width<=100&&y+height<=100,id)}
}
console.log(JSON.stringify({status:'PASS',chapters:GUIDE_CHAPTERS.length,chapter_steps:GUIDE_CHAPTERS.reduce((sum,item)=>sum+item.steps.length,0),domains:GUIDE_DOMAINS.length,domain_steps:GUIDE_DOMAINS.reduce((sum,item)=>sum+item.steps.length,0),screenshots:used.size,animated_walkthroughs:Object.values(GUIDE_MEDIA).filter(item=>item.tour?.length>1).length,application_requests:0}))
