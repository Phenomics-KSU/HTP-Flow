#!/usr/bin/env python

class GeoImage(object):
    '''Image properties with X,Y,Z position and heading. All distances in centimeters.'''
    def __init__(self, file_name, position=(0,0,0), heading=0, focal_length=0, camera_height=0,
                   sensor_width=0, image_width_in_pixels=0):
        '''Constructor.'''
        self.file_name = file_name
        self.position = position
        self.heading = heading
        self.focal_length = focal_length
        self.camera_height = camera_height
        self.image_width_in_pixels = image_width_in_pixels
        self.sensor_width = sensor_width
        
    @property
    def resolution(self):
        '''Return centimeter/pixel resolution.'''
        if self.focal_length <= 0 or self.image_width_in_pixels <= 0:
            return 0 #  Avoid division by zero or negative results
        hfov = self.camera_height * (self.sensor_width / self.focal_length)
        return hfov / self.image_width_in_pixels  # cm per pixel
        
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
        