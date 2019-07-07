from sqlalchemy import Column, Integer, String

from AmionScraper.Base import Base, Session

session = Session()


class Authentication(Base):

    __tablename__ = 'authentication'

    id = Column(Integer(), primary_key=True)
    data = Column(String(2048))
    developerKey = Column(String(2048))
    calendarId = Column(String(2048))
