from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# ✅ Fix for Neon PostgreSQL — requires SSL + connection pooling settings
DATABASE_URL = settings.DATABASE_URL

# Neon requires sslmode=require — add it if not already in URL
if "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},  # ✅ Required for Neon on Render
    pool_pre_ping=True,                   # ✅ Reconnects if connection dropped
    pool_recycle=300,                     # ✅ Recycle connections every 5 min
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
