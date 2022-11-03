from datetime import datetime

from model.elastix_transformation import ElastixTransformation
from controller.main_controller import Controller

class ElastixController(Controller):
    """Controller class for the elastix table

    Args:
        Controller (Class): Parent class of sqalchemy session
    """
    def __init__(self,*args,**kwargs):
        """initiates the controller class
        """        
        Controller.__init__(self,*args,**kwargs)

    def check_elastix_row(self, animal, section):
        """checks that a given elastix row exists in the database

        Args:
            animal (str): Animal ID
            section (int): Section Number

        Returns:
            bool: if the row in question exists
        """        
        row_exists = bool(self.session.query(ElastixTransformation).filter(
            ElastixTransformation.prep_id == animal,
            ElastixTransformation.section == section).first())
        return row_exists

    def check_elastix_metric_row(self, animal, section):
        """checks that a given elastix row exists in the database

        Args:
            animal (str): Animal ID
            section (int): Section Number

        Returns:
            bool: if the row in question exists
        """        
        row_exists = bool(self.session.query(ElastixTransformation).filter(
            ElastixTransformation.prep_id == animal,
            ElastixTransformation.section == section,
            ElastixTransformation.metric != 0).first())
        return row_exists
    
    def delete_elastix_row(self, animal, section):
        """checks that a given elastix row exists in the database

        Args:
            animal (str): Animal ID
            section (int): Section Number

        Returns:
            bool: if the row in question exists
        """        
        search_dictionary = {'prep_id':animal,'section':section}
        self.delete_row(search_dictionary, ElastixTransformation)
    
    def add_elastix_row(self, animal, section, rotation, xshift, yshift):
        """adding a row in the elastix table

        Args:
            animal (str): Animal ID
            section (_type_): _description_
            rotation (_type_): _description_
            xshift (_type_): _description_
            yshift (_type_): _description_
        """        
        data = ElastixTransformation(
            prep_id=animal, section=section, rotation=rotation, xshift=xshift, yshift=yshift,
            created=datetime.utcnow(), active=True)
        self.add_row(data)

    def clear_elastix(self, animal):
        """delelte an elastix row

        Args:
            animal (str): Animal ID
        """    
        self.session.query(ElastixTransformation).filter(ElastixTransformation.prep_id == animal)\
            .delete()


    def update_elastix_row(self, animal, section, updates):
        row = self.session.query(ElastixTransformation)\
            .filter(ElastixTransformation.prep_id == animal)\
            .filter(ElastixTransformation.section == section).update(updates)
        self.session.commit()
