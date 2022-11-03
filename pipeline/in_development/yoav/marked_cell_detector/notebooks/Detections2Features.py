import sys
import numpy as np
import pickle as pkl
import cv2

if __name__=='__main__':
    DATA_DIR =sys.argv[1]

DATA_DIR='/Users/yoavfreund/projects/butons/data/164'
print('DATA_DIR=%s'%(DATA_DIR))

with open(DATA_DIR+'/extracted_cells.pkl','br') as pkl_file:
    E=pkl.load(pkl_file)
    Examples=E['Examples']

df_dict=None
thresh=2000
for i in range(len(Examples)):
    e=Examples[i]

    Stats=cv2.connectedComponentsWithStats(np.int8(e['image']>thresh))

    if Stats[1] is None:
        continue
    seg=Stats[1]

    # Isolate the connected component at the middle of seg
    middle=np.array(np.array(seg.shape)/2,dtype=np.int16)
    middle_seg=seg[middle[0],middle[1]]
    middle_seg_mask = np.uint8(seg==middle_seg)

    # Calculate Moments
    moments = cv2.moments(middle_seg_mask)
    # Calculate Hu Moments
    huMoments = cv2.HuMoments(moments)

    features={'h%d'%i:huMoments[i,0]  for i in range(7)}
    features.update(moments)

    for key in ['animal','section','index','label','area','height2','width2']:
        features[key]=e[key]

    features['row']=e['row_center']+e['origin'][0]
    features['col']=e['col_center']+e['origin'][0]

    if df_dict==None:
        df_dict={}
        for key in features:
            df_dict[key]=[]

    for key in features:
        df_dict[key].append(features[key])


import pandas as pd
df=pd.DataFrame(df_dict)
outfile=DATA_DIR+'/puntas.csv'
print('df shape=',df.shape,'output_file=',outfile)

df.to_csv(outfile)
