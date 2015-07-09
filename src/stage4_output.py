#! /usr/bin/env python

import sys
import os
import argparse
import pickle
import time

# non-default import
import numpy as np

# Project imports
from data import *
from item_processing import export_results

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
    
    items = []
    for row in rows:
        for segment in row.group_segments:
            items += segment.items
    
    print 'Found {} items in rows.'.format(len(items))
    
    print 'Sorting items by number within field.'
    items = sorted(items, key=lambda item: item.number_within_field)
    
    # Write everything out to CSV file to be imported into database.
    all_results_filename = time.strftime("_results_all-%Y%m%d-%H%M%S.csv")
    all_results_filepath = os.path.join(out_directory, all_results_filename)
    all_output_items = []
    for item in items:
        all_output_items.extend([item] + item.other_items)
    export_results(all_output_items, all_results_filepath)
    print "Exported all results to " + all_results_filepath
    
    # Write averaged results out to file.
    avg_results_filename = time.strftime("_results_averaged-%Y%m%d-%H%M%S.csv")
    avg_results_filepath = os.path.join(out_directory, avg_results_filename)
    avg_output_items = []
    for item in items:
        avg_item = item # copy.copy(item)
        item_references = [avg_item] + avg_item.other_items
        avg_x = np.mean([item.position[0] for item in item_references])
        avg_y = np.mean([item.position[1] for item in item_references])
        avg_z = np.mean([item.position[2] for item in item_references])
        avg_item.position = (avg_x, avg_y, avg_z)
        avg_item.area = np.mean([item.area for item in item_references])
        avg_width = np.mean([item.size[0] for item in item_references])
        avg_height = np.mean([item.size[1] for item in item_references])
        avg_item.size = (avg_width, avg_height)
        avg_output_items.append(avg_item)
    print 'Output averaged {} items'.format(len(avg_output_items))
    export_results(avg_output_items, avg_results_filepath)
    print "Exported averaged results to " + avg_results_filepath
    