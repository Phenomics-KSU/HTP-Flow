#! /usr/bin/env python

import sys
import os
import argparse
import math
import bisect

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
        print 'No filename containing {}'.format(keyword_id)
        return None
    elif len(matched_filenames) > 1:
        print 'More than one file containing ID {}\n{}'.format(keyword_id, matched_filenames)
        return None
    
    return matched_filenames[0]

def find_less_than_or_equal(a, x):
    '''
    Return rightmost index in list a where the value at a[i] is less than or equal to x.
    If x is greater than all elements in a then len(a)-1 is returned.
    If x is smaller than all elements in a then -1 is returned.
    '''
    i = bisect.bisect_right(a, x)
    return i - 1

def geotag(reading_time, reading_data, reading_position, reading_orientation, offsets):
    # Use heading to split body offsets into inertial x,y,z offsets
    x, y, z = reading_position
    angle1, angle2, angle3 = reading_orientation
    x_body, y_body, z_body = offsets
    
    x_offset = x_body * math.cos(angle3) - y_body * math.sin(angle3)
    y_offset = x_body * math.sin(angle3) + y_body * math.cos(angle3)
    z_offset = z_body
    
    # Add on offsets to position.
    x += x_offset
    y += y_offset
    z += z_offset
    
    return GeoReading(reading_time, reading_data, (x, y, z), (angle1, angle2, angle3))

def geotag_all_readings_closest(readings, offsets, position_times, positions, orientation_times, orientations):
    
    geotagged_readings = []
    for reading in readings:
        reading_time = reading[0]
        reading_data = reading[1:]
        reading_position, reading_orientation = closests_pose_by_time(reading_time, reading_data, position_times, positions, orientation_times, orientations)
        geotagged_reading = geotag(reading_time, reading_data, reading_position, reading_orientation, offsets)
        geotagged_readings.append(geotagged_reading)

    return geotagged_readings

def closests_pose_by_time(reading_time, reading_data, position_times, positions, orientation_times, orientations):
    ''''''
    position = closests_value(reading_time, position_times, positions)
    orientation = closests_value(reading_time, orientation_times, orientations)
    
    return position, orientation

def closests_value(x_value, x_set, y_set, i1=None):
    '''
    Return y corresponding to x_value such that it matches with the closest value in x_set. 
    If i1 isn't None then it's treated as the rightmost index in x_set where x_set[i1] is less than or equal to x_value.
    Returns None on failure.
    '''
    if len(x_set) != len(y_set):
        return None
    
    if i1 is None:
        # index of element in x_set right before or equal to x_value
        i1 = find_less_than_or_equal(x_set, x_value)  
    
    if i1 < 0:
        # specified x value occurs before any x's so return first y
        return y_set[0]
    
    if i1 >= (len(x_set) - 1):
        # specified x value occurs after all x's so return last y
        return y_set[-1]
    
    # i2 is the index of the element in x_set right after x_value.
    i2 = i1 + 1
    
    # Find the magnitude difference between specified x value and 2 closest values in x set.
    i1_mag = abs(x_set[i1] - x_value)
    i2_mag = abs(x_set[i2] - x_value)
    
    closest_index = i1 if (i1_mag < i2_mag) else i2
    
    return y_set[closest_index]

def geotag_all_readings_interpolate(readings, offsets, position_times, positions, orientation_times, orientations):

    x_list = [position[0] for position in positions]
    y_list = [position[1] for position in positions]
    z_list = [position[2] for position in positions]
    positions_by_axes = [x_list, y_list, z_list]

    angle1_list = [orientation[0] for orientation in orientations]
    angle2_list = [orientation[1] for orientation in orientations]
    angle3_list = [orientation[2] for orientation in orientations]
    orientations_by_axes = [angle1_list, angle2_list, angle3_list]
    
    geotagged_readings = []
    for reading in readings:
        reading_time = reading[0]
        reading_data = reading[1:]
        reading_position, reading_orientation = interpolate_pose(reading_time, reading_data, position_times, positions_by_axes, orientation_times, orientations_by_axes)
        geotagged_reading = geotag(reading_time, reading_data, reading_position, reading_orientation, offsets)
        geotagged_readings.append(geotagged_reading)

    return geotagged_readings

def interpolate_pose(reading_time, reading_data, position_times, positions_by_axes, orientation_times, orientations_by_axes):
    ''''''
    print "Interpolation not currently supported for orientation. Exiting"
    sys.exit(1)
    time_index = find_less_than_or_equal(position_times, reading_time)  
    x = interpolate(reading_time, position_times, positions_by_axes[0], i1=time_index)
    y = interpolate(reading_time, position_times, positions_by_axes[1], i1=time_index)
    z = interpolate(reading_time, position_times, positions_by_axes[2], i1=time_index)

    orientation_index = find_less_than_or_equal(orientation_times, reading_time)
    angle1 = interpolate(reading_time, orientation_times, orientations_by_axes[0], i1=orientation_index)
    angle2 = interpolate(reading_time, orientation_times, orientations_by_axes[1], i1=orientation_index)
    angle3 = interpolate(reading_time, orientation_times, orientations_by_axes[2], i1=orientation_index)
    
    return ((x,y,z), (angle1,angle2,angle3))

def interpolate(x_value, x_set, y_set, i1=None):
    '''
    Return y value corresponding to x value.  If outside bounds of x_set then returns closest value.
    x_set and y_set must have the same amounts of elements. If i1 isn't None then it's treated as the
    rightmost index in x_set where x_set[i1] is less than or equal to x_value.  Returns None on failure.
       '''
    if len(x_set) != len(y_set):
        return None
    
    if i1 is None:
        # index of element in x_set right before or equal to x_value
        i1 = find_less_than_or_equal(x_set, x_value)  
    
    if i1 < 0:
        # specified x value occurs before any x's so return first y
        return y_set[0]
    
    if i1 >= (len(x_set) - 1):
        # specified x value occurs after all x's so return last y
        return y_set[-1]
    
    if x_value == x_set[i1]:
        # don't need to interpolate since match exactly.
        return y_set[i] 
    
    # i2 is the index of the element in x_set right after x_value.
    # at this point x_set[i1] can't be equal to x_set[i2] or else
    # i2 would have been returned instead of i1 above.
    i2 = i1 + 1
    
    slope = (y_set[i2] - y_set[i1]) / (x_set[i2] - x_set[i1])
    
    return y_set[i1] + slope * (x_value - x_set[i1])

if __name__ == '__main__':
    '''Create geotag file for each sensor reading file.'''
    # Any reference to keyword ID is a short (unique) part of a filename.  
    # For example in the filename irt235 a keyword ID could be irt if no other irt files exist in the same directory. 
    match_options = ['closest', 'interpolate']
    default_position_id = 'position'
    default_orientation_id = 'orientation'
    parser = argparse.ArgumentParser(description='Create geotag file for each sensor file.')
    parser.add_argument('input_directory', help='Where to search for files to process')
    parser.add_argument('match_type', help='How to match up sensor readings to position/orientations. Options are {}'.format(match_options))
    parser.add_argument('-p', dest='position', default=default_position_id, help='File name identifier for input position file. Default {}'.format(default_position_id))
    parser.add_argument('-o', dest='orientation', default=default_orientation_id, help='File name identifier for input orientation file. Default {}'.format(default_orientation_id))
    parser.add_argument('-s', dest='sensors', default='', help='File name identifier for sensor file followed by offset from position file.  Positive body offsets are x forward, y left, z up.  Multiple sensors are separated by commas. For example \'sensor1 .5 .1 0, sensor2 .5 -.1 0 \'')
    args = parser.parse_args()
    
    # Convert command line arguments
    input_directory = args.input_directory
    match_type = args.match_type.lower()
    position_id = args.position
    orientation_id = args.orientation
    sensors = args.sensors
    
    if match_type not in match_options:
        print "Invalid match type.  Options are {}".format(match_options)
        sys.exit(1)

    output_directory = os.path.join(input_directory, 'geotagged')
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
            print 'Bad sensor info. Need exactly 4 elements: {}'.format(sensor)
            continue
        sensor_id = sensor[0]
        sensor_filename = match_id_to_filename(filenames, sensor_id)
        if sensor_filename is None:
            continue
        sensor[0] = sensor_filename
        
    # Read in positions.
    positions = []
    print 'Reading in positions from {}'.format(position_filename)
    position_filepath = os.path.join(input_directory, position_filename)
    with open(position_filepath) as position_file:
        positions = [line.replace(',',' ').split() for line in position_file.readlines()]
        positions = [[float(i) for i in position[:4]] for position in positions]
    print 'Read {} positions'.format(len(positions))
    
    print "Sorting positions by time."
    positions = sorted(positions, key=lambda p: p[0])
    
    # Split off time from position now that it's sorted.
    position_times = [p[0] for p in positions]
    positions = [p[1:] for p in positions]
           
    # Read in orientation.
    orientations = []
    print 'Reading in orientation from {}'.format(orientation_filename)
    orientation_filepath = os.path.join(input_directory, orientation_filename)
    with open(orientation_filepath) as orientation_file:
        orientations = [line.replace(',',' ').split() for line in orientation_file.readlines()]
        orientations = [[float(i) for i in orientation] for orientation in orientations]
    print 'Read {} orientations'.format(len(orientations))
    
    print "Sorting orientations by time."
    orientations = sorted(orientations, key=lambda o: o[0])
    
    # Split off time from orientation now that it's sorted.
    orientation_times = [o[0] for o in orientations]
    orientations = [o[1:] for o in orientations]
    
    # Read in sensor data and create corresponding geo-referenced file.
    for sensor in sensors:
        sensor_filename = sensor[0]
        offsets = [float(offset) for offset in sensor[1:4]] # offsets from position reading
        
        print 'Reading in sensor data from {}'.format(sensor_filename)
        sensor_filepath = os.path.join(input_directory, sensor_filename)
        with open(sensor_filepath) as sensor_file:
            sensor_data = [line.replace(',',' ').split() for line in sensor_file.readlines()]
            for data in sensor_data:
                # Convert time to float.
                data[0] = float(data[0])

        if match_type == 'closest':
            geo_readings = geotag_all_readings_closest(sensor_data, offsets, position_times, positions, orientation_times, orientations)
        elif match_type == 'interpolate':
            geo_readings = geotag_all_readings_interpolate(sensor_data, offsets, position_times, positions, orientation_times, orientations)
        else:
            print "Invalid type {}.".format(match_type)
            continue
        
        just_sensor_filename, sensor_extension = os.path.splitext(sensor_filename)
        geo_filename = "{}_geo{}".format(just_sensor_filename, sensor_extension)
        geo_filepath = os.path.join(output_directory, geo_filename)
        with open(geo_filepath, 'w') as geo_file:
            for reading in geo_readings:
                geo_file.write('{},'.format(reading.time))
                for element in reading.data:
                    geo_file.write('{},'.format(element))
                for element in reading.position:
                    geo_file.write('{},'.format(element))
                for element in reading.orientation:
                    geo_file.write('{},'.format(element))
                geo_file.write('\n')

        print 'Created output file {}'.format(geo_filepath)
