from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref

from .Base import Base, Session

session = Session()


class Physician(Base):

    __tablename__ = 'physicians'

    id = Column(Integer(), primary_key=True)
    name = Column(String(32), index=True)
    position_id = Column(Integer(), ForeignKey('positions.id'), index=True)
    email = Column(String(64), index=True, unique=True)

    position = relationship("Position", uselist=False, backref=backref('physicians'))
