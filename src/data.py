#!/usr/bin/env python

from math import sqrt

class GeoImage(object):
    '''Image properties with X,Y,Z position and heading. All distances in centimeters.'''
    def __init__(self, file_name, image_time=0, position=(0,0,0), heading_degrees=0, focal_length=0,
                  camera_rotation_degrees=0, camera_height=0, sensor_width=0, size=(0,0)):
        '''Constructor.'''
        self.file_name = file_name
        self.image_time = image_time
        self.position = position
        self.heading_degrees = heading_degrees 
        self.focal_length = focal_length
        self.camera_rotation_degrees = camera_rotation_degrees # 0 degrees camera top forward. Increase CCW.
        self.camera_height = camera_height
        self.size = size # Image (width,height) in pixels.
        self.sensor_width = sensor_width
        
    @property
    def resolution(self):
        '''Return centimeter/pixel resolution.'''
        if self.focal_length <= 0 or self.size[0] <= 0:
            return 0 #  Avoid division by zero or negative results
        hfov = self.camera_height * (self.sensor_width / self.focal_length)
        return hfov / self.size[0]  # cm per pixel
        
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
    def __init__(self, entry, rep, start_qr=None, plants=[]):
        '''Constructor.'''
        self.entry = entry
        self.rep = rep
        self.start_qr = start_qr
        self.plants = plants
        
def is_same_item(item1, item2, max_position_difference):
    '''returns true if both items are similar enough to be considered the same.'''
    if item1.item_type != item2.item_type:
        return False
    
    if item1.parent_image == item2.parent_image:
        return False # Come from same image so can't be different.
    
    delta_x = item1.position[0] - item2.position[0]
    delta_y = item1.position[1] - item2.position[1]
    position_difference = sqrt(delta_x*delta_x + delta_y*delta_y)
    
    if position_difference > max_position_difference:
        return False # Too far apart
    
    return True # Similar enough
    