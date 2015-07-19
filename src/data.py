#!/usr/bin/env python

from math import sqrt

class GeoImage(object):
    '''Image properties with X,Y,Z position and heading. All distances in centimeters.'''
    def __init__(self, file_name, image_time=0, position=(0,0,0), heading_degrees=0, provided_resolution=0, 
                  focal_length=0, camera_rotation_degrees=0, camera_height=0, sensor_width=0, size=(0,0)):
        '''Constructor.'''
        self.file_name = file_name # name of image file with extension (not full path).
        self.image_time = image_time # UTC time when image was taken.
        self.position = position # 3D position of camera in either local ENU frame or UTM when the image was taken.
        self.heading_degrees = heading_degrees # heading of image with 0 degrees being East and increasing CCW.
        self.provided_resolution = provided_resolution # resolution (cm/pix) that user specified.  If set then overrides focal length, sensor width and camera height.
        self.focal_length = focal_length # focal length of lens in centimeters
        self.camera_rotation_degrees = camera_rotation_degrees # 0 degrees camera top forward. Increase CCW.
        self.camera_height = camera_height # height of camera above ground in centimeters.
        self.size = size # image (width,height) in pixels.
        self.sensor_width = sensor_width # width of camera sensor in centimeters
        #self.items = items # list of items located within image. KLM removed. Just use parent filename reference from field items.
        # 3D positions of image corners.
        self.top_left_position = (0,0,0) 
        self.top_right_position = (0,0,0) 
        self.bottom_right_position = (0,0,0)
        self.bottom_left_position = (0,0,0)
        
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
    def __init__(self, start_code=None, end_code=None, direction=None, segments=None):
        # Start and end codes are defined to be in the direction of the entire field... not the individual row.
        self.start_code = start_code # QR code on the side of the field where range = 0
        self.end_code = end_code # QR code on the other side of the field.
        self.direction = direction # Either 'up' if the in same direction as field or 'back' if row runs opposite direction.
        self.group_segments = segments # Segments in row in order from start code -> end code.  
        if self.group_segments is None:
            self.group_segments = []
    
    @property
    def number(self):
        '''Return row number using start QR code.'''
        return self.start_code.row_number

class FieldItem(object):
    '''Item found within image'''
    def __init__(self, name, position=(0,0,0), field_position=(0,0,0), size=(0,0), area=0, row=0, range_grid=0,
                  image_path='', parent_image_filename='', bounding_rect=None, number_within_field=0, number_within_row=0):
        '''Constructor.'''
        self.name = name # identifier 
        self.position = position # 3D position of item in either local ENU frame or UTM
        self.field_position = field_position # 3D position relative to first field item. axes are in direction of row, range, altitude.
        self.size = size # Width and height of item in centimeters.
        self.area = area # Area of item in cm^2
        self.row = row # The row the item is found in. First row is #1.  If zero or negative then doesn't belong to a row.
        self.range = range_grid # The range the item is found in.  If row is the 'x' value then the range is the 'y' value and the units are dimensionless.
        self.image_path = image_path # Full path where cropped out image of field item is found.
        self.parent_image_filename = parent_image_filename  # Filename of image where field item was found. Don't store ref since we'll run out of memory.
        self.bounding_rect = bounding_rect # OpenCV minimum rotated bounding rectangle containing item. Units in pixels. No pad added in.
        self.number_within_field = number_within_field # Number of item within entire field.  
        self.number_within_row = number_within_row # Number of item within current row.  Measured from range = 0 side of field.
        self.other_items = [] # same field item from different images.
        
    @property
    def type(self):
        '''Return type of item (ie plant, QR code, gap, etc). No need for subclass to override this, it will return name of child class already.'''
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
        self.entry = 'none'
        self.rep = 'none'
    
    @property
    def id(self):
        return self.name

class RowCode(FieldItem):
    '''Code found within image corresponding to a row start/end. Name should be 'row#' where # is the row number.'''
    def __init__(self, *args, **kwargs):
        '''Constructor.'''
        super(RowCode, self).__init__(*args, **kwargs)
        self.row_number = int(self.name[2:])
        
class PlantGroupSegment(object):
    '''Part of a plant grouping. Hit end of row before entire grouping could be planted.'''
    def __init__(self, start_code, end_code, items=None):
        '''Constructor.'''
        self.items = items # items found in segment not counting start or end QR code.
        if self.items is None:
            self.items = []
        self.group = None # group that segment belongs to.
        self.start_code = start_code # QR code to start segment. Could either be Row or Group Code depending on if segment is starting or ending.
        self.end_code = end_code # QR code that ends segment. Could either be Row or Group Code depending on if segment is starting or ending.
    
    def update_group(self, new_group):
        '''Update the grouping that this segment belongs to and update the reference of all the items stored in the segment.'''
        self.group = new_group
        for code in [self.start_code] + self.start_code.other_items:
            code.group = new_group
    
    def add_item(self, item):
        '''Add item to list of items and updates item reference. Raise ValueError if item is None.'''
        if item is None:
            raise ValueError('Cannot add None item to item group.')
        self.items.append(item)
        for new_item in [item] + item.other_items:
            new_item.group = self.group
            
    def length(self):
        '''Return distance between start and end code in centimeters.'''
        if self.start_code is None or self.end_code is None:
            return 0
        delta_x = self.start_code.position[0] - self.end_code.position[0]
        delta_y = self.start_code.position[1] - self.end_code.position[1]
        return sqrt(delta_x*delta_x + delta_y*delta_y)
        
class PlantGroup(object):
    '''Complete plant grouping made of 1 or more segments that span multiple rows.'''
    def __init__(self):
        '''Constructor.'''
        self.segments = []

    def add_segment(self, segment):
        segment.update_group(self)
        self.segments.append(segment)

    @property
    def start_code(self):
        return self.segments[0].start_code
    @property
    def id(self):
        return self.start_code.id
    @property
    def entry(self):
        return self.start_code.entry
    @property
    def rep(self):
        return self.start_code.rep
    @property
    def length(self):
        '''Return distance of all segments in centimeters.'''
        length = 0
        for segment in self.segments:
            length += segment.length
        return length
