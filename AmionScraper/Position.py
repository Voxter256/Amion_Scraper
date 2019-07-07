from sqlalchemy import Column, Integer, String

from AmionScraper.Base import Base, Session

session = Session()


class Position(Base):

    __tablename__ = 'positions'

    id = Column(Integer(), primary_key=True)
    name = Column(String(32), index=True)
