from utilities.brain_specimens.get_com import get_atlas_com_dict,get_manual_annotation_from_beth
from toolbox.IOs.get_landmark_lists import get_shared_landmarks_between_specimens
from toolbox.brain_lists import get_prep_list_for_rough_alignment_test
import numpy as np

def get_common_land_marks():
    prep_list = get_prep_list_for_rough_alignment_test()
    prep_list.append('DK52')
    common_landmarks = get_shared_landmarks_between_specimens(prep_list)
    return common_landmarks

def get_common_landmarks_between_dk52_and_atlas():
    common_landmarks = get_shared_landmarks_between_specimens(['Dk52','Atlas'])
    return common_landmarks

def get_common_com_from_dict(com_dict): 
    common_landmarks = get_common_land_marks()
    return np.array([com_dict[landmarki] for landmarki in common_landmarks])

def get_reference_com(prepi):
    reference_coms_dict = get_manual_annotation_from_beth(prepi)
    reference_com = get_common_com_from_dict(reference_coms_dict)
    return reference_com

def get_atlas_com():
    atlas_coms_dict = get_atlas_com_dict()
    atlas_com = get_common_com_from_dict(atlas_coms_dict)
    return atlas_com