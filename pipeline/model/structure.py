from sqlalchemy import Column, String, Integer
from model.atlas_model import Base, AtlasModel



class Structure(Base, AtlasModel):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'structure'
    id =  Column(Integer, primary_key=True, nullable=False)
    abbreviation = Column(String, nullable=False)
    description = Column(String, nullable=False)
    color = Column(Integer, nullable=False)
    hexadecimal = Column(String, nullable=False)
    is_structure = Column(Integer, nullable=False)




