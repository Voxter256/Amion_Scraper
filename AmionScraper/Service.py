from sqlalchemy import Column, Integer, String, Boolean

from .Base import Base, Session

session = Session()


class Service(Base):

    __tablename__ = 'services'

    id = Column(Integer(), primary_key=True)
    name = Column(String(64), index=True)
    hospital_group = Column(Integer())
    is_call = Column(Boolean())
    has_call = Column(Boolean())
    has_post_call = Column(Boolean())
    vacation_allowed = Column(Boolean())
    required_number_residents = Column(Integer())
