def get_full_list_of_brains():
    return ['DK39', 'DK41', 'DK43', 'DK52', 'DK54', 'DK55','MD589']

def get_list_of_DK_brains():
    full_list = get_full_list_of_brains()
    DK_brians = [braini for braini in full_list if 'DK' in braini]
    return DK_brians

def get_list_of_brains_to_align():
    DK_brians = get_list_of_DK_brains()
    brians_to_align = [braini for braini in DK_brians if not 'DK52' in braini]
    return brians_to_align

def get_prep_list_for_rough_alignment_test():
    return ['DK39', 'DK41', 'DK43', 'DK54', 'DK55']