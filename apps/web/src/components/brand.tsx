/** Original linked-record mark from the owner-selected Operations Desk proposal. */
export function BrandMark(){return <svg className="brand-mark" viewBox="0 0 25 25" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M4 17V9a5 5 0 0 1 10 0v8M10 8v8a5 5 0 0 0 10 0V8"/></svg>}
export function Brand({caption,onClick}:{caption?:string;onClick?:()=>void}){
 return <a className="brand" href={onClick?'/home':'/'} aria-label="CareBalance home" onClick={onClick?event=>{event.preventDefault();onClick()}:undefined}><BrandMark/><span>CareBalance{caption&&<small>{caption}</small>}</span></a>
}
