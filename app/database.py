from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
url=settings.DATABASE_URL
if url.startswith('postgres://'): url=url.replace('postgres://','postgresql://',1)
args={'check_same_thread':False} if url.startswith('sqlite') else {}
engine=create_engine(url,connect_args=args,pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
Base=declarative_base()
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
