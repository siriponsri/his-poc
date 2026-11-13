// Icons authored for this project: 24px grid, 1.75 stroke, round joins. No third-party icon code copied.
import type {ReactNode} from 'react'
const paths:Record<string,ReactNode>={
 home:<><path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/></>,
 list:<><path d="M9 6h11M9 12h11M9 18h11"/><path d="m4 6 1 1 1.5-2M4 12l1 1 1.5-2M4 18l1 1 1.5-2"/></>,
 history:<><path d="M4 12a8 8 0 1 0 2.6-5.9"/><path d="M4 4v3.5h3.5M12 8v4.2l2.8 1.8"/></>,
 search:<><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></>,
 menu:<><path d="M4 7h16M4 12h16M4 17h16"/></>,
 chevron:<><path d="m9 6 6 6-6 6"/></>,
 check:<><circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.7 2.7L16 9.5"/></>,
 missing:<><circle cx="12" cy="12" r="9"/><path d="M8 12h8"/></>,
 unclear:<><circle cx="12" cy="12" r="9"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.6 2.2c-.8.5-1.2 1-1.2 1.9M12 16.6v.1"/></>,
 alert:<><path d="M12 4 3 19.5h18z"/><path d="M12 10v4.5M12 17.2v.1"/></>,
 info:<><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.1"/></>,
 clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/></>,
 user:<><circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c.6-3.6 3.4-5.5 7-5.5s6.4 1.9 7 5.5"/></>,
 refresh:<><path d="M20 12a8 8 0 0 1-13.8 5.5M4 12a8 8 0 0 1 13.8-5.5"/><path d="M18 3v4h-4M6 21v-4h4"/></>,
 document:<><path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M14 3v4h4M9 12h6M9 16h6"/></>,
 spark:<><path d="M12 3.5 13.8 10l6.7 2-6.7 2L12 20.5 10.2 14 3.5 12l6.7-2z"/></>,
 shield:<><path d="M12 3.5 5 6v5.5c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.8 7-9V6z"/><path d="m9 12 2.2 2.2L15.2 10"/></>,
 logout:<><path d="M14 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 8l-4 4 4 4M6 12h9"/></>,
 inbox:<><path d="M4 13 6.5 5h11L20 13v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/><path d="M4 13h4.5l1 2.5h5l1-2.5H20"/></>,
 close:<><path d="m6 6 12 12M18 6 6 18"/></>,
}
export type IconName=keyof typeof paths
export function Icon({name,size=20}:{name:string;size?:number}){
 return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[name]||paths.info}</svg>
}
