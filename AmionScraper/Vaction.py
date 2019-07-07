from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

from AmionScraper.Base import Base, Session

session = Session()


class Vacation(Base):

    __tablename__ = 'vacations'

    id = Column(Integer(), primary_key=True)
    start_date = Column(DateTime(), index=True)
    end_date = Column(DateTime(), index=True)
    physician_id = Column(Integer(), ForeignKey('physicians.id'), index=True)
    calendar_id = Column(String(), index=True)
    created_at = Column(DateTime())
    updated_at = Column(DateTime())

    physician = relationship("Physician", uselist=False, backref=backref('vacations'))
