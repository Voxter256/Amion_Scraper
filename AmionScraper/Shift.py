from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

from .Base import Base, Session

session = Session()


class Shift(Base):

    __tablename__ = 'shifts'

    id = Column(Integer(), primary_key=True)
    shift_date = Column(DateTime(), index=True)
    service_id = Column(Integer(), ForeignKey('services.id'), index=True)
    physician_id = Column(Integer(), ForeignKey('physicians.id'), index=True)

    service = relationship("Service", uselist=False, backref=backref('shifts'))
    physician = relationship("Physician", uselist=False, backref=backref('shifts'))
