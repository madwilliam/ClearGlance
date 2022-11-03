'''
Put file doc info here
'''
import string
import random
from unicodedata import category
from attr import has
import numpy as np
from django.http.response import Http404

default_annotation_layer = dict(type = 'annotation',annotations = [],name = 'annotation',source = '')

class AnnotationLayer:
    '''
    Class mapping to different annotation types in neuroglancer
    '''

    def __init__(self, annotation_layer=default_annotation_layer):
        """Initiates the AnnotationLayer object with the neuroglancer json state of one layer
        Args:
            annotation_layer (dict, optional): The neuroglancer json state of one annotation layer. Defaults to default_annotation_layer.
        Raises:
            Http404: django http404 response
        """        
        try:
            assert annotation_layer['type'] == 'annotation'
        except:
            raise Http404
        self.annotations = annotation_layer['annotations']
        self.name = annotation_layer['name']
        if 'tool' in annotation_layer:
            self.tool = annotation_layer['tool']
        self.source = annotation_layer['source']
        self._type = 'annotation'
        self.parse_annotations()

    def __str__(self):
            return "str method: annotation_layer is %s, b is %s" % (self.annotation_layer)
    
    def parse_annotations(self):
        '''
        This is the main function that parses the annotation in the neuroglancer json state to custom
        object mappings in python.  This step groups points into polygons and polygons into volumes 
        '''
        annotations = []
        for annotationi in self.annotations:
            if annotationi['type'] == 'polygon':
                annotations.append(self.parse_polygon(annotationi))
            elif annotationi['type'] == 'volume':
                annotations.append(self.parse_volume(annotationi))
            elif annotationi['type'] == 'point':
                annotations.append(self.parse_point(annotationi))
            elif annotationi['type'] == 'cell':
                annotations.append(self.parse_point(annotationi,point_class='Cell'))
            elif annotationi['type'] == 'com':
                annotations.append(self.parse_point(annotationi,point_class='COM'))
            elif annotationi['type'] == 'line':
                annotations.append(self.parse_line(annotationi))
        self.annotations = np.array(annotations)
        self.group_annotations('polygon')
        # self.reorder_polygon_points()
        # self.check_polygon_points()
        self.group_annotations('volume')
    
    def parse_point(self, point_json,point_class ='Point'):
        '''
        Parse the neuroglancer json of a point annotation
        :param point_json: dictionary of neuroglancer point annotation json state
        '''
        point = eval(f'{point_class}(point_json["point"], point_json["id"])')
        if 'description' in point_json:
            point.description = point_json['description']
        if 'category' in point_json:
            point.category = point_json['category']
        if point.category =='':
            point.category = 'Null'
        return point
    
    def parse_line(self, line_json):
        '''
        Parse the neuroglancer json of a line annotation
        :param line_json:dictionary of neuroglancer line annotation json state
        '''
        line = Line(line_json['pointA'], line_json['pointB'], line_json['id'])
        if 'parentAnnotationId' in line_json:
            line.parent_id = line_json['parentAnnotationId']
        if 'description' in line_json:
            line.description = line_json['description']
        return line

    def parse_polygon(self, polygon_json):
        '''
        Parse the neuroglancer json of a polygon annotation
        :param polygon_json: dictionary of neuroglancer polygon annotation json state
        '''
        polygon = Polygon(polygon_json['id'], polygon_json['childAnnotationIds'], polygon_json['source'])
        if 'description' in polygon_json:
            polygon.description = polygon_json['description']
        if 'parentAnnotationId' in polygon_json:
            polygon.parent_id = polygon_json['parentAnnotationId']
        return polygon
    
    def parse_volume(self, volume_json):
        '''
        Parse the neuroglancer json of a volume annotation
        :param volume_json: dictionary of neuroglancer polygon annotation json state
        '''
        volume = Volume(volume_json['id'], volume_json['childAnnotationIds'], volume_json['source'])
        if 'description' in volume_json:
            volume.description = volume_json['description']
        return volume

    def search_annotation_with_id(self, id):
        '''
        search in the annnotation in the layer for one with a set id 
        :param id: UUID annotation id set by neuroglancer
        '''
        search_result = [annotationi.id == id for annotationi in self.annotations]
        if sum(search_result) == 0:
            print('annotation not found')
        elif sum(search_result) > 1:
            print('more than one result found')
        return search_result
    
    def group_annotations(self, _type):
        '''
        The main function to group points into polygons and polygons into volumes
        :param _type: string to determing if we are grouping points to polygons are polygons to volumes
        '''
        for annotationi in self.annotations:
            if annotationi._type == _type:
                annotationi.childs = []
                for childid in annotationi.child_ids:
                    annotationi.childs.append(self.get_annotation_with_id(childid))
                    self.delete_annotation_with_id(childid)
                annotationi.childs = np.array(annotationi.childs)
    
    def reorder_polygon_points(self):
        '''
        Reorder the polygon points by tracing out the start and end of each line segment.  Requires that 
        all the points in the polygons are unique
        '''
        for annotationi in self.annotations:
            if annotationi._type == 'polygon':
                start_points = np.array([pointi.coord_start for pointi in annotationi.childs])
                end_points = np.array([pointi.coord_end for pointi in annotationi.childs])
                sorter = ContourSorter(start_points=start_points, end_points=end_points, first_point=annotationi.source)
                annotationi.childs = np.array(annotationi.childs)[sorter.sort_index]
                annotationi.child_ids = annotationi.child_ids[sorter.sort_index]

    def check_polygon_points(self):
        '''
        Check the the ordering of the annotation points makes sense.  Traces all the polygons from start to finish and checks 
        that you return to the starting point
        '''
        for annotationi in self.annotations:
            if annotationi._type == 'polygon':
                start_points = np.array([pointi.coord_start for pointi in annotationi.childs])
                end_points = np.array([pointi.coord_end for pointi in annotationi.childs])
                first_point=annotationi.source
                check_if_contour_points_are_in_order(first_point,start_points,end_points)

    def get_annotation_with_id(self, id):
        '''
        returns the annotation object with a set id
        :param id: UUID string assigned by neuroglancer
        '''
        search_result = self.search_annotation_with_id(id)
        if sum(search_result) == 0:
            return None
        else:
            return self.annotations[search_result][0]
    
    def delete_annotation_with_id(self, id):
        '''
        Delete annoatation with a set id from the list of annotations
        :param id:UUID string assigned by neuroglancer
        '''
        search_result = self.search_annotation_with_id(id)
        self.annotations = self.annotations[np.logical_not(search_result)]
    
    def get_volumes(self):
        """return all the volumes int this layer
        Returns:
            list: list of volume annotations
        """        
        return [i for i in self.annotations if i._type == 'volume']

    def get_polygons(self):
        """get list of all polygon
        Returns:
            list: list of all polygon annotations
        """        
        return [i for i in self.annotations if i._type == 'polygons']
        
    def to_json(self):
        '''
        convert an annotation to it's json form.  To be implemented
        '''
        point_json = {}
        ...

class Annotation:
    """generic annotation type, serves as the base type for all annotations
    """    
    def is_point(self):
        """checks if an annotation is a point
        Returns:
            bool: if annotaion is point
        """        
        return self._type == 'point'
    def is_polygon(self):
        """checks if an annotation is a polygon
        Returns:
            bool: if annotation is a polygon
        """        
        return self._type == 'polygon'
    def is_volume(self):
        """checks if an annotation is a volume
        Returns:
            bool: if annotation is volume
        """        
        return self._type == 'volume'
    def is_line(self):
        """checks if an annotation is a line
        Returns:
            bool: if annotation is line
        """        
        return self._type == 'line'
    def get_description(self):
        """get the description of the 
        Returns:
            str: the description field of the annotation point
        """        
        if hasattr(self,'description'):
            return self.description
        else:
            return None
    def is_com(self):
        return self._type == 'com'

    def is_cell(self):
        return self._type == 'cell'


class Point(Annotation):
    '''
    Point Annotation
    '''

    def __init__(self, coord, id):
        """initialize the point annotation
        Args:
            coord (list): list of x,y,z coordinates
            id (str): UUID for point annotations
        """        
        self.coord = np.array(coord)
        self.id = id
        self._type = 'point'
    
    def to_json(self):
        """convert the point annotation to neuroglancer json state 
        """        
        if hasattr(self,'description'):
            point_json = create_point_annotation(list(self.coord),self.description,type = self._type)
        else:
            point_json = create_point_annotation(list(self.coord),'',type = self._type)
        if hasattr(self,'category'):
            point_json['category'] = self.category
        return point_json

class COM(Point):
    def __init__(self, coord, id):
        super().__init__(coord,id)
        self._type = 'com'

class Cell(Point):
    def __init__(self, coord, id):
        super().__init__(coord,id)
        self._type = 'cell'
        self.category = 'Null'
        self.description = 'Null'

class Line(Annotation):
    '''
    Line Annotation
    '''

    def __init__(self, coord_start, coord_end, id):
        """Initializes the line annotation
        Args:
            coord_start (list): list of x,y,z, coordinate of the starting point
            coord_end (list): list of x,y,z coordinate of the ending point
            id (str): UUID of the annotation
        """        
        self.coord_start = np.array(coord_start)
        self.coord_end = np.array(coord_end)
        self.id = id
        self._type = 'line'
        
    def __str__(self):
        return "Line ID is %s, start is %s, end is %s" % (self.id, self.coord_start, self.coord_start)

    def to_json(self):
        """Turns the line annotation to neuroglancer json
        """        
        ...


class Polygon(Annotation):
    '''
    Polygon Annotation
    '''

    def __init__(self, id, child_ids, source):
        """Initilaizes the polygon
        Args:
            id (str): UUID of the polygon annotation
            child_ids (list): list of child annotations
            source (list): list of x,y,z, coordinates of the source field for the polygon annotation
        """        
        self.source = source
        self.id = id
        self.child_ids = np.array(child_ids)
        self._type = 'polygon'
        
    def __str__(self):
        return "Polygon ID is %s, source is %s" % (self.id, self.source)
    
    def to_json(self):
        """converts the polygon annotation to neuroglancer json
        """        
        ...
    
    def to_numpy(self):
        """convert the points in the polygon to a np array
        Returns:
            _type_: _description_
        """        
        return np.array([i.coord_start for i in self.childs])
    
    def get_section_direction(self,points):
        """find the direction where the sections are made.  That direction would be whichever x,y,z direction that 
        always have the same orientation
        Args:
            points (list): list of x,y,z coordinates
        Returns:
            int: integer of sectioning direction 0,1,2 corresponding to x,y,z
        """        
        xs,ys,zs = points[:,0],points[:,1],points[:,2]
        uniquexs,uniqueys,uniquezs =len(np.unique(xs)),len(np.unique(ys)),len(np.unique(zs))
        section_direction = np.where(np.array([uniquexs,uniqueys,uniquezs])==1)
        assert len(section_direction) == 1
        return section_direction[0]
    
    def get_section_and_2d_contours(self):
        """Get the 2d contours indexed by section number
        Returns:
            dict: dictionary of 2d contours indexed by section number
        """        
        points = self.to_numpy()
        section_direction = self.get_section_direction(points)
        contours2d = points[:,[i for i in range(3) if i != section_direction]]
        section = np.unique(points[:,section_direction])[0]
        section = int(np.floor(section))
        return section,contours2d

class Volume(Annotation):
    '''
    Volume Annotation
    '''

    def __init__(self, id, child_ids, source):
        """Initialize the volume annotation
        Args:
            id (str): UUID of volume annotatin
            child_ids (list): list of id for child annotations
            source (list): list of x,y,z values for the source field
        """        
        self.source = source
        self.id = id
        self.child_ids = np.array(child_ids)
        self._type = 'volume'
        
    def __str__(self):
        return "Polygon ID is %s, source is %s" % (self.id, self.source)
    
    def get_volume_name_and_contours(self,downsample_factor = 1):
        """Get the name of volume and dictionary of contours
        Returns:
            str,dict: The name of the volume in question and the dictionary containing the contour points
        """        
        assert hasattr(self,'description')
        volume_contours = {}
        for childi in self.childs:
            section,contours = childi.get_section_and_2d_contours()
            volume_contours[section] = contours/downsample_factor
        # assert len(self.childs) == len(volume_contours.keys())
        return self.description,volume_contours
    
    def to_dict(self):
        """Convert the volume annotation to dictionaries
        """        
        ...

class ContourSorter:
    '''
    Class for sorting the contour points in a polygon
    This is depricated now that neuroglancer is able to handle point ordering
    '''

    def __init__(self, start_points, end_points, first_point):
        '''
        starting the contour sorter with the starting and ending points
        :param start_points:    list of x,y,z, coordinates of the starting points   
        :param end_points: list of x,y,z, coordinates of the ending points
        :param first_point:  The coordinate of the first point
        '''
        self.first_point = np.array(first_point)
        self.start_points = np.array(start_points)
        self.end_points = np.array(end_points)
        self.check_input_dimensions()
        self.npoints = len(self.start_points)
        self.sort_index = []
        first_point_index = self.find_index_of_point_in_array(first_point, self.start_points)
        self.sort_index.append(first_point_index)
        self.sort_points()

    def check_input_dimensions(self):
        """checking that the input dimensions are correct
        """        
        if not self.start_points.shape[1] == 3:
            self.start_points = self.start_points.T
        if not self.end_points.shape[1] == 3:
            self.end_points = self.end_points.T
        assert len(self.start_points) == len(self.end_points)
        assert len(self.start_points[0]) == len(self.end_points[0]) == len(self.first_point) == 3

    def find_index_of_point_in_array(self, point, array):
        '''
        Finding the index of the point in the array according to x,y,z, coordinates
        :param point: x,y,z coordinates
        :param array: array of which we are searching
        '''
        result = np.where(np.all(array == point, axis=1))[0]
        assert len(result) == 1
        return result[0]

    def sort_points(self):
        '''
        Main function that sorts the orders of points
        '''
        while len(self.sort_index) < self.npoints:
            last_point_index = self.sort_index[-1]
            next_point_index = self.find_index_of_next_point(last_point_index)
            self.sort_index.append(next_point_index)
        check_if_contour_points_are_in_order(self.first_point, self.start_points[self.sort_index], self.end_points[self.sort_index])

    def find_index_of_next_point(self, last_point_index):
        '''
        Find the index of the point next to the current point
        :param last_point_index:index of the last point
        '''
        last_end_point = self.end_points[last_point_index]
        next_start_index = self.find_index_of_point_in_array(last_end_point, self.start_points)
        return next_start_index

    
def check_if_contour_points_are_in_order(first_point, start_points, end_points):
    '''
    This function is run at the end of sorting to make sure that polygon points are sorted correctly.
    It follows the start and end points from the first point to see if the polygon returns to the original spot and is continuous at every step
    :param first_point: first point in the polygon  
    :param start_points: sorted starting points 
    :param end_points: sorted ending points
    '''
    assert len(start_points) == len(end_points)
    assert len(start_points[0]) == len(end_points[0]) == len(first_point) == 3
    assert np.all(first_point == start_points[0])
    npoints = len(start_points)
    for i in range(npoints - 1):
        assert np.all(np.isclose(start_points[i + 1], end_points[i],atol=0.1))

def random_string() -> str:
    '''
    Creates a 40 char string of random characters
    '''
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=40))

def create_point_annotation(coordinates,description=None,category = None,type = 'point'):
    """create annotation points in the neuroglancer json format
    Args:
        coordinates (list): list of coordinates: x,y,z for this annotation point
        description (str): the description field of this annotation point.  This would be displayed in neuroglancer 
    Returns:
        _type_: _description_
    """    
    point_annotation = {}
    point_annotation['id'] = random_string()
    point_annotation['point'] = list(coordinates)
    point_annotation['type'] = type
    if description is not None:
        point_annotation['description'] = description
    if category is not None:
        point_annotation['category'] = category
    return point_annotation