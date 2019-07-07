from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship, backref

from AmionScraper.Base import Base, Session

session = Session()


class BlockedDays(Base):

    __tablename__ = 'blocked_days'

    id = Column(Integer(), primary_key=True)
    summary = Column(String())
    calendar_id = Column(String(), index=True)
    start_date = Column(DateTime(), index=True)
    end_date = Column(DateTime(), index=True)
    service_id = Column(Integer(), ForeignKey('services.id'), index=True)
    created_at = Column(DateTime())
    updated_at = Column(DateTime())

    service = relationship("Service", uselist=False, backref=backref('blocked_days'))
