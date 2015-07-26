#! /usr/bin/env python

import sys
import os
import argparse
import pickle
import time
import csv

# non-default import
import numpy as np

# Project imports
from data import *
from item_processing import export_results, position_difference

if __name__ == '__main__':
    '''Output results.'''

    parser = argparse.ArgumentParser(description='''Output results.''')
    parser.add_argument('input_filepath', help='pickled file from either stage 2 or stage 3.')
    parser.add_argument('output_directory', help='where to write output files')
    
    args = parser.parse_args()
    
    # convert command line arguments
    input_filepath = args.input_filepath
    out_directory = args.output_directory

    # Unpickle rows.
    with open(input_filepath) as input_file:
        rows = pickle.load(input_file)
        print 'Loaded {} rows from {}'.format(len(rows), input_filepath)
    
    rows = sorted(rows, key=lambda r: r.number)
    
    current_field_item_num = 1
    ordered_items = []
    for row in rows:
        row_items = []
        for i, segment in enumerate(row.group_segments):
            row_items.append(segment.start_code)
            row_items += segment.items
            if i == len(row.group_segments) - 1:
                row_items.append(segment.end_code) # since on last segment it won't show up in next segment
                
        # Get everything going in the 'up' direction
        if row.direction == 'back':
            row_items.reverse()
        
        # Reverse items in even row numbers for serpentine ordering    
        if row.number % 2 == 0:
            row_items.reverse()
            
        for item_num_in_row, item in enumerate(row_items):
            item.number_within_field = current_field_item_num
            item.number_within_row = item_num_in_row + 1 # index off 1 instead of 0
            ordered_items.append(item)
            current_field_item_num += 1
                
    items = ordered_items
    
    first_group_code = None
    for item in items:
        if item.type.lower() == 'groupcode':
            first_group_code = item
            break
        
    if first_group_code is None:
        print "No group codes. Exiting"
        sys.exit(1)
        
    expected_first_group_code = '930'
    if first_group_code.name != expected_first_group_code:
        expected_first_group_code_actual_index = [item.name for item in items].index(expected_first_group_code)
        print "First group code is {0} and should be {1}. {1} actually has an index of {2}. Exiting".format(first_group_code.name, expected_first_group_code, expected_first_group_code_actual_index)
        sys.exit(1)
                
    first_position = first_group_code.position
    
    for item in items:
        rel_x = item.position[0] - first_position[0]
        rel_y = item.position[1] - first_position[1]
        rel_z = item.position[2] - first_position[2]
        item.field_position = (rel_x, rel_y, rel_z)
                
    print 'Found {} items in rows.'.format(len(items))
    
    # Shouldn't be necessary, but do it anyway.
    print 'Sorting items by number within field.'
    items = sorted(items, key=lambda item: item.number_within_field)
    
    # Write everything out to CSV file to be imported into database.
    all_results_filename = time.strftime("_results_all-%Y%m%d-%H%M%S.csv")
    all_results_filepath = os.path.join(out_directory, all_results_filename)
    all_output_items = []
    for item in items:
        all_output_items.extend([item] + item.other_items)
    export_results(all_output_items, rows, all_results_filepath)
    print "Exported all results to " + all_results_filepath
    
    # Write averaged results out to file.
    avg_results_filename = time.strftime("_results_averaged-%Y%m%d-%H%M%S.csv")
    avg_results_filepath = os.path.join(out_directory, avg_results_filename)
    avg_output_items = []
    for item in items:
        avg_item = item # copy.copy(item)
        item_references = [avg_item] + avg_item.other_items
        avg_x = np.mean([it.position[0] for it in item_references])
        avg_y = np.mean([it.position[1] for it in item_references])
        avg_z = np.mean([it.position[2] for it in item_references])
        avg_item.position = (avg_x, avg_y, avg_z)
        avg_item.area = np.mean([it.area for it in item_references])
        avg_width = np.mean([it.size[0] for it in item_references])
        avg_height = np.mean([it.size[1] for it in item_references])
        avg_item.size = (avg_width, avg_height)
        avg_output_items.append(avg_item)
    print 'Output averaged {} items'.format(len(avg_output_items))
    export_results(avg_output_items, rows, avg_results_filepath)
    print "Exported averaged results to " + avg_results_filepath
