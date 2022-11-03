from sqlalchemy import Column, String

from model.atlas_model import Base


class User(Base):
    __tablename__ = 'auth_user'
    id = Column(String, nullable=False, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)