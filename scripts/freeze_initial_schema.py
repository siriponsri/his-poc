"""Development-only schema snapshot. Do not run against an already released revision."""
from pathlib import Path
from sqlalchemy.schema import CreateTable,CreateIndex,AddConstraint
from backend.app.db import Base,engine
from backend.app import model_registry
statements=[]
for table in Base.metadata.sorted_tables:
    statements.append(str(CreateTable(table).compile(dialect=engine.dialect)))
    for index in sorted(table.indexes,key=lambda i:i.name):statements.append(str(CreateIndex(index).compile(dialect=engine.dialect)))
for table in Base.metadata.tables.values():
    for constraint in table.foreign_key_constraints:
        if constraint.use_alter:statements.append(str(AddConstraint(constraint).compile(dialect=engine.dialect)))
Path('backend/migrations/schema_0001.py').write_text('# Frozen initial migration DDL; future edits require a new Alembic revision.\nDDL = '+repr(statements)+'\n')
print('Frozen',len(Base.metadata.tables),'tables')
