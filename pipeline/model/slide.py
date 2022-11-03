from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Enum
from model.atlas_model import Base, AtlasModel

class SlideCziTif(Base, AtlasModel):
    __tablename__ = 'slide_czi_to_tif'
    __table_args__ = {'extend_existing': True}
    id =  Column(Integer, primary_key=True, nullable=False)
    FK_slide_id = Column(Integer, ForeignKey('slide.id'), nullable=False)
    file_name = Column(String, nullable=False)
    scene_number = Column(Integer, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Float)
    comments = Column(String)
    channel = Column(Integer)
    scene_index = Column(Integer)
    processing_duration = Column(Float, nullable=False)

class Slide(Base, AtlasModel):
    __tablename__ = 'slide'
    __table_args__ = {'extend_existing': True}
    id =  Column(Integer, primary_key=True, nullable=False)
    scan_run_id = Column(Integer, ForeignKey('scan_run.id'))
    slide_physical_id = Column(Integer)
    rescan_number = Column(Enum("1", "2", "3"), default="1", nullable=False)
    slide_status = Column(Enum("Bad", "Good"), nullable=False)
    scenes = Column(Integer, nullable=False)
    insert_before_one = Column(Integer, default=0)
    scene_qc_1 =  Column(Integer, default=0)
    insert_between_one_two =  Column(Integer, default=0)
    scene_qc_2 =  Column(Integer, default=0)
    insert_between_two_three = Column(Integer, default=0)
    scene_qc_3 =  Column(Integer, default=0)
    insert_between_three_four =  Column(Integer, default=0)
    scene_qc_4 =  Column(Integer, default=0)
    insert_between_four_five =  Column(Integer, default=0)
    scene_qc_5 = Column(Integer, default=0)
    insert_between_five_six = Column(Integer, default=0)
    scene_qc_6 =  Column(Integer, default=0)
    processed = Column(Boolean(), default=False)
    file_size = Column(Float, nullable=False)
    file_name = Column(String, nullable=False)
    comments = Column(String)
    

class Section(Base, AtlasModel):
    __tablename__ = 'sections'
    __table_args__ = {'extend_existing': True}
    id =  Column(Integer, primary_key=True, nullable=False)
    prep_id = Column(String, ForeignKey('animal.prep_id'), nullable=False)
    czi_file = Column(String, nullable=False)
    slide_physical_id = Column(Integer, nullable=False)
    file_name = Column(String, nullable=False)
    tif_id = Column(Integer, ForeignKey('slide_czi_to_tif.id'), nullable=False)
    scene_number = Column(Integer, nullable=False)
    scene_index = Column(Integer, nullable=False)
    channel = Column(Integer, nullable=False)
    channel_index = Column(Integer, nullable=False)
    FK_slide_id = Column(Integer, ForeignKey('slide.id'), nullable=False)
    def get_rotation(self):
        return getattr(self.slide,f'scene_rotation_{self.scene_number}')

