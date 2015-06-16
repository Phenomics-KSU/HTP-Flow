#!/usr/bin/env python

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
        return self.start_code.row_number

class FieldItem(object):
    '''Item found within image'''
    def __init__(self, name, position=(0,0,0), size=(0,0), row=0, range_grid=0,
                  image_path='', parent_image='', bounding_rect=None, 
                  number_within_field=0, number_within_row=0):
        '''Constructor.'''
        self.name = name # identifier 
        self.position = position
        self.size = size
        self.row = row
        self.range = range_grid
        self.image_path = image_path
        self.parent_image = parent_image
        self.bounding_rect = bounding_rect
        self.number_within_field = number_within_field
        self.number_within_row = number_within_row
        self.other_items = [] # same field item from different images
        
    @property
    def type(self):
        return self.__class__.__name__
        
class GroupItem(FieldItem):
    '''Field item that belongs to grouping.'''
    def __init__(self, *args, **kwargs):
        '''Constructor.'''
        super(GroupItem, self).__init__(*args, **kwargs)
        self.group = None
        
    @property
    def number_within_group(self):
        '''Return index number within grouping or -1 if not in a group.'''
        try:
            return self.group.items.index(self)
        except (AttributeError, ValueError):
            return -1
    
class Plant(GroupItem):
    '''Plant found within image'''
    def __init__(self, *args, **kwargs):
        '''Constructor.'''
        super(Plant, self).__init__(*args, **kwargs)
        
class Gap(GroupItem):
    '''Gap detected within grouping.'''
    def __init__(self, *args, **kwargs):
        '''Constructor.'''
        super(Gap, self).__init__(*args, **kwargs)
        
class GroupCode(GroupItem):
    '''Code found within image corresponding to plant grouping. Name should be entry followed by single character rep ie 1234a.'''
    def __init__(self, *args, **kwargs):
        '''Constructor.'''
        super(GroupCode, self).__init__(*args, **kwargs)
    
    @property
    def entry(self):
        return self.name[:-1]
    @property
    def rep(self):
        return self.name[-1]
    
class RowCode(FieldItem):
    '''Code found within image corresponding to a row start/end. Name should be 'row#' where # is the row number.'''
    def __init__(self, *args, **kwargs):
        '''Constructor.'''
        super(RowCode, self).__init__(*args, **kwargs)
        self.row_number = int(self.name[3:])
        
class PlantGroup(object):
    '''Plant grouping. Entry number and repetition. '''
    def __init__(self, start_code=None, items=None):
        '''Constructor.'''
        self.start_code = start_code
        self.items = items
        if self.items is None:
            self.items = []
    
    @property
    def name(self):
        return self.start_code.name
    @property
    def entry(self):
        return self.start_code.entry
    @property
    def rep(self):
        return self.start_code.rep
    
    def add_item(self, item):
        '''Add item to list of items and updates item reference. Raise ValueError if item is None.'''
        if item is None:
            raise ValueError('Cannot add None item to item group.')
        self.items.append(item)
        item.group = self
    