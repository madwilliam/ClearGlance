import os
import cv2
import sys
import numpy as np
from skimage import io
from utilities.utilities_mask import equalized

class Normalizer:
    def create_normalized_image(self):
        """Normalize the downsampled images with QC applied"""
        if self.channel == 1 and self.downsample:
            INPUT = self.fileLocationManager.thumbnail
            OUTPUT = self.fileLocationManager.get_normalized(self.channel)
            self.logevent(f"INPUT FOLDER: {INPUT}")
            files = sorted(os.listdir(INPUT))
            self.logevent(f"CURRENT FILE COUNT: {len(files)}")
            self.logevent(f"OUTPUT FOLDER: {OUTPUT}")
            os.makedirs(OUTPUT, exist_ok=True)

            for file in files:
                infile = os.path.join(INPUT, file)
                outpath = os.path.join(OUTPUT, file)
                if os.path.exists(outpath):
                    continue
                try:
                    img = io.imread(infile)
                except IOError as errno:
                    print(f"I/O error {errno}")
                except ValueError:
                    print("Could not convert data to an integer.")
                except:
                    print(f' Could not open {infile}')
                    print("Unexpected error:", sys.exc_info()[0])
                    sys.exit()


                if img.dtype == np.uint16:
                    img = (img / 256).astype(np.uint8)
                fixed = equalized(img)
                cv2.imwrite(outpath, fixed.astype(np.uint8))
