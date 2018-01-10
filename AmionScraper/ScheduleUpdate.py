from datetime import datetime
from sqlalchemy import Column, Integer, DateTime

from .Base import Base, Session

session = Session()


class ScheduleUpdate(Base):

    __tablename__ = 'schedule_updates'

    id = Column(Integer(), primary_key=True)
    update_date = Column(DateTime(), index=True)
