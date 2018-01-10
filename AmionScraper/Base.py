import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

postgres_url = os.environ['DATABASE_URL']
engine = create_engine(postgres_url)  # echo=True) for debug
Session = sessionmaker(bind=engine)
Base = declarative_base()

