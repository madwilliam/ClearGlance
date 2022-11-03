"""
This gets the CSV data of the 3 foundation brains' annotations.
These annotations were done by Lauren, Beth, Yuncong and Harvey
(i'm not positive about this)
The annotations are full scale vertices.
"""
import argparse
import json
import os
import sys
import cv2
import numpy as np
from tqdm import tqdm
from scipy.ndimage.measurements import center_of_mass
HOME = os.path.expanduser("~")
PATH = os.path.join(HOME, 'programming/pipeline_utility/src')
sys.path.append(PATH)
from pipeline.lib.FileLocationManager import DATA_PATH
from pipeline.utilities.utilities_atlas import ATLAS
from pipeline.Controllers.SqlController import SqlController

DOWNSAMPLE_FACTOR = 32

def save_volume_origin(atlas_name, animal, structure, volume, xyz_offsets):
    x, y, z = xyz_offsets
    xx = (x * DOWNSAMPLE_FACTOR) / (10/0.452)
    yy = (y * DOWNSAMPLE_FACTOR) / (10/0.452)

    volume = np.swapaxes(volume, 0, 2)
    volume = np.rot90(volume, axes=(0,1))
    volume = np.flip(volume, axis=0)

    OUTPUT_DIR = os.path.join(DATA_PATH, 'atlas_data', atlas_name, animal)
    volume_filepath = os.path.join(OUTPUT_DIR, 'structure', f'{structure}.npy')
    os.makedirs(os.path.join(OUTPUT_DIR, 'structure'), exist_ok=True)
    np.save(volume_filepath, volume)
    origin_filepath = os.path.join(OUTPUT_DIR, 'origin', f'{structure}.txt')
    os.makedirs(os.path.join(OUTPUT_DIR, 'origin'), exist_ok=True)
    np.savetxt(origin_filepath, (xx,yy,z))


def create_volumes(animal, debug):
    sqlController = SqlController(animal)
    CSVPATH = os.path.join(DATA_PATH, 'atlas_data', ATLAS, animal)
    jsonpath = os.path.join(CSVPATH,  'aligned_padded_structures.json')
    with open(jsonpath) as f:
        aligned_dict = json.load(f)
    structures = list(aligned_dict.keys())
    for structure in tqdm(structures):
        onestructure = aligned_dict[structure]
        mins = []
        maxs = []
        avgs = []

        for section_num, points in onestructure.items():
            lpoints = len(points)
            arr_tmp = np.array(points)
            min_tmp = np.min(arr_tmp, axis=0)
            max_tmp = np.max(arr_tmp, axis=0)
            mins.append(min_tmp)
            maxs.append(max_tmp)
            ss = [int(section_num) for s in range(lpoints)]
            avgarr = np.column_stack((arr_tmp, ss))
            com = np.mean(avgarr, axis=0)
            avgs.append(com)

        avgarr = np.array(avgs)
        com = np.mean(avgarr, axis=0)
        min_xy = np.min(mins, axis=0)
        min_x = min_xy[0]
        min_y = min_xy[1]
        max_xy = np.max(maxs, axis=0)
        max_x = max_xy[0]
        max_y = max_xy[1]
        xlength = max_x - min_x
        ylength = max_y - min_y
        sections = [int(i) for i in onestructure.keys()]
        zlength = (max(sections) - min(sections))
        padding = 1.0
        PADDED_SIZE = (int(ylength), int(xlength))
        volume = []
        for section, points in sorted(onestructure.items()):
            vertices = np.array(points) - np.array((min_x, min_y))
            volume_slice = np.zeros(PADDED_SIZE, dtype=np.uint8)
            points = (vertices).astype(np.int32)
            #color = sqlController.get_structure_color_rgb(structure)
            volume_slice = cv2.polylines(volume_slice, [points], isClosed=True, 
                                         color=1, thickness=1)
            cv2.fillPoly(volume_slice, pts=[points], color=1)

            volume.append(volume_slice)

        volume = np.array(volume).astype(np.bool8)
        to_um = 32 * 0.452
        ndcom = center_of_mass(volume)
        #x = round(ndcom[0] + min_x)
        #y = round(ndcom[1] + min_y)
        x = com[0]
        y = com[1]
        z = round(com[2])
        x_um  = x * to_um
        y_um = y * to_um
        z_um = z * 20
        if debug:
            print(animal, structure,'\tcom', '\tcom x y z', x_um, y_um, z_um)
        else:
            sqlController.add_layer_data(abbreviation=structure, animal=animal, 
                                     layer='COM', x=x_um, y=y_um, section=z_um, 
                                     person_id=1, input_type_id=3)
            save_volume_origin(ATLAS, animal, structure, volume, (x, y, z))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Work on Animal')
    parser.add_argument('--animal', help='Enter the animal', required=False)
    parser.add_argument('--debug', help='Enter debug True|False', required=False,
                         default='true')
    args = parser.parse_args()
    animal = args.animal
    debug = bool({'true': True, 'false': False}[str(args.debug).lower()])
    if animal is None:
        animals = ['MD585', 'MD589', 'MD594']
    else:
        animals = [animal]

    for animal in animals:
        create_volumes(animal, debug)
