#!/usr/bin/env python

from math import sqrt

class GeoImage(object):
    '''Image properties with X,Y,Z position and heading. All distances in centimeters.'''
    def __init__(self, file_name, image_time=0, position=(0,0,0), heading_degrees=0, provided_resolution=0, 
                  focal_length=0, camera_rotation_degrees=0, camera_height=0, sensor_width=0, size=(0,0)):
        '''Constructor.'''
        self.file_name = file_name
        self.image_time = image_time
        self.position = position
        self.heading_degrees = heading_degrees
        self.provided_resolution = provided_resolution # resolution (cm/pix) that user specified. 
        self.focal_length = focal_length
        self.camera_rotation_degrees = camera_rotation_degrees # 0 degrees camera top forward. Increase CCW.
        self.camera_height = camera_height
        self.size = size # Image (width,height) in pixels.
        self.sensor_width = sensor_width
        
    @property
    def resolution(self):
        '''Return centimeter/pixel resolution.'''
        if self.provided_resolution > 0:
            return self.provided_resolution # User resolution overrides calculated resolution.
        if self.focal_length <= 0 or self.size[0] <= 0:
            return 0 #  Avoid division by zero or negative results
        hfov = self.camera_height * (self.sensor_width / self.focal_length)
        return hfov / self.size[0]  # cm per pixel

class Row(object):
    '''Collection of items in field row.'''
    def __init__(self, start_code=None, end_code=None, items=None):
        self.start_code = start_code
        self.end_code = end_code
        self.items = items
        if self.items is None:
            self.items = []
    
    @property
    def number(self):
        '''Return row number of -1 if not set.'''
        try:
            row_number = int(self.start_code.name)
        except (ValueError, TypeError):
            row_number = -1
        return row_number
            
class FieldItem(object):
    '''Item found within image'''
    def __init__(self, item_type, name, position=(0,0,0), size=(0,0), row=0, range_grid=0,
                  image_path='', parent_image='', bounding_rect=None, classification='auto'):
        '''Constructor.'''
        self.item_type = item_type
        self.name = name 
        self.position = position
        self.size = size
        self.row = row 
        self.range = range_grid
        self.image_path = image_path
        self.parent_image = parent_image
        self.bounding_rect = bounding_rect
        self.classification = classification
        self.other_items = [] # same field item from different images
        
class Plant(FieldItem):
    '''Plant found within image'''
    def __init__(self, item_type, name, position=(0,0,0), size=(0,0), row=0, range_grid=0,
                  image_path='', parent_image='', bounding_rect=None, classification='auto', number=0):
        '''Constructor.'''
        super(Plant, self).__init__(item_type, name, position, size, row, range_grid, image_path, parent_image, bounding_rect, classification)
        self.number = number
        self.group = None
        
class PlantGroup(object):
    '''Plant grouping. Entry number and repetition. '''
    def __init__(self, start_code=None, plants=None):
        '''Constructor.'''
        self.start_code = start_code
        self.plants = plants
        if self.plants is None:
            self.plants = []
            
    @property
    def name(self):
        return self.start_code.name
    @property
    def entry(self):
        return self.start_code.name[:-1]
    @property
    def rep(self):
        return self.start_code.name[-1]

def position_difference(position1, position2):
    '''Return difference in XY positions between both items.'''
    delta_x = position1[0] - position2[0]
    delta_y = position1[1] - position2[1]
    return sqrt(delta_x*delta_x + delta_y*delta_y)
        
def is_same_item(item1, item2, max_position_difference):
    '''Return true if both items are similar enough to be considered the same.'''
    if item1.item_type != item2.item_type:
        return False
    
    if item1.parent_image == item2.parent_image:
        return False # Come from same image so can't be different.
    
    if 'code' in item1.item_type: 
        if item1.name == item2.name:
            return True # Same QR code (which are unique) so must be same item. 

    # convert max difference from cm to meters
    max_position_difference /= 100.0
    
    if position_difference(item1.position, item2.position) > max_position_difference:
        return False # Too far apart
    
    return True # Similar enough
    