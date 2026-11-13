export type Field={name:string;label:string;type?:string;required?:boolean;options?:({value:string;label:string}|string)[];source?:string;default?:string|number|boolean;min?:number;step?:string;order_kind?:string}
export type ActionDef={name:string;label:string;from?:string[];fields?:Field[];path?:string;target?:string;omitVersion?:boolean;method?:string}
export type Resource={id:string;label:string;path:string;fields:Field[];actions:ActionDef[];patient_context?:boolean;encounter_context?:boolean;description?:string;detailPath?:string|false}
export type DomainDef={id:string;name_th:string;domain_group:string;resources:Resource[]}
export const field=(name:string,label:string,type='text',required=true):Field=>({name,label,type,required})
