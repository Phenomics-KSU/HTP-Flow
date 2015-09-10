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

def make_grouping_info_unique(grouping_info):
    # Warn if there are duplicate groups in info file.
    unique_grouping_info_dict = defaultdict(list)
    unique_grouping_info_list = []
    for info in grouping_info:
        unique_grouping_info_dict[info[0]].append(info)
    for id, infos in unique_grouping_info_dict.iteritems():
        if len(infos) > 2:
            print "More than 2 entries with id {}".format(id)
        elif len(infos) == 2:
            if infos[0][:-1] == infos[1][:-1]:
                print "Duplicate entries with id {}".format(id)
            else:
                print "Two different entries with id {}".format(id)
                print infos
            unique_grouping_info_list.append(infos[0])
        else: # just one unique info listing
            unique_grouping_info_list.append(infos[0])
    return unique_grouping_info_list
    
def unpickle_geo_images(input_directory):
    stage1_filenames = [f for f in os.listdir(input_directory) if os.path.isfile(os.path.join(input_directory, f))]
    geo_images = []
    for stage1_filename in stage1_filenames:
        stage1_filepath = os.path.join(input_directory, stage1_filename)
        with open(stage1_filepath) as stage1_file:
            file_geo_images = pickle.load(stage1_file)
            print 'Loaded {} geo images from {}'.format(len(file_geo_images), stage1_filename)
            geo_images += file_geo_images
    return geo_images

def all_codes_from_geo_images(geo_images):
    all_codes = []
    for geo_image in geo_images:
        all_codes += [item for item in geo_image.items if 'code' in item.type.lower()]
    return all_codes

def do_row_replacements(all_codes):

    row_replacements = ['''5    622404.3927    4292601.145''',
                        '''6    622403.4527    4292600.131''',
                        '''21    622389.8787    4292601.365''',
                        '''22    622388.7657    4292600.238''',
                        #'''44    622367.3307    4292598.465''',
                        #'''45    622366.2117    4292597.781''',
                        #'''46    622365.2607    4292597.434''',
                        '''47    622364.6697    4292597.434''',
                        '''48    622363.2557    4292597.847''',
                        '''49    622362.2257    4292597.054''',
                        '''50    622361.1887    4292596.705''',
                        '''51    622360.2127    4292598.022''',
                        '''52    622359.3467    4292597.787''',
                        #'''53    622358.3927    4292597.661''',
                        #'''54    622357.5137    4292598.313''',
                        '''55    622356.5707    4292597.522''',
                        '''56    622355.6987    4292597.731''',
                        #'''57    622354.8327    4292597.495''',
                        #'''58    622353.9647    4292597.482'''
                        ]
    
    for row_replacement in row_replacements:
        
        line_items = [i.strip() for i in row_replacement.split(' ')]
        line_items = filter(None, line_items) # remove empty entries
        
        row_name = "R." + line_items[0]
        row_easting = float(line_items[1])
        row_northing = float(line_items[2])
        
        for code in all_codes:
            if code.type == 'GroupCode':
                continue
            replacement_code = copy.copy(code)
            replacement_code.name = row_name
            replacement_code.position = (row_easting, row_northing, code.position[2])
            if is_same_item(code, replacement_code, max_position_difference=5000):
                #print "Updating code " + code.name
                code.position = replacement_code.position
                
def parse_updated_items(updated_items_filepath):
    
    updated_all_items = []
    updated_missing_items = []
    updated_none_items = []
    
    if updated_items_filepath != 'none':
        if os.path.exists(updated_items_filepath):
            updated_all_items, updated_missing_items, updated_none_items = parse_updated_fix_file(updated_items_filepath)
            print "From updated fix file parsed: "
            print "All {} missing {} none {}".format(len(updated_all_items), len(updated_missing_items), len(updated_none_items))
        else:
            print "Updated file file {} does not exist.".format(updated_items_filepath)
        
    return updated_all_items, updated_missing_items, updated_none_items

def add_in_none_codes(updated_none_items, grouping_info):

    # codes that were missing from expected grouping file
    for none_item in updated_none_items:
        # TODO make grouping info a class. This needs to stay in sync with actual parsing of grouping file.
        order_entered = -1 # don't know it wasn't in file
        qr_id = none_item[0] # same as name
        flag = none_item[3]
        entry = flag[:-1]
        rep = flag[-1].upper()
        try:
            # use actual number of plant since we don't know estimated.
            actual_num_plants = int(none_item[2])
            estimated_num_plants = actual_num_plants
        except ValueError:
            estimated_num_plants = -1
        grouping_info.append((qr_id, entry, rep, estimated_num_plants, order_entered))

def add_in_missing_codes(updated_missing_items, all_codes):

    # codes that weren't originally found
    for missing_item_info in updated_missing_items:
        missing_name = missing_item_info[4]
        missing_flag =  missing_item_info[5]

        # TODO once have position then add to list
        if 'R.' in missing_flag:
            # TODO update once missing codes have actual position
            #all_codes.append(RowCode(missing_name, position=all_codes[0].position))
            pass
        else: # group code
            # TODO update once missing codes have actual position
            group_code = GroupCode(missing_name, position=all_codes[0].position)
            group_code.entry = missing_flag[:-1]
            group_code.rep = missing_flag[-1].upper()
            #all_codes.append(group_code)
            
def check_code_precision(merged_codes):
    # Sanity check that multiple references of the same code are all close to each other.
    largest_separation = 0
    sum_separation = 0
    sum_separation_count = 0
    for code in merged_codes:
        avg_position = average_position(code)
        code_refs = [code] + code.other_items
        for code_ref in code_refs:
            diff = position_difference(avg_position, code_ref.position)
            sum_separation += diff
            sum_separation_count += 1
            if diff > largest_separation:
                largest_separation = diff
            
        #code_combos = itertools.combinations([code] + code.other_items, 2)
        #for (code1, code2) in code_combos:
        #    separation = position_difference(code1.position, code2.position)
        #    if separation > largest_separation:
        #        largest_separation = separation
                
    average_separation = 0
    if sum_separation_count > 0:
        average_separation = sum_separation / sum_separation_count
                
    print "From average position largest separation is {} and average is {}".format(largest_separation, average_separation)

def warn_about_missing_and_extra_codes(missing_code_ids, extra_code_ids):
    print "Missing {} ids.".format(len(missing_code_ids))
    if len(missing_code_ids) < 30:
        for id in missing_code_ids:
            print "missing id: {}".format(id)
            
    if len(extra_code_ids) > 0:
        print "WARNING: Found {} group codes that aren't listed in expected grouping file.".format(len(extra_code_ids))
        for id in extra_code_ids:
            print "Extra ID: {}".format(id)

def associate_ids_to_entry_rep(group_codes):
    # Update group codes with entry x rep
    num_matched_ids_to_info = 0
    for group_code in group_codes:
        matching_info = [info for info in grouping_info if info[0] == group_code.name]
        if len(matching_info) == 0:
            continue
        matching_info = matching_info[0]
        group_code.entry = matching_info[1]
        group_code.rep = matching_info[2]
        num_matched_ids_to_info += 1
        
    print "Updated {} group codes with entry x rep".format(num_matched_ids_to_info)

def group_row_codes(row_codes):
    # Group row codes by row number.
    grouped_row_codes = defaultdict(list)
    for code in row_codes:
        grouped_row_codes[code.row_number].append(code)
    return grouped_row_codes

def display_row_info(grouped_row_codes):
    # Show user information about which rows were found and which are missing.
    sorted_row_numbers = sorted(grouped_row_codes.keys())
    smallest_row_number = sorted_row_numbers[0]
    biggest_row_number = sorted_row_numbers[-1]
    print "Found rows from {} to {}".format(smallest_row_number, biggest_row_number)
    missing_row_numbers = set(range(smallest_row_number, biggest_row_number+1)) - set(sorted_row_numbers)
    if len(missing_row_numbers) > 0:
        print "Missing row numbers {}".format(missing_row_numbers)
    else:
        print "No skipped row numbers."

def create_rows(grouped_row_codes):
    rows = []
    for row_number, codes in grouped_row_codes.iteritems():
        if len(codes) == 1:
            print "Only found 1 code for row {}".format(row_number)
        elif len(codes) > 2:
            print "Found {} codes for row {}".format(len(codes), row_number)
        else:
            # Create row objects with start/end codes.
            code1, code2 = codes
            start_code, end_code = orient_items(code1, code2, field_direction)
            if start_code and end_code:
                rows.append(Row(start_code, end_code)) 
    return rows

def associate_row_numbers_with_up_back_rows():
    
    # Take into account how the row runs (up or back)
    # Have to change this for each field or all to pass in with args.
    first_start = 1 # first section start row
    first_end = 22 # last row number from first section
    second_start = first_end + 1 # first row number from second section (since started in wrong direction)
    second_end = 58 # last row number in field
    row_step = 4 # Goes with double planter.
    # First section
    up_row_nums = range(first_start, second_start, row_step)
    up_row_nums += range(first_start+1, second_start, row_step)
    back_row_nums = range(first_start+2, second_start, row_step)
    back_row_nums += range(first_start+3, second_start, row_step)
    # Second section
    up_row_nums += range(second_start, second_end+1, row_step)
    up_row_nums += range(second_start+1, second_end+1, row_step)
    back_row_nums += range(second_start+2, second_end+1, row_step)
    back_row_nums += range(second_start+3, second_end+1, row_step)
    
    up_row_nums = sorted(up_row_nums, key=lambda n: n)
    back_row_nums = sorted(back_row_nums, key=lambda n: n)
    
    return up_row_nums, back_row_nums

def verify_up_back_row_numbers(up_row_nums, back_row_nums):

    overlap = list(set(up_row_nums) & set(back_row_nums))
    if len(overlap) > 0:
        print "Bad row generation.  Overlapping between up and back: "
        print overlap
        sys.exit(1)
    
    if back_row_nums[-1] != 58:
        print "Bad row generation.  Last row should be back and number 58"
        sys.exit(1) 
        
    if 22 not in up_row_nums or 23 not in up_row_nums:
        print "Bad row generation.  Back rows should have number 22"
        sys.exit(1) 

def assign_rows_a_direction(rows, up_row_nums, back_row_nums):
    for row in rows:
        if row.number in up_row_nums:
            row.direction = 'up'
        elif row.number in back_row_nums:
            row.direction = 'back'
        else:
            print "Row number {} doesn't have a defined up/back direction".format(row.number)
            sys.exit(1)

def calculate_projection_to_nearest_row(group_codes, rows):
    codes_with_projections = []
    for code in group_codes:
        
        min_distance = sys.float_info.max
        projection_distance = 0 # projection along closest row (in meters) from bottom of field to top.
        closest_row = None
        for row in rows:
            start_pos = row.start_code.position
            end_pos = row.end_code.position
            distance_to_code, row_projection_distance = lateral_and_projection_distance_2d(code.position, start_pos, end_pos)
            distance_to_code = abs(distance_to_code)
            if distance_to_code < min_distance:
                min_distance = distance_to_code
                projection_distance = row_projection_distance
                closest_row = row
        if closest_row is not None and min_distance < 3: # TODO remove hard-coded value
            code.row = closest_row.number
            if closest_row.number == 0:
                print "closest row has 0 number"
            codes_with_projections.append((code, projection_distance))
        else:
            code.row = -1
            print "Couldn't find a row for code {}. Closest row is {} meters away.".format(code.name, min_distance)
            
    return codes_with_projections

def create_group_segments(codes_with_projections):
    
    group_segments = []
    for row in rows:
        group_codes_in_row = [code for code in codes_with_projections if code[0].row == row.number]
        if len(group_codes_in_row) == 0:
            print "No group codes in row {}.".format(row.number)
            continue
        # Sort group codes by projection distance.
        sorted_row_codes = [row.start_code]
        sorted_group_codes_in_row = sorted(group_codes_in_row, key=lambda c: c[1])
        sorted_row_codes += [code[0] for code in sorted_group_codes_in_row]
        sorted_row_codes.append(row.end_code)
        if row.direction == 'back':
            sorted_row_codes = list(reversed(sorted_row_codes))
        
        for i, code in enumerate(sorted_row_codes[:-1]):
            new_segment = PlantGroupSegment(start_code=code, end_code=sorted_row_codes[i+1])
            row.group_segments.append(new_segment)
            group_segments.append(new_segment)
            
    return group_segments

def organize_group_segments(group_segments):

    start_segments = []
    middle_segments = []
    end_segments = []
    single_segments = []
    for segment in group_segments:
        starts_with_row_code = segment.start_code.type.lower() == 'rowcode'
        ends_with_row_code = segment.end_code.type.lower() == 'rowcode'
        if starts_with_row_code and ends_with_row_code:
            middle_segments.append(segment)
        elif starts_with_row_code:
            start_segments.append(segment)
        elif ends_with_row_code:
            end_segments.append(segment)
        else:
            single_segments.append(segment)
    
    return start_segments, middle_segments, end_segments, single_segments

def complete_groups(end_segments, single_segments):
    
    groups = []
    for end_segment in end_segments[:]: 
        
        field_pass = [fpass for fpass in field_passes if end_segment.row_number in [row.number for row in fpass]]
        
        if len(field_pass) == 0:
            print "End segment {} with row {} isn't in field pass list.".format(end_segment.start_code.name, end_segment.row_number)
            continue
        
        field_pass = field_pass[0]
        pass_index = [row.number for row in field_pass].index(end_segment.row_number)
        
        field_pass_index = field_passes.index(field_pass)
        if field_pass_index >= len(field_passes) - 1:
            print "End segment {} can't be matched since it's in the last pass. Treating as single segment.".format(end_segment.start_code.name)
            single_segments.append(end_segment)
            end_segments.remove(end_segment)
            continue
        
        next_pass = field_passes[field_pass_index+1]
        
        if len(next_pass) < 2:
            print "Pass {} doesn't contain 2 rows".format(field_pass_index+1)
            continue
        
        next_pass_index = 0 # assume inside
        if pass_index == 0:
            next_pass_index = 1 # was actually outside
            
        this_planting_row = field_pass[pass_index]
        next_planting_row = next_pass[next_pass_index]
        
        if this_planting_row.direction == next_planting_row.direction:
            single_segments.append(end_segment)
            end_segments.remove(end_segment)
            print "End segment {} in row {} can't match to row {} since both rows are in the same direction ({}).  Treating as single segment.".format(end_segment.start_code.name, this_planting_row.number, next_planting_row.number, this_planting_row.direction)
            continue
        
        if len(next_planting_row.group_segments) == 0:
            single_segments.append(end_segment)
            end_segments.remove(end_segment)
            print "End segment {} in row {} can't match to row {} since next row doesn't have any segments.  Treating as single segment.".format(end_segment.start_code.name, this_planting_row.number, next_planting_row.number)
            continue

        matching_start_segment = next_planting_row.group_segments[0]
        new_group = PlantGroup()
        new_group.add_segment(end_segment)
        new_group.add_segment(matching_start_segment)
        groups.append(new_group)
        
    return groups

def handle_single_segments(single_segments, groups):
    for segment in single_segments:
        new_group = PlantGroup()
        new_group.add_segment(segment)
        groups.append(new_group)

def display_group_info(group_segments, groups):
    print "Combined {} segments into {} groups.".format(len(group_segments), len(groups))
    
    group_seg_count = defaultdict(list)
    for group in groups:
        group_seg_count[len(group.segments)].append(group)
        
    for num_segs, groups_with_that_many_segs in group_seg_count.iteritems():
        print "{} groups with {} segments".format(len(groups_with_that_many_segs), num_segs) 

def order_and_number_items_by_row(rows):
    '''JUST HERE FOR FINDING MISSING CODES'''
    rows = sorted(rows, key=lambda r: r.number)
    #missing_code_ids = sorted(missing_code_ids, key=lambda r: int(r))
    
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
        #if row.number % 2 == 0:
        #    row_items.reverse()
            
        for item_num_in_row, item in enumerate(row_items):
            item.number_within_field = current_field_item_num
            item.number_within_row = item_num_in_row + 1 # index off 1 instead of 0
            ordered_items.append(item)
            current_field_item_num += 1
            
    return ordered_items

def warn_about_bad_group_lengths(groups):

    num_good_lengths = 0 # how many groups have a close expected length
    num_bad_lengths = 0 # how many groups don't have a close expected length
    num_no_info = 0 # how many groups don'have any expected lengths
    num_too_much_info = 0 # how many groups have more than 1 expected lengths
    for group in groups:
        info = [i for i in grouping_info if i[0] == group.id]
        if len(info) == 0:
            #print "no expected info for group found in field {}".format(group.id)
            num_no_info += 1
            group.expected_num_plants = -1
            continue
        if len(info) > 1:
            #print "too many matches for row {} found in plant info file.".format(group.id)
            num_too_much_info += 1
            group.expected_num_plants = -1
            continue
        info = info[0]
        expected_num_plants = info[3]
        group.expected_num_plants = expected_num_plants
        if len(group.segments) == 1:
            # TODO clean this ups
            group.segments[0].expected_num_plants = group.expected_num_plants
        spacing_between_plants = 0.9144 # meters
        spacing_for_codes = spacing_between_plants / 2.0
        expected_length = (expected_num_plants - 1) * spacing_between_plants
        expected_length += spacing_for_codes * 2 * len(group.segments) # for before and end codes for each segment
        actual_length = group.length

        max_length_difference = 5.0

        length_difference = actual_length - expected_length

        if abs(length_difference) > max_length_difference:
            #print "For group {} the actual length of {} is {} meters off from expected length {}.".format(group.id, actual_length, length_difference, expected_length)
            if length_difference > max_length_difference:
                print "Group with start code {} ({}{}) that is {} from the {} side of row {} is {} meters too long.".format(group.id,
                                                                                                                     group.entry,
                                                                                                                     group.rep,
                                                                                                                     group.start_code.number_within_row,
                                                                                                                     'south',
                                                                                                                     group.start_code.row, 
                                                                                                                     length_difference)
            num_bad_lengths += 1
        else:
            num_good_lengths += 1
    
    print "Found {} groups with close expected lengths and {} groups that aren't close.".format(num_good_lengths, num_bad_lengths)
    print "{} groups with no expected number of plants and {} with too many expected number number of plants.".format(num_no_info, num_too_much_info)

def display_missing_codes_neighbors(missing_code_ids):

    for missing_id in missing_code_ids:
        missing_id_info = [info for info in grouping_info if info[0] == missing_id][0]
        
        order_entered = missing_id_info[4]
        
        print "\nMissing id {} ({}{}) is entered {} in document".format(missing_id, missing_id_info[1], missing_id_info[2], order_entered)
  
        neighbor_info = [] 
        neighbors_order_entered = range(order_entered - 3, order_entered + 4, 1)
        for neighbor_order_entered in neighbors_order_entered:
            close_neighbor_info = [info for info in grouping_info if info[4] == neighbor_order_entered]
            neighbor_info.append(close_neighbor_info)
            '''
            if missing_id == '1525':
                print str(neighbor_order_entered)
                grouping_info = sorted(grouping_info, key=lambda k: k[4])
                for i in grouping_info:
                    print i
                sys.exit(1)
            '''

        for neighbor in neighbor_info:
            if len(neighbor) == 0:
                print "\tNo neighbor in document."
            else:
                neighbor = neighbor[0]
                neighbor_code = [code for code in group_codes if code.name == neighbor[0]]
                if len(neighbor_code) == 0:
                    print "\tNeighbor code with id {} not found in field.".format(neighbor[0])
                else:
                    neighbor_code = neighbor_code[0]
                    print "\tHas neighbor code {} ({}{}) that is {} code from {} side of row {}".format(neighbor_code.name,
                                                                                                                      neighbor_code.entry,
                                                                                                                      neighbor_code.rep,
                                                                                                                      neighbor_code.number_within_row,
                                                                                                                      'south',
                                                                                                                      neighbor_code.row)

def update_number_of_plants_in_groups(updated_all_items, group_segments):

    num_fixed_segments_expected_plants = 0
    for updated_item_info in updated_all_items:
        item_name = updated_item_info[0]
        expected_plants = updated_item_info[1]
        actual_plants = updated_item_info[2]
        position = updated_item_info[6]

        if 'R.' not in item_name:
            try:
                actual_plants = int(actual_plants)
                matching_segments = [seg for seg in group_segments if seg.start_code.name == item_name]
                if len(matching_segments) >= 1:
                    matching_segments[0].expected_num_plants = actual_plants # update expected number of plant to actual number
                    num_fixed_segments_expected_plants += 1
            except ValueError:
                pass
    
    print "{} segments updated with actual number of plants.".format(num_fixed_segments_expected_plants)

def update_number_of_plants_in_end_groups(updated_all_items, groups):
    
    measured_end_segment_row_codes = []        
    for updated_item in updated_all_items:
        
        item_name = updated_item[0]
        item_position = updated_item[6]
        actual_plants = updated_item[2]
        
        if 'R.' in item_name:
            measured_row_code = RowCode(item_name, position=item_position)
            measured_row_code.measured_plants = actual_plants
            measured_end_segment_row_codes.append(measured_row_code)
        
    # Calculate expected plants in each group that wraps to the next row.
    measured_row_seg_count = 0
    for group in groups:
        if len(group.segments) < 2:
            continue # don't care about single segments
        
        total_group_length = group.length
        remaining_group_plants = group.expected_num_plants
        for segment in group.segments:
            percent_of_group = segment.length / total_group_length
            num_segment_plants = int(round(group.expected_num_plants * percent_of_group))
            num_segment_plants =  min(remaining_group_plants, num_segment_plants)
            segment.expected_num_plants = num_segment_plants
            remaining_group_plants -= num_segment_plants
            
            # Check to see if actual amount was counted in the field.
            for measured_row_code in measured_end_segment_row_codes:
                if is_same_position_item(segment.start_code, measured_row_code, 4000) or \
                   is_same_position_item(segment.end_code, measured_row_code, 4000):
                    segment.expected_num_plants = measured_row_code.measured_plants
                    measured_row_seg_count += 1
    print "Updated {} row segs wtih measured values".format(measured_row_seg_count)

def output_results(geo_images, output_directory):
    
    dump_filename = "stage2_rows_{}_{}.txt".format(geo_images[0].image_time, geo_images[-1].image_time)
    dump_filepath = os.path.join(output_directory, dump_filename)
    print "Serializing {} rows to {}.".format(len(rows), dump_filepath)
    sys.setrecursionlimit(10000)
    with open(dump_filepath, 'wb') as dump_file:
        try:
            pickle.dump(rows, dump_file)
        except RuntimeError as e:
            print "Runtime error when pickling. Exception {}".format(e)


if __name__ == '__main__':
    '''Group codes into rows/groups/segments.'''

    parser = argparse.ArgumentParser(description='''Group codes into rows/groups/segments.''')
    parser.add_argument('group_info_file', help='file with group numbers and corresponding number of plants.')
    #parser.add_argument('path_file', help='file with path position information used for segmenting rows.')
    parser.add_argument('input_directory', help='directory containing pickled files from previous stage.')
    parser.add_argument('field_direction', help='Planting angle of entire field.  0 degrees East and increases CCW.')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('-u', dest='updated_items_filepath', default='none', help='')
    
    args = parser.parse_args()
    
    # convert command line arguments
    group_info_file = args.group_info_file
    #path_file = args.path_file
    input_directory = args.input_directory
    field_direction = float(args.field_direction)
    output_directory = args.output_directory
    updated_items_filepath = args.updated_items_filepath
    
    # Parse in group info
    grouping_info = parse_grouping_file(group_info_file)
    print "Parsed {} groups. ".format(len(grouping_info))
    
    grouping_info = make_grouping_info_unique(grouping_info)

    geo_images = unpickle_geo_images(input_directory)

    if len(geo_images) == 0:
        print "Couldn't load any geo images from input directory {}".format(input_directory)
        sys.exit(1)
    
    all_codes = all_codes_from_geo_images(geo_images)
    
    print 'Found {} codes in {} geo images.'.format(len(all_codes), len(geo_images))
    if len(all_codes) == 0:
        sys.exit(1)
        
    # correction step
    do_row_replacements(all_codes)
                
    updated_all_items, updated_missing_items, updated_none_items = parse_updated_items(updated_items_filepath)

    add_in_none_codes(updated_none_items, grouping_info)
        
    # TODO go through and estimate plants / meter.  At end go through and calculate the estimated
    # positions then copy them and put them back up here.

    add_in_missing_codes(updated_missing_items, all_codes)
        
    #for code in all_codes:
    #    from pprint import pprint
    #    pprint(vars(code))
    #    print "\n\n\n"
    
    # Merge items down so they're unique.  One code with reference other instances of that same code.
    merged_codes = merge_items(all_codes, max_distance=2000)
    
    merged_codes = cluster_merged_items(merged_codes, geo_images, cluster_size=0.3)
    
    print '{} unique codes.'.format(len(merged_codes))
    
    check_code_precision(merged_codes)
                
    row_codes = [code for code in merged_codes if code.type.lower() == 'rowcode']
    group_codes = [code for code in merged_codes if code.type.lower() == 'groupcode']
    
    # Tell user how many codes are missing or if there are any extra codes.
    found_code_ids = [code.name for code in group_codes] 
    all_code_ids = [g[0] for g in grouping_info] 
    missing_code_ids = [id for id in all_code_ids if id not in found_code_ids]
    extra_code_ids = [id for id in found_code_ids if id not in all_code_ids]
    
    warn_about_missing_and_extra_codes(missing_code_ids, extra_code_ids)

    associate_ids_to_entry_rep(group_codes)

    grouped_row_codes = group_row_codes(row_codes)
    
    if len(grouped_row_codes) == 0:
        print "No rows detected."
        sys.exit(1)

    display_row_info(grouped_row_codes)
        
    rows = create_rows(grouped_row_codes)
                
    if len(rows) == 0:
        print "No complete rows found.  Exiting."
        sys.exit(1)
        

    up_row_nums, back_row_nums = associate_row_numbers_with_up_back_rows()

    verify_up_back_row_numbers(up_row_nums, back_row_nums)

    assign_rows_a_direction(rows, up_row_nums, back_row_nums)

    field_passes = [rows[x:x+2] for x in xrange(0, len(rows), 2)]

    # Create list of vectors corresponding to rows then for each QR code figure out which one it belongs to and add it to row object
    #row_vectors = []
    #for row in rows:
    #    s = row.start_code.positions
    #    e = row.end_code.positions
    #    vector = (e[0]-s[0], e[1]-s[1], e[2]-s[2])
    #    row_vectors.append(row.number, vector)

    codes_with_projections = calculate_projection_to_nearest_row(group_codes, rows)
            
    group_segments = create_group_segments(codes_with_projections)
        
    # Go through and organize segments.
    start_segments, middle_segments, end_segments, single_segments = organize_group_segments(group_segments)
    
    if len(middle_segments) > 0:
        print "Middle segments that span entire row aren't supported right now. Exiting"
        sys.exit(1)
    
    groups = complete_groups(end_segments, single_segments)
        
    handle_single_segments(single_segments, groups)
        
    display_group_info(group_segments, groups)

    # JUST HERE FOR FINDING MISSING CODES
    order_and_number_items_by_row(rows)
    
    warn_about_bad_group_lengths(groups)

    display_missing_codes_neighbors(missing_code_ids)
    
    # update # of plants in each measured groups and ones at end of rows
    update_number_of_plants_in_groups(updated_all_items, group_segments)

    update_number_of_plants_in_end_groups(updated_all_items, groups)
                    
    output_results(geo_images, output_directory)