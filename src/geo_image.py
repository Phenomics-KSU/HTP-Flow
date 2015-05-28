#!/usr/bin/env python

class GeoImage : object
    '''Image with X,Y,Z position and heading.'''
    
    def __init__(self, file_name, x, y, z, heading):
        '''Constructor.'''
        self.file_name = file_name
        self.x = x
        self.y = y
        self.z = z
        self.heading = heading
        
