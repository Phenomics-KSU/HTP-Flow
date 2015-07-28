#! /usr/bin/env python

import sys
import os
import argparse
import pickle
import time
import csv

# non-default import
#import numpy as np

# Project imports
from data import *

if __name__ == '__main__':
    '''.'''

    parser = argparse.ArgumentParser(description='''.''')
    parser.add_argument('input_filepath', help='pickled file from either stage 2.')
    parser.add_argument('output_directory', help='where to write output files')
    
    args = parser.parse_args()
    
    # convert command line arguments
    input_filepath = args.input_filepath
    out_directory = args.output_directory

    # Unpickle rows.
    with open(input_filepath) as input_file:
        rows = pickle.load(input_file)
        print 'Loaded {} rows from {}'.format(len(rows), input_filepath)
    
    if len(rows) == 0:
        print "No rows could be loaded from {}".format(input_filepath)
        sys.exit(1)
    
    rows = sorted(rows, key=lambda r: r.number)
    
    for row in rows:

        for segment in row.group_segments:
            
            # Get East-North unit vector of segment.
            e = segment.end_code.position[0] - segment.start_code.position[0]
            n = segment.end_code.position[1] - segment.start_code.position[1]
            up = segment.end_code.position[2] - segment.start_code.position[2]
            if segment.length == 0:
                print "Skipping segment {} since it has zero length.".format(segment.start_code.name)
                continue
            e /= segment.length
            n /= segment.length
            up /= segment.length # TODO: length is for 2D not 3D

            if segment.expected_num_plants == 0:
                print "Can't place plants for segment {} since it has no estimated num of plants.".format(segment.start_code.name)
                continue
            
            distance_between_plants = segment.length / segment.expected_num_plants
            
            min_distance_between_plants = 0.3
            if distance_between_plants < min_distance_between_plants:
                print "Group {} with length {} and expected num plants {} has a plant spacing of {} which is less than the minimum {}".format(segment.start_code.name, segment.length,
                                                                                                                                              segment.expected_num_plants, distance_between_plants,
                                                                                                                                               min_distance_between_plants)
                continue
            
            # Distance to place next plant.  Start at position for first plant.
            current_distance = distance_between_plants
            
            for i in range(segment.expected_num_plants):
                
                # Place new plant at current distance into segment.
                plant_easting = segment.start_code.position[0] + (current_distance * e)
                plant_northing = segment.start_code.position[1] + (current_distance * n)
                plant_altitude = segment.start_code.position[2] + (current_distance * up)
                plant_position = (plant_easting, plant_northing, plant_altitude)
                
                new_plant = Plant('Plant'+str(i+1), plant_position, row = row.number)
                
                segment.items.append(new_plant)
                
                current_distance += distance_between_plants
                
    # Pickle
    dump_filename = "stage3_rows.txt"
    dump_filepath = os.path.join(out_directory, dump_filename)
    print "Serializing {} rows to {}.".format(len(rows), dump_filepath)
    sys.setrecursionlimit(10000)
    with open(dump_filepath, 'wb') as dump_file:
        try:
            pickle.dump(rows, dump_file)
        except RuntimeError as e:
            print "Runtime error when pickling. Exception {}".format(e)