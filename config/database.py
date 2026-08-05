from sqlalchemy import create_engine

DATABASE_URL = "postgresql://postgres:phuc12a2k44@localhost:5432/fintech_db"
engine = create_engine(DATABASE_URL)