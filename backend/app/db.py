"""PostgreSQL persistence. Startup does not create, migrate or seed a schema."""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={'ix':'ix_%(column_0_label)s','uq':'uq_%(table_name)s_%(column_0_N_name)s','ck':'ck_%(table_name)s_%(constraint_name)s','fk':'fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s','pk':'pk_%(table_name)s'})

url = os.environ.get('DATABASE_URL', 'postgresql+psycopg://his:unconfigured@127.0.0.1:5432/his')
if not url.startswith(('postgresql://','postgresql+psycopg://')):
    raise RuntimeError('DATABASE_URL must use PostgreSQL; SQLite fallback is prohibited')
if url.startswith('postgresql://'): url = url.replace('postgresql://','postgresql+psycopg://',1)
engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout':5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
