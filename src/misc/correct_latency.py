#! /usr/bin/env python

import sys
import os
import argparse
import pickle
import itertools
import copy
from collections import Counter
from collections import defaultdict

# Project imports
from data import *
from item_extraction import *
from image_utils import *
from item_processing import *
from geotag import geotag, closests_pose_by_time

class EvalSet(object):
    
    def __init__(self, parent_image_set):
        self.parent_image_set = parent_image_set
        self.time_offset = 0
        self.images = []
        self.averaged_items = []
        self.sse = 0
        self.avg_matching_sep = 0
        self.cost = 0

class ImageSet(object):
    
    next_image_number = 0
    
    def __init__(self):
        self.number = ImageSet.next_image_number
        ImageSet.next_image_number += 1
        self.geo_images = []
        self.time_offsets = []
        self.eval_sets = []

class PositionItem(object):
    
    def __init__(self, name, position=(0,0,0)):
        self.name = name
        self.position = position

def find_matching_item_in_eval_list(item, item_list):
    
    matching_item = None
    for item_ref in item_list:
        if is_same_position_item(item_ref, item, max_position_difference=5000):
            matching_item = item_ref
            break
        
    return matching_item
    

def get_user_index(selectable_list):
    valid_index = False
    while not valid_index:    
        index = raw_input('Enter index:  ')
        try:
            index = int(index)
            if index >= -1 and index < len(selectable_list):
                valid_index = True
            
        except ValueError:
            print 'Non-integer input'
    return index

def split_into_sets(geo_images):
    image_sets = []
    current_set = []
    time_from_last_image = None
    for i, geo_image in enumerate(geo_images):
        current_set.append(geo_image)
        if i == len(geo_images) - 1:
            break # don't have another image to compare to
        next_geo_image = geo_images[i+1]
        time_to_next_image = next_geo_image.image_time - geo_image.image_time
        if time_from_last_image is not None and time_from_last_image != 0:
            time_change = abs(time_from_last_image - time_to_next_image)
            if time_change > 6.0:
                # start new set
                #print "{} seconds between {} and {}".format(time_change, geo_image.file_name, next_geo_image.file_name)
                image_sets.append(current_set)
                current_set = []
                time_from_last_image = None
        else:
            time_from_last_image = time_to_next_image
            
    if len(current_set) > 0:
        image_sets.append(current_set)
            
    return image_sets

def is_same_position_item(item1, item2, max_position_difference):
    if item1.name != item2.name:
        return False
    
    # convert from cm to meters
    max_position_difference /= 100.0
    
    return position_difference(item1.position, item2.position) < max_position_difference
        
#def analyze_image_sets(image_sets):
        
def analyze_set(image_set, time_offset):
    
    eval_set = EvalSet(image_set)
    eval_set.time_offset = time_offset
    
    sum_squared_errors = 0
    max_sep = 0.0
    
    # create copy of geo-images
    images = copy.deepcopy(image_set.geo_images)
    
    set_items = []
    
    # change time of all images
    for image in images:
        image.image_time += time_offset
    
        # TODO: remove hardcoded
        if "c01" in image.file_name.lower():
            offsets = (1, 0.4, 0)
        elif "c04" in image.file_name.lower():
            offsets = (1, -0.4, 0)
        else:
            print "bad"
            sys.exit(1)
    
        reading_position, reading_orientation = closests_pose_by_time(image.image_time, "none", position_times, positions, orientation_times, orientations)
        geotagged_reading = geotag(image.image_time, "none", reading_position, reading_orientation, offsets)
        new_position = geotagged_reading.position
        new_heading = math.degrees(geotagged_reading.orientation[2])
        image.position = new_position
        image.heading_degrees = new_heading
        
        for item in image.items:
            item.other_items = [] # make sure no old references so we don't duplicate them when merging items below.
            item.position = calculate_position(item, image)
            set_items.append(item)
    
    # Make a copy of all codes before merging so we don't end up with duplicates (merged references and original ones).
    merged_codes = merge_items(copy.deepcopy(set_items), max_distance=5000)
    
    # calculate least squares error sum 
    for item in merged_codes:
        item_references = [item] + item.other_items
        avg_x = np.mean([it.position[0] for it in item_references])
        avg_y = np.mean([it.position[1] for it in item_references])
        avg_z = np.mean([it.position[2] for it in item_references])
    
        if len(item.other_items) > 0:
    
            distances = [position_difference(item_ref.position, (avg_x, avg_y)) for item_ref in item_references]
            
            item_combos = itertools.combinations(item_references, 2)
            for (item1, item2) in item_combos:
                separation = position_difference(item1.position, item2.position)
                if separation > max_sep:
                    max_sep = separation
            
            for dist in distances:
                sum_squared_errors += dist * dist
                
        eval_set.averaged_items.append(PositionItem(item.name, (avg_x, avg_y, avg_z)))
        
    eval_set.sse = sum_squared_errors
        
    return eval_set, images

if __name__ == '__main__':
    '''Group codes into rows/groups/segments.'''

    parser = argparse.ArgumentParser(description='''Group codes into rows/groups/segments.''')
    parser.add_argument('input_directory', help='path containing pickled files from stage 1.')
    parser.add_argument('position_filename', help='.')
    parser.add_argument('orientation_filename', help='.')
    
    args = parser.parse_args()
    
    # convert command line arguments
    input_directory = args.input_directory
    position_filepath = args.position_filename
    orientation_filepath = args.orientation_filename

    # Unpickle geo images.
    stage1_filenames = [f for f in os.listdir(input_directory) if os.path.isfile(os.path.join(input_directory, f))]
    geo_images = []
    for stage1_filename in stage1_filenames:
        stage1_filepath = os.path.join(input_directory, stage1_filename)
        with open(stage1_filepath) as stage1_file:
            file_geo_images = pickle.load(stage1_file)
            print 'Loaded {} geo images from {}'.format(len(file_geo_images), stage1_filename)
            geo_images += file_geo_images
            
    if len(geo_images) == 0:
        print "Couldn't load any geo images from {}".format(stage1_filepath)
        sys.exit(1)
        
    print "Sorting geo images by time"
    geo_images = sorted(geo_images, key=lambda image: image.image_time)
            
    cam1_geo_images = [image for image in geo_images if 'c01' in image.file_name.lower()]
    cam2_geo_images = [image for image in geo_images if 'c04' in image.file_name.lower()]
            
    cam1_sets = split_into_sets(cam1_geo_images)
    cam2_sets = split_into_sets(cam2_geo_images)
            
    cam1_sets = [s for s in cam1_sets if len(s) > 15]
    cam2_sets = [s for s in cam2_sets if len(s) > 15]
    
    if len(cam1_sets) != len(cam2_sets):
        print "number of camera sets don't match."    
        print "cam1 len {} cam2 len {}".format(len(cam1_sets), len(cam2_sets))
        sys.exit(1)
          
    image_sets = []  
    for set1, set2 in zip(cam1_sets, cam2_sets):
        image_set = ImageSet()
        # Remove first and last 3 images from each set since there times might be really off.
        set1 = set1[3:-3]
        set2 = set2[3:-3]
        image_set.geo_images = set1 + set2    
        image_sets.append(image_set)

    # Read in positions.
    positions = []
    print 'Reading in positions from {}'.format(position_filepath)
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
    print 'Reading in orientation from {}'.format(orientation_filepath)
    with open(orientation_filepath) as orientation_file:
        orientations = [line.replace(',',' ').split() for line in orientation_file.readlines()]
        orientations = [[float(i) for i in orientation] for orientation in orientations]
    print 'Read {} orientations'.format(len(orientations))
    
    print "Sorting orientations by time."
    orientations = sorted(orientations, key=lambda o: o[0])
    
    # Split off time from orientation now that it's sorted.
    orientation_times = [o[0] for o in orientations]
    orientations = [o[1:] for o in orientations]
        
    start_time = -7
    end_time = 7
    time_step = .05
        
    analyzed_sets = []
    for k, image_set in enumerate(image_sets):
        
        if len(image_set.geo_images) <= 1:
            print "Really small image set.  Skipping."
            continue

        print "{} images in set from {} to {}".format(len(image_set.geo_images), image_set.geo_images[0].file_name, image_set.geo_images[-1].file_name)

        # must have 0.0 be first time offset so that sse check below works
        image_set.time_offsets = [0.0] + list(np.arange(start_time, end_time+time_step, time_step))

        for time_offset in image_set.time_offsets:
            eval_set, _ = analyze_set(image_set, time_offset)
            image_set.eval_sets.append(eval_set)
            
            if eval_set.sse == 0.0:
                # No duplicate elements so don't keep analyzing.
                print "No items occuring in multiple images so moving to next set."
                image_set.time_offsets = [eval_set.time_offset]
                if eval_set.time_offset != 0.0:
                    print "Bad first time offset."
                    sys.exit(1)
                break
            
        analyzed_sets.append(image_set)
        
    
    print str(len(analyzed_sets))

    for image_set in analyzed_sets:
        print "Image set {} has {} eval sets".format(image_set.number, len(image_set.eval_sets))
        if len(image_set.eval_sets) == 0:
            print "Empty eval sets after analyzing. Shouldn't happen."
            sys.exit(1)     
        
    chosen_sets = []
    for i, image_set in enumerate(analyzed_sets):

        original_items = image_set.eval_sets[0].averaged_items
                
        tied_sets = defaultdict(list)

        for other_set in analyzed_sets[:i] + analyzed_sets[i+1:]:
            other_items = other_set.eval_sets[0].averaged_items
            for item in original_items:
                for other_item in other_items:
                    # TODO use different function
                    if is_same_position_item(item, other_item, max_position_difference=5000):
                        tied_sets[other_set].append((item, other_item, position_difference(item.position, other_item.position)))
                
        print "For set {} found {} other sets with matching items.".format(image_set.number, len(tied_sets.keys()))
                
        all_seps = []
        for other_set, all_matching_items in tied_sets.iteritems():
            these_items, other_items, seps = zip(*all_matching_items)
            
            #for i, sep in enumerate(seps):
            #    print "{} and {} has sep of {}".format(these_items[i].name, other_items[i].name, sep)
            
            print "..comparing to set {} with {} matching items.".format(other_set.number, len(all_matching_items))
            
            eval_seps = []
            for eval_set in image_set.eval_sets:
                # Find item in current eval set corresponding to matched item
                these_items = [find_matching_item_in_eval_list(item, eval_set.averaged_items) for item in these_items]
                
                for other_eval_set in other_set.eval_sets:
                    group_seps = 0
                    other_items = [find_matching_item_in_eval_list(item, other_eval_set.averaged_items) for item in other_items]
                    
                    for this_item, other_item in zip(these_items, other_items):
                        diff = position_difference(this_item.position, other_item.position)
                        #print "{} at {} sec and {} at {} sec has sep of {}".format(this_item.name, eval_set.time_offset, other_item.name, other_eval_set.time_offset, diff)
                        group_seps += diff
                        
                    average_sep_per_code = 0
                    if len(these_items) > 0:
                        average_sep_per_code = group_seps / len(these_items)

                    eval_seps.append((eval_set, other_eval_set, average_sep_per_code))
                    
            sorted_seps = sorted(eval_seps, key=lambda s: s[2])
            smallest_sep = sorted_seps[0]
            all_seps += eval_seps
            #print "Smallest avg sep is {} at time offsets {} and {}".format(smallest_sep[2], smallest_sep[0].time_offset, smallest_sep[1].time_offset)
            
        for eval_set in image_set.eval_sets:
            
            avg_sep_within_set = math.sqrt(eval_set.sse)
            
            # one matching sep for each tie group.  The value is the smallest for that tie group.
            matching_seps = [sep for sep in all_seps if (sep[0].time_offset == eval_set.time_offset)]
            
            if len(matching_seps) > 0:
                avg_matching_sep = np.mean([sep[2] for sep in matching_seps])
                
                eval_set.avg_matching_sep = avg_matching_sep
                
                eval_set.cost = avg_sep_within_set * .5 + avg_matching_sep * .5
            else:
                # Can only rely on separation within a set
                eval_set.avg_matching_sep = 0
                
                eval_set.cost = avg_sep_within_set
            
        sorted_eval_sets = sorted(image_set.eval_sets, key=lambda eval_set: eval_set.cost)
            
        eval_set_with_smallest_cost = sorted_eval_sets[0]
        chosen_sets.append(eval_set_with_smallest_cost)
           
    output_images = []
    for i, chosen_set in enumerate(chosen_sets):
        print "Set {} smallest cost {} at time offset {}. sqrt(sse) {} avg_match_sep {}".format(i, chosen_set.cost, chosen_set.time_offset, math.sqrt(chosen_set.sse), chosen_set.avg_matching_sep)
        _, geo_images = analyze_set(chosen_set.parent_image_set, chosen_set.time_offset)
        output_images += geo_images
    
    for image_set in image_sets:
        with open(os.path.join(input_directory, "set_{}.csv".format(image_set.number)), 'w') as image_set_file:
            for eval_set in image_set.eval_sets:
                image_set_file.write("{},{},{},{}\n".format(eval_set.time_offset, eval_set.cost, math.sqrt(eval_set.sse), eval_set.avg_matching_sep))
        
    print "Resorting images by timestamp."
    output_images = sorted(output_images, key=lambda i: i.image_time)
        
    #dump_filename = "latencyfixed".format(just_in_filename, in_fileext)
    dump_filepath = os.path.join(input_directory, 'latency_fixed.txt')
    print "Serializing {} geo images to {}.".format(len(output_images), dump_filepath)

    with open(dump_filepath, 'wb') as dump_file:
        pickle.dump(output_images, dump_file)
