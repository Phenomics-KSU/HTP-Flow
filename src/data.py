#!/usr/bin/env python

class GeoImage(object):
    '''Image with X,Y,Z position and heading.'''
    def __init__(self, file_name, x, y, z, heading):
        '''Constructor.'''
        self.file_name = file_name
        self.x = x
        self.y = y
        self.z = z
        self.heading = heading
        
class FieldItem(object):
    '''Item found within image'''
    def __init__(self, item_type, name, x, y, z, row, range_grid, image_path, parent_image, classification):
        '''Constructor.'''
        self.item_type = item_type
        self.name = name 
        self.x = x
        self.y = y
        self.z = z
        self.row = row 
        self.range = range_grid
        self.image_path = image_path
        self.parent_image = parent_image
        self.classification = classification
        
class Plant(FieldItem):
    '''Plant found within image'''
    def __init__(self, item_type, name, x, y, z, row, range_grid, image_path, parent_image, classification, number):
        '''Constructor.'''
        super(FieldItem, item_type, name, x, y, z, row, range_grid, image_path, parent_image, classification)
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
        