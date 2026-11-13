"""Export actual application contracts and relational dictionary; does not connect/write DB."""
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy.schema import CreateTable,CreateIndex
from sqlalchemy.dialects import postgresql
from backend.app.main import app
from backend.app.db import Base
ROOT=Path(__file__).resolve().parents[1]
def main():
 target=ROOT/'contracts/v2';target.mkdir(parents=True,exist_ok=True)
 from backend.app.document_completeness import CHECKLIST_ID, CHECKLIST, PROMPT_VERSION, output_schema
 (target/'document-completeness.json').write_text(json.dumps({'checklist_id':CHECKLIST_ID,'prompt_version':PROMPT_VERSION,'checklist':[{'key':k,'label':v} for k,v in CHECKLIST],'model_output_schema':output_schema(),'scope':'authored synthetic documentation completeness only; source quotes and human review required'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 from backend.app.domains.clinical import domain_schemas
 (target/'clinical-inputs.json').write_text(json.dumps(domain_schemas(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 from backend.app.domains.erp import CREATES,ACTIONS
 erp_schemas={domain:{'create':model.model_json_schema(),'action':ACTIONS[domain].model_json_schema()} for domain,model in CREATES.items()}
 (target/'erp-inputs.json').write_text(json.dumps(erp_schemas,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 schema=app.openapi()
 (target/'openapi.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 tables=sorted(Base.metadata.tables.values(),key=lambda t:t.name)
 ddl=[]
 for table in tables:
  ddl.append(str(CreateTable(table).compile(dialect=postgresql.dialect()))+';')
  ddl.extend(str(CreateIndex(i).compile(dialect=postgresql.dialect()))+';' for i in sorted(table.indexes,key=lambda x:x.name or ''))
 (target/'schema-reference.sql').write_text('-- REFERENCE ONLY: apply Alembic migrations, not this export.\n'+'\n\n'.join(ddl)+'\n',encoding='utf-8')
 with (ROOT/'docs/DATA_DICTIONARY.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['table','column','postgresql_type','nullable','primary_key','foreign_keys','constraints'])
  for t in tables:
   cs='; '.join(sorted(str(c.sqltext) for c in t.constraints if c.__class__.__name__=='CheckConstraint'))
   for c in t.columns:
    w.writerow([t.name,c.name,str(c.type.compile(dialect=postgresql.dialect())),c.nullable,c.primary_key,';'.join(sorted(x.target_fullname for x in c.foreign_keys)),cs])
 print(json.dumps({'tables':len(tables),'paths':len(schema['paths']),'schemas':len(schema.get('components',{}).get('schemas',{}))}))
if __name__=='__main__':main()
