// Locally authored accessible navigation primitives; routes and scope remain server-controlled.
import {createContext,useContext,useState,useEffect,useRef,type ReactNode} from 'react'
const SidebarContext=createContext({open:false,mobile:false,toggle:()=>{},close:()=>{}})
export function SidebarProvider({children}:{children:ReactNode}){
 const [open,setOpen]=useState(false)
 const [mobile,setMobile]=useState(()=>typeof window.matchMedia==='function'&&window.matchMedia('(max-width:1099px)').matches)
 useEffect(()=>{if(typeof window.matchMedia!=='function')return;const mq=window.matchMedia('(max-width:1099px)');const update=()=>{setMobile(mq.matches);if(!mq.matches)setOpen(false)};mq.addEventListener('change',update);return()=>mq.removeEventListener('change',update)},[])
 return <SidebarContext value={{open,mobile,toggle:()=>setOpen(x=>!x),close:()=>setOpen(false)}}><div className={'app-layout '+(open?'sidebar-open':'')}>{children}</div></SidebarContext>
}
export function useSidebar(){return useContext(SidebarContext)}
export function Sidebar({children}:{children:ReactNode}){
 const {close,open,mobile}=useContext(SidebarContext);const ref=useRef<HTMLElement>(null)
 useEffect(()=>{
  if(!mobile||!open)return
  const panel=ref.current
  const controls=()=>Array.from(panel?.querySelectorAll<HTMLElement>('a[href],button:not(:disabled),input:not(:disabled),select:not(:disabled),[tabindex="0"]')||[])
  controls()[0]?.focus()
  const key=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){event.preventDefault();close();setTimeout(()=>document.querySelector<HTMLButtonElement>('[aria-controls=app-navigation]')?.focus(),0)}
   if(event.key==='Tab'){const list=controls();const first=list[0],last=list[list.length-1];if(!first)return;if(event.shiftKey&&(document.activeElement===first||!panel?.contains(document.activeElement))){event.preventDefault();last.focus()}else if(!event.shiftKey&&(document.activeElement===last||!panel?.contains(document.activeElement))){event.preventDefault();first.focus()}}
  }
  document.addEventListener('keydown',key);return()=>document.removeEventListener('keydown',key)
 },[mobile,open,close])
 return <><button className="sidebar-scrim" onClick={close} aria-label="ปิดเมนู" tabIndex={-1}/><aside ref={ref} id="app-navigation" className="sidebar" inert={mobile&&!open} aria-label="เมนูระบบ">{children}</aside></>
}
export function SidebarTrigger(){const {open,toggle}=useContext(SidebarContext);return <button className="icon-button" onClick={toggle} aria-expanded={open} aria-controls="app-navigation" aria-label="เปิดหรือปิดเมนู"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>}
export function SidebarInset({children}:{children:ReactNode}){const {mobile,open}=useSidebar();return <main id="main-content" className="sidebar-inset" tabIndex={-1} inert={mobile&&open}>{children}</main>}
export function SidebarGroup({title,children}:{title:string;children:ReactNode}){return <div className="sidebar-group"><h2>{title}</h2>{children}</div>}
