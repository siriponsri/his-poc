import {useEffect,useRef,useState} from 'react'
import * as THREE from 'three'
import {OrbitControls} from 'three/addons/controls/OrbitControls.js'
import type {AssistantProfileId,OperationsMap,OperationsZone} from '../lib/assistant-types'
import {executionLabels,scopedCount} from '../lib/assistant-client'
import {hospitalStations,resolveHospitalPick,supportsHospitalWebGL,type HospitalPick} from '../lib/hospital-layout'
import {useLang} from '../lib/i18n'

type Props={data:OperationsMap;disabled:boolean;onSelectZone:(zone:OperationsZone)=>void;onSelectRun:(id:string,profile:AssistantProfileId)=>void}
export default function HospitalScene({data,disabled,onSelectZone,onSelectRun}:Props){
 const {t}=useLang();const host=useRef<HTMLDivElement>(null),reset=useRef<(()=>void)|null>(null),pose=useRef<{camera:number[];target:number[]}|null>(null),[unavailable,setUnavailable]=useState(!supportsHospitalWebGL())
 const latest=useRef({data,disabled,onSelectZone,onSelectRun});latest.current={data,disabled,onSelectZone,onSelectRun}
 const sceneDataKey=JSON.stringify([data.zones,data.agents])
 useEffect(()=>{
  if(!host.current||!supportsHospitalWebGL())return
  const element=host.current;let renderer:THREE.WebGLRenderer
  try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false})}catch{setUnavailable(true);return}
  setUnavailable(false);renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer.setClearColor(0xf5f6f7);renderer.outputColorSpace=THREE.SRGBColorSpace
  const canvas=renderer.domElement;canvas.setAttribute('aria-label','Illustrative hospital operations. Use the department and preparation lists below for keyboard selection.');canvas.setAttribute('role','img');element.append(canvas)
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(32,1,.1,100);camera.position.set(11,12,14)
  const controls=new OrbitControls(camera,canvas);controls.target.set(0,0,-.5);if(pose.current){camera.position.fromArray(pose.current.camera);controls.target.fromArray(pose.current.target)}controls.enableDamping=false;controls.autoRotate=false;controls.minDistance=12;controls.maxDistance=40;controls.maxPolarAngle=Math.PI/2.2;controls.enablePan=true;controls.update()
  scene.add(new THREE.AmbientLight(0xffffff,2.2));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(7,14,8);scene.add(light)
  const targets:THREE.Object3D[]=[];const textures:THREE.Texture[]=[]
  function box(w:number,h:number,d:number,x:number,y:number,z:number,color:number){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:1}));mesh.position.set(x,y,z);scene.add(mesh);return mesh}
  function label(text:string,x:number,y:number,z:number,width=3.8){const c=document.createElement('canvas');c.width=640;c.height=120;const ctx=c.getContext('2d');if(!ctx)return;ctx.fillStyle='#303841';let fontSize=52;do{ctx.font='500 '+fontSize+'px Manrope, Anuphan, sans-serif';if(ctx.measureText(text).width<610)break;fontSize-=2}while(fontSize>26);ctx.textAlign='center';ctx.fillText(text,320,67);const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;textures.push(texture);const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}));sprite.position.set(x,y,z);sprite.scale.set(width,1,1);scene.add(sprite)}
  box(16.8,.25,11.8,0,-.25,-.5,0xe1e4e8);box(15.8,.06,1.1,0,-.07,-.5,0xffffff)
  for(const station of hospitalStations){const zone=data.zones.find(item=>item.id===station.id);const available=!!zone?.available;const floor=box(4.6,.12,3.9,station.x,0,station.z,available?station.color:0xe9ebed);floor.userData.pick={kind:'zone',id:station.id};targets.push(floor)
   box(4.6,1,.12,station.x,.5,station.z-1.95,0xd5dae0);box(.12,1,3.9,station.x-2.3,.5,station.z,0xd5dae0)
   const desk=box(2,.6,.7,station.x,.4,station.z-.65,available?0xffffff:0xdde0e3);desk.userData.pick={kind:'zone',id:station.id};targets.push(desk)
   const monitor=box(.65,.44,.08,station.x,.98,station.z-.75,available?0x687a97:0xabb0b8);monitor.userData.pick={kind:'zone',id:station.id};targets.push(monitor);box(.08,.2,.08,station.x,.7,station.z-.75,0x8f99a6)
   box(.65,.45,.65,station.x,.24,station.z+.45,0xc9ced5)
   label(zone?.label||station.name,station.x,2.15,station.z,4.4)
   label(zone?.available?scopedCount(zone.open_task_count,true)+' open · '+scopedCount(zone.awaiting_review_count,true)+' review':'Unavailable',station.x,1.55,station.z,4.3)
  }
  data.agents.forEach((agent,index)=>{const zoneId=agent.profile==='laboratory_handoff'?'laboratory':agent.profile==='nursing_handover'?'nursing':agent.profile==='records_readiness'?'records':'ai_workspace';const station=hospitalStations.find(item=>item.id===zoneId)!;const offset=(index%3-1)*.85;const color=agent.execution_state==='running'?0x1c4286:agent.review_state==='pending'?0x861c42:0x87919e
   const marker=new THREE.Mesh(new THREE.OctahedronGeometry(.27),new THREE.MeshStandardMaterial({color,roughness:.85}));marker.position.set(station.x+offset,1.12,station.z+.7);marker.userData.pick={kind:'agent',index};scene.add(marker);targets.push(marker);if(agent.run_id)label(executionLabels[agent.execution_state]||agent.execution_state,station.x+offset,.65,station.z+1.18,2.2)
  })
  let frame:number|undefined,disposed=false
  function render(){frame=undefined;if(disposed)return;const width=Math.max(element.clientWidth,1),height=Math.max(element.clientHeight,320);renderer.setSize(width,height,false);camera.aspect=width/height;camera.fov=camera.aspect<1.4?60:32;camera.updateProjectionMatrix();renderer.render(scene,camera)}
  function requestRender(){if(frame===undefined&&!disposed)frame=window.requestAnimationFrame(render)}
  reset.current=()=>{camera.position.set(11,12,14);controls.target.set(0,0,-.5);controls.update();requestRender()}
  controls.addEventListener('change',requestRender);const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(requestRender):null;observer?.observe(element);window.addEventListener('resize',requestRender)
  const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let down={x:0,y:0}
  function pointerDown(event:PointerEvent){down={x:event.clientX,y:event.clientY}}
  function pointerUp(event:PointerEvent){if(event.button!==0||!event.isPrimary||Math.hypot(event.clientX-down.x,event.clientY-down.y)>5||latest.current.disabled)return;const rect=canvas.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);const picked=raycaster.intersectObjects(targets,false)[0]?.object.userData.pick as HospitalPick|undefined;if(!picked)return;const resolved=resolveHospitalPick(latest.current.data,picked);if(resolved?.kind==='zone')latest.current.onSelectZone(resolved.zone);else if(resolved?.kind==='agent'&&resolved.agent.run_id)latest.current.onSelectRun(resolved.agent.run_id,resolved.agent.profile)}
  function contextLost(event:Event){event.preventDefault();setUnavailable(true)}
  canvas.addEventListener('pointerdown',pointerDown);canvas.addEventListener('pointerup',pointerUp);canvas.addEventListener('webglcontextlost',contextLost);requestRender()
  return()=>{pose.current={camera:camera.position.toArray(),target:controls.target.toArray()};disposed=true;if(frame!==undefined)window.cancelAnimationFrame(frame);observer?.disconnect();window.removeEventListener('resize',requestRender);canvas.removeEventListener('pointerdown',pointerDown);canvas.removeEventListener('pointerup',pointerUp);canvas.removeEventListener('webglcontextlost',contextLost);controls.removeEventListener('change',requestRender);controls.dispose();scene.traverse(object=>{if(object instanceof THREE.Mesh){object.geometry.dispose();const materials=Array.isArray(object.material)?object.material:[object.material];materials.forEach(material=>material.dispose())}else if(object instanceof THREE.Sprite)object.material.dispose()});textures.forEach(texture=>texture.dispose());renderer.dispose();renderer.forceContextLoss();canvas.remove();reset.current=null}
 },[sceneDataKey])
 return <div className="care-map-frame">{unavailable&&<p className="care-map-fallback" role="status">{t('3D ไม่พร้อมในเบราว์เซอร์นี้ ใช้รายการ Departments และ Preparation desk ด้านล่างได้ครบ','3D is unavailable in this browser. All department and preparation actions are available in the lists below.')}</p>}<div className="care-map-canvas" ref={host} hidden={unavailable}/>{!unavailable&&<button className="secondary care-map-reset" onClick={()=>reset.current?.()}>{t('มุมมองเริ่มต้น','Reset view')}</button>}</div>
}
