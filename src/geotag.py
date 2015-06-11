#! /usr/bin/env python

import sys
import os
import argparse
import math

class GeoReading:
    '''Sensor reading with position/orientation information.'''
    def __init__(self, time, data, position, orientation):
        self.time = time
        self.data = data
        self.position = position
        self.orientation = orientation

def match_id_to_filename(filesnames, keyword_id):
    '''Return filename that contains id somewhere in name or extension. Returns None if not exactly one filename found.'''
    matched_filenames = []
    for filename in filenames:
        if keyword_id in filename:
            matched_filenames.append(filename)
            
    if len(matched_filenames) == 0:
        print 'No filename containing {0}'.format(keyword_id)
        return None
    elif len(matched_filenames) > 1:
        print 'More than one file containing ID {0}\n{1}'.format(keyword_id, matched_filenames)
        return None
    
    return matched_filenames[0]

def geotag(reading, offsets, positions, orientations):
    '''Find position/orientation of reading (time, data) using specified sensor offsets in body frame.
        x = positive forward
        y = positive left
        z = positive upwards
    '''
    reading_time = reading[0]
    reading_data = reading[1:]
    
    # Terribly inefficient way to do this but I'm in a hurry so it'll do for right now.
    position_times = [position[0] for position in positions]
    x = interpolate(reading_time, position_times, [position[1] for position in positions])
    y = interpolate(reading_time, position_times, [position[2] for position in positions])
    z = interpolate(reading_time, position_times, [position[3] for position in positions])
    
    orientation_times = [orientation[0] for orientation in orientations]
    angle1 = interpolate(reading_time, orientation_times, [orientation[1] for orientation in orientations])
    angle2 = interpolate(reading_time, orientation_times, [orientation[2] for orientation in orientations])
    angle3 = interpolate(reading_time, orientation_times, [orientation[3] for orientation in orientations])
    
    # Use heading to split body offsets into inertial x,y,z offsets
    x_body, y_body, z_body = offsets
    x_offset = x_body * math.cos(angle3) - y_body * math.sin(angle3)
    y_offset = x_body * math.sin(angle3) + y_body * math.cos(angle3)
    z_offset = z_body
    
    # Add on offsets to interpolated position.
    x += x_offset
    y += y_offset
    z += z_offset
    
    return GeoReading(reading_time, reading_data, (x, y, z), (angle1, angle2, angle3))

def interpolate(x_value, x_set, y_set):
    '''Return y value corresponding to x value.  If outside bounds of x_set then returns closest value.
       x_set and y_set must have the same amounts of elements.  Returns None on failure.'''
    if len(x_set) != len(y_set):
        return None
    
    i1 = None  # index of element in x_set right before x_value
    i2 = None  # index of element in x_set right after x_value
    for i, x in enumerate(x_set):
        if x == x_value:
            return y_set[i] # don't need to interpolate since match exactly.
        if x > x_value:
            i2 = i
            break
        else:
            i1 = i
            
    if i1 is None:
        # specified x value occurs before any x's so return first y
        return y_set[0]
                     
    if i2 is None:
        # specified x value occurs after all x's so return last y
        return y_set[-1]
    
    slope = (y_set[i2] - y_set[i1]) / (x_set[i2] - x_set[i1])
    
    return y_set[i1] + slope * (x_value - x_set[i1])

if __name__ == '__main__':
    '''Create geotag file for each sensor reading file.'''
    # Any reference to keyword ID is a short (unique) part of a filename.  
    # For example in the filename irt235 a keyword ID could be irt if no other irt files exist in the same directory. 
    default_position_id = 'position'
    default_orientation_id = 'orientation'
    parser = argparse.ArgumentParser(description='Create geotag file for each sensor file.')
    parser.add_argument('input_directory', help='Where to search for files to process')
    parser.add_argument('-p', dest='position', default=default_position_id, help='File name identifier for input position file. Default {0}'.format(default_position_id))
    parser.add_argument('-o', dest='orientation', default=default_orientation_id, help='File name identifier for input orientation file. Default {0}'.format(default_orientation_id))
    parser.add_argument('-s', dest='sensors', default='', help='File name identifier for sensor file followed by offset from position file.  Positive body offsets are x forward, y left, z up.  Multiple sensors are separated by commas. For example \'sensor1 .5 .1 0, sensor2 .5 -.1 0 \'')
    args = parser.parse_args()
    
    # Convert command line arguments
    input_directory = args.input_directory
    position_id = args.position
    orientation_id = args.orientation
    sensors = args.sensors

    output_directory = os.path.join(input_directory, 'output')
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Map keyword IDs to files.
    filenames = os.listdir(input_directory)
    
    position_filename = match_id_to_filename(filenames, position_id)
    if position_filename is None:
        sys.exit(1)

    orientation_filename = match_id_to_filename(filenames, orientation_id)
    if orientation_filename is None:
        sys.exit(1)
    
    # Convert sensor info to keywords IDs and offset positions (x,y,z)
    # First determine if sensors is file path or a list.
    if os.path.exists(sensors):
        # Replace sensors variable with file contents to mimic passing in on command line.
        with open(sensors) as sensors_file:
            sensors = sensors_file.read()
    
    # Split sensors up into list of lists (sensor keyword id, x offset, y offset, z offset)
    sensors = sensors.replace('\n',',').replace('\t',',').split(',')
    sensors = [sensor.split() for sensor in sensors]
    
    # Convert sensor keyword IDs to filenames so now we have (sensor filename, x offset, y offset, z offset).
    for sensor in sensors:
        if len(sensor) != 4:
            print 'Bad sensor info. Need exactly 4 elements: {0}'.format(sensor)
            continue
        sensor_id = sensor[0]
        sensor_filename = match_id_to_filename(filenames, sensor_id)
        if sensor_filename is None:
            continue
        sensor[0] = sensor_filename
        
    # Read in positions.
    positions = []
    print 'Reading in positions from {0}'.format(position_filename)
    position_filepath = os.path.join(input_directory, position_filename)
    with open(position_filepath) as position_file:
        positions = [line.replace(',',' ').split() for line in position_file.readlines()]
        positions = [[float(i) for i in position] for position in positions]
    print 'Read {0} positions'.format(len(positions))
           
    # Read in orientation.
    orientations = []
    print 'Reading in orientation from {0}'.format(orientation_filename)
    orientation_filepath = os.path.join(input_directory, orientation_filename)
    with open(orientation_filepath) as orientation_file:
        orientations = [line.replace(',',' ').split() for line in orientation_file.readlines()]
        orientations = [[float(i) for i in orientation] for orientation in orientations]
    print 'Read {0} orientations'.format(len(orientations))
    
    # Read in sensor data and create corresponding geo-referenced file.
    for sensor in sensors:
        sensor_filename = sensor[0]
        offsets = [float(offset) for offset in sensor[1:4]] # offsets from position reading
        
        print 'Reading in sensor data from {0}'.format(sensor_filename)
        sensor_filepath = os.path.join(input_directory, sensor_filename)
        with open(sensor_filepath) as sensor_file:
            sensor_data = [line.replace(',',' ').split() for line in sensor_file.readlines()]
            for data in sensor_data:
                # Convert time to float.
                data[0] = float(data[0])

        geo_readings = [geotag(reading, offsets, positions, orientations) for reading in sensor_data]
        
        geo_filename = "geo_{0}".format(sensor_filename)
        geo_filepath = os.path.join(output_directory, geo_filename)
        with open(geo_filepath, 'w') as geo_file:
            for reading in geo_readings:
                geo_file.write('{0},'.format(reading.time))
                for element in reading.data:
                    geo_file.write('{0},'.format(element))
                for element in reading.position:
                    geo_file.write('{0},'.format(element))
                for element in reading.orientation:
                    geo_file.write('{0},'.format(element))
                geo_file.write('\n')

        print 'Created output file {0}'.format(geo_filepath)
