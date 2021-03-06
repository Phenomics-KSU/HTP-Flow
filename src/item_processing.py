#! /usr/bin/env python

import time
from math import sqrt

# Project imports
from data import *
from image_utils import *

def process_geo_image(geo_image, item_extractor, camera_rotation, image_directory, out_directory, use_marked_image):
    '''Return list of extracted items sorted in direction of movement.'''
    full_filename = os.path.join(image_directory, geo_image.file_name)
    
    image = cv2.imread(full_filename, cv2.CV_LOAD_IMAGE_COLOR)
    
    if image is None:
        print 'Cannot open image: {0}'.format(full_filename)
        return []
    
    # Update remaining geo image properties before doing image analysis.  This makes it so we only open image once.
    image_height, image_width, _ = image.shape
    geo_image.size = (image_width, image_height)
    
    if geo_image.resolution <= 0:
        print "Cannot calculate image resolution. Skipping image."
        return []
    
    # Specify 'image directory' so that if any images associated with current image are saved a directory is created.
    image_out_directory = os.path.join(out_directory, os.path.splitext(geo_image.file_name)[0])
    ImageWriter.output_directory = image_out_directory
    
    marked_image = None
    if use_marked_image:
        # Copy original image so we can mark on it for debugging.
        marked_image = image.copy()
    
    image_items = item_extractor.extract_items(geo_image, image, marked_image, image_out_directory)
    
    image_items = order_items(image_items, camera_rotation)

    if marked_image is not None:
        marked_image_filename = postfix_filename(geo_image.file_name, '_marked')
        marked_image_path = os.path.join(out_directory, marked_image_filename)
        cv2.imwrite(marked_image_path, marked_image)
        
    return image_items

def all_items(geo_images):
    '''Return single list of all items found within geo images.'''
    items = []
    for geo_image in geo_images:
        items.extend(geo_image.items)
    return items

def order_items(items, camera_rotation):
    '''Return new list but sorted from backward to forward taking into account camera rotation.'''
    if camera_rotation == 180:  # top to bottom
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[1])
    elif camera_rotation == 0: # bottom to top
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[1], reverse=True)
    elif camera_rotation == 90: # left to right
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[0])
    elif camera_rotation == 270: # right to left
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[0], reverse=True)
    else:
        return None
    
def merge_items(items, max_distance):
    '''Return new list of items with all duplicates removed and instead can be referenced through surviving items.'''
    unique_items = []
    for item in items:
        matching_item = None
        for comparision_item in unique_items:
            if is_same_item(item, comparision_item, max_distance):
                matching_item = comparision_item
                break
        if matching_item is None:
            #print 'No matching item for {} adding to list'.format(item.name)
            unique_items.append(item)
        else:
            # We've already stored this same item so just have the one we stored reference this one.
            matching_item.other_items.append(item)
            
    return unique_items

def cluster_merged_items(items, cluster_size):
    
    clustered_merged_items = []
    for item in items:
        clusters = []
        item_refs = [item] + item.other_items
        for item_ref in item_refs:
            added_to_an_existing_cluster = False
            for cluster in clusters:
                for clustered_item in cluster:
                    if position_difference(item_ref.position, clustered_item.position) < cluster_size:
                        cluster.append(item_ref)
                        added_to_an_existing_cluster = True
                        break
            if not added_to_an_existing_cluster:
                # make a new cluster
                clusters.append([item_ref])
        
        clusters = sorted(clusters, key=lambda c: len(c), reverse=True)
        
        if len(clusters) == 0:
            continue 
        
        kept_cluster = []
        if len(clusters) == 1:
            kept_cluster = clusters[0]
        elif len(clusters) > 1:
            largest_cluster = clusters[0]
            second_largest_cluster = clusters[1]
            
            if len(largest_cluster) > len(second_largest_cluster):
                kept_cluster = largest_cluster
            else:
                #kept_cluster = largest_cluster
                for cluster in clusters:
                    kept_cluster += cluster # keep all clusters

        main_item = kept_cluster[0]
        main_item.other_items = []
        for item in kept_cluster[1:]:
            item.other_items = []
            main_item.other_items.append(item)

        clustered_merged_items.append(main_item)

    return clustered_merged_items

def average_position(item):
    
    item_references = [item] + item.other_items
    avg_x = np.mean([it.position[0] for it in item_references])
    avg_y = np.mean([it.position[1] for it in item_references])
    avg_z = np.mean([it.position[2] for it in item_references])

    return (avg_x, avg_y, avg_y)

def touches_image_border(item, geo_image, rotated_bounding_box=True):
    '''Return true if item bounding box touches image border.'''
    rect = item.bounding_rect
    if rotated_bounding_box:
        rect = rotatedToRegularRect(item.bounding_rect)
    x1, y1, x2, y2 = rectangle_corners(rect, rotated=False)
    img_w, img_h = geo_image.size
    # Need to use (1 and -1) since bounding box has 1 pix border.
    touches_border = x1 <= 1 or y1 <= 1 or x2 >= (img_w-1) or y2 >= (img_h-1)
    return touches_border

def group_into_rows(items):
    '''Split items into list of rows.  Current row will be None if didn't end in middle of row.'''
    rows = []
    current_row = None
    outside_row_plants = [] # plants found not in a row.
    for item in items:
        if item.type == 'RowCode':
            if current_row is None:
                # Start a new row.
                current_row = Row(start_code=item)
            elif item.row_number == current_row.number:
                # Ending current row.
                current_row.end_code = item
                rows.append(current_row)
                current_row = None
                continue
            else:
                # Unexpectedly hit next row.  Likely missed row end QR code.
                print "HIT NEXT ROW!!!" # TODO ask user for correction
        else: # item isn't a row end code.
            if current_row is not None:
                current_row.items.append(item)
            else: # Not in a row.
                if item.type == 'GroupCode':
                    # Hit a QR code outside of row.  This means we likely missed the row start code.
                    print "HIT QR GROUP CODE OUTSIDE OF ROW!!!" # TODO have user fix
                else:
                    # This means item is a false positive plant since it occurred outside of row.
                    outside_row_plants.append(item)
                    
    return rows, current_row, outside_row_plants

def split_into_plant_groupings(rows):
    '''Return list of plant groups.'''
    plant_groups = []
    for row in rows:
        print "Finding plant groupings in row {0}".format(row.number)
        
        current_group = None
        for item in row.items:
            print item.type
            if item.type == 'GroupCode':
                if current_group is not None:
                    print 'Ending group ' + current_group.entry
                    # End current group.
                    plant_groups.append(current_group)
                    current_group = None
                    
                # Start a new group.
                current_group = PlantGroup(start_code=item)
                print 'Starting group ' + current_group.entry

            else: # item is a plant since it's not a code.
                if current_group is None:
                    # TODO: Need to look up and add to previous group from 2 rows ago.
                    print "TODO: Hit plant in row before group"
                else:
                    print 'Adding plant'
                    current_group.add_item(item)
                    
            if current_group is not None:
                # End current group.
                plant_groups.append(current_group)
                    
    return plant_groups


def correct_plant_groupings(plant_groups, grouping_info):
    '''Correct plant groups to match specified grouping info.'''
    for group in plant_groups:
        # Find expected number of plants in group so we can do validations/corrections.
        try:
            grouping_index = [y[0] for y in grouping_info].index(group.name)
            expected_num_plants = grouping_info[grouping_index][1]
        except ValueError:
            # TODO handle better
            print 'WARNING: Group {0} not found in provided group list. Skipping.'.format(group.name)
            continue
        
        # First need to make actual/expected number of plants match.
        num_plants = len(group.items)

        if num_plants > expected_num_plants:
            pass # group = remove_false_positive_plants(group, expected_num_plants)
        elif num_plants < expected_num_plants:
            pass # group = add_missing_plants(group, expected_num_plants)
            
        # Now fill in any gaps.
        #group = include_gaps(group)
        
def position_difference(position1, position2):
    '''Return difference in XY positions between both items.'''
    delta_x = position1[0] - position2[0]
    delta_y = position1[1] - position2[1]
    return sqrt(delta_x*delta_x + delta_y*delta_y)
        
def is_same_item(item1, item2, max_position_difference):
    '''Return true if both items are similar enough to be considered the same.'''
    if item1.type != item2.type:
        return False
    
    if (item1.type.lower() != 'rowcode') and (item1.parent_image_filename == item2.parent_image_filename):
        return False # Come from same image so can't be different... except there were duplicate row codes right next to each other.
    
    if 'code' in item1.type.lower(): 
        if item1.name == item2.name:
            # Same QR code so give ourselves more room to work with.
            # Can't just say they're the same because row/start end could have same name.
            max_position_difference = max(max_position_difference, 30)
        else:
            # Two codes with different names so can't be same item.
            return False

    # convert max difference from cm to meters
    max_position_difference /= 100.0
    
    if position_difference(item1.position, item2.position) > max_position_difference:
        return False # Too far apart
    
    return True # Similar enough

def is_same_position_item(item1, item2, max_position_difference):
    if item1.name != item2.name:
        return False
    
    # convert from cm to meters
    max_position_difference /= 100.0
    
    return position_difference(item1.position, item2.position) < max_position_difference

def cap_angle_plus_minus_180_deg(angle):
    '''Return angle in range of (-180, 180]'''
    while angle <= -180.0:
        angle += 360.0
    while angle > 180.0:
        angle -= 360.0
    return angle
        
def compare_angles(angle1, angle2, thresh):
    '''Return true if angle1 is within thresh degrees of angle2.  Everything in degrees.'''
    diff = angle1 - angle2
    diff = cap_angle_plus_minus_180_deg(diff)
    return abs(diff) < thresh

def orient_items(item1, item2, direction, thresh=45):
    '''Return item 1 and 2 as start_item , end_item specified by direction given in degrees.'''
    p1 = item1.position
    p2 = item2.position
    # Calculate angle from item1 to item2
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle =  math.degrees(math.atan2(dy, dx))
    if compare_angles(angle, direction, thresh):
        # item1 is the start item
        return item1, item2
    elif compare_angles(angle, -direction, thresh):
        # item2 is the start item
        return item2, item1
    else:
        print "Can't orient items with names {} and {}.  Angle {} is not within {} degrees of specified direction {}".format(item1.name, item2.name, angle, thresh, direction)
        return None, None
    
def lateral_and_projection_distance_2d(p, a, b):
    '''Return lateral error from position (p) to vector from points (a) to (b).'''
    a_to_b = (b[0] - a[0], b[1] - a[1])
    a_to_b_mag = sqrt(a_to_b[0]*a_to_b[0] + a_to_b[1]*a_to_b[1])
    
    if a_to_b_mag == 0.0:
        print "Warning: Vector from point a to b has zero magnitude. Returning NaN."
        return float('NaN')
    
    # Calculate position vector from a to p.
    a_to_p = (p[0] - a[0], p[1] - a[1])

    # Project a_to_p position vector onto a_to_b vector.
    a_to_b_traveled_mag = (a_to_p[0]*a_to_b[0] + a_to_p[1]*a_to_b[1]) / a_to_b_mag
    a_to_b_traveled = [0, 0]
    a_to_b_traveled[0] = a_to_b[0] * a_to_b_traveled_mag / a_to_b_mag
    a_to_b_traveled[1] = a_to_b[1] * a_to_b_traveled_mag / a_to_b_mag
    
    dx = a_to_p[0] - a_to_b_traveled[0]
    dy = a_to_p[1] - a_to_b_traveled[1]
    lateral_error_magnitude = sqrt(dx * dx + dy * dy)
    
    # Use cross product between path and position vector to find correct sign of lateral error.
    path_cross_position_z = a_to_b[0]*a_to_p[1] - a_to_b[1]*a_to_p[0]
    lateral_error_sign =  -1.0 if path_cross_position_z < 0.0 else 1.0
    
    lateral_error = lateral_error_sign * lateral_error_magnitude
    
    return lateral_error, a_to_b_traveled_mag
 
def export_results(items, rows, out_filepath):
    '''Write all items to results file.'''
    with open(out_filepath, 'wb') as out_file:
        writer = csv.writer(out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Write out header
        writer.writerow([
               'Type',
               'Name',
               'Entry',
               'Rep',
               '# In Field',
               '# In Row',
               'Direction',
               'Row',
               'Range',
               'E',
               'N',
               'U',
               'Easting',
               'Northing',
               'Altitude',
               'UTM-Zone',
               'Image Name',
               'Parent Image Name'])

        for item in items:
            
            has_group = hasattr(item, 'group') and item.group is not None
            
            #entry = item.group.entry if has_group else ''
            #rep = item.group.rep if has_group else ''
            entry = item.entry if hasattr(item, 'entry') else ''
            rep = item.rep if hasattr(item, 'rep') else ''

            # TODO cleanup 
            if hasattr(item, 'row_number'):
                item.row = item.row_number

            # Row properties
            row_direction = 'N/A'
            row = [row for row in rows if row.number == item.row]
            if len(row) > 0:
                row_direction = row[0].direction

            writer.writerow([
                           item.type,
                           item.name,
                           entry,
                           rep,
                           item.number_within_field,
                           item.number_within_row,
                           row_direction,
                           item.row,
                           item.range,
                           item.field_position[0],
                           item.field_position[1],
                           item.field_position[2],
                           item.position[0],
                           item.position[1],
                           item.position[2],
                           'TODO', # UTM-Zone
                           os.path.split(item.image_path)[1],
                           os.path.split(item.parent_image_filename)[1]])

    return out_filepath