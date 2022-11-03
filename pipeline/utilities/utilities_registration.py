"""

 #Notes from the manual regarding MOMENTS vs GEOMETRY:

 The CenteredTransformInitializer supports two modes of operation. In the first mode, the centers of
 the images are computed as space coordinates using the image origin, size and spacing. The center of
 the fixed image is assigned as the rotational center of the transform while the vector going from the
 fixed image center to the moving image center is passed as the initial translation of the transform.
 In the second mode, the image centers are not computed geometrically but by using the moments of the
 intensity gray levels.

 Keep in mind that the scale of units in rotation and translation is quite different. For example, here
 we know that the first element of the parameters array corresponds to the angle that is measured in radians,
 while the other parameters correspond to the translations that are measured in millimeters

"""

import os
import numpy as np
from matplotlib import pyplot as plt
import SimpleITK as sitk
from IPython.display import clear_output
import cv2
from scipy.stats import skew
from scipy.ndimage import affine_transform

ITERATIONS = "2000"




def parameters_to_rigid_transform(rotation, xshift, yshift, center):
    rotation, xshift, yshift = np.array([rotation, xshift, yshift]).astype(
        np.float16
    )
    center = np.array(center).astype(np.float16)
    R = np.array(
        [
            [np.cos(rotation), -np.sin(rotation)],
            [np.sin(rotation), np.cos(rotation)],
        ]
    )
    shift = center + (xshift, yshift) - np.dot(R, center)
    T = np.vstack([np.column_stack([R, shift]), [0, 0, 1]])
    return T

def rigid_transform_to_parmeters(transform,center):
    """convert a 2d transformation matrix (3*3) to the rotation angles, rotation center and translation

    Args:
        transform (array like): 3*3 array that stores the 2*2 transformation matrix and the 1*2 translation vector for a 
        2D image.  the third row of the array is a place holder of values [0,0,1].

    Returns:
        float: x translation
        float: y translation
        float: rotation angle in arc
        list:  lisf of x and y for rotation center
    """        
    R = transform[:2,:2]
    shift = transform[:2,2]
    tan= R[1,0]/R[0,0]
    rotation = np.arctan(tan)
    xshift,yshift = shift-center +np.dot(R, center)
    return xshift,yshift,rotation,center

def create_matrix(final_transform):
    finalParameters = final_transform.GetParameters()
    fixedParameters = final_transform.GetFixedParameters()
    # print(finalParameters)
    # print(fixedParameters)
    # return
    rot_rad, xshift, yshift = finalParameters
    center = np.array(fixedParameters)

    R = np.array(
        [
            [np.cos(rot_rad), -np.sin(rot_rad)],
            [np.sin(rot_rad), np.cos(rot_rad)],
        ]
    )
    shift = center + (xshift, yshift) - np.dot(R, center)
    T = np.vstack([np.column_stack([R, shift]), [0, 0, 1]])
    return T

def convert_2d_transform_forms(arr):
    """
    Just creates correct size matrix
    """
    return np.vstack([arr, [0, 0, 1]])


def start_plot():
    global metric_values, multires_iterations
    metric_values = []
    multires_iterations = []


# Callback invoked when the EndEvent happens, do cleanup of data and figure.
def end_plot():
    global metric_values, multires_iterations
    del metric_values
    del multires_iterations
    # Close figure, we don't want to get a duplicate of the plot latter on.
    plt.close()


# Callback invoked when the sitkMultiResolutionIterationEvent happens, update the index into the
# metric_values list.
def update_multires_iterations():
    global metric_values, multires_iterations
    multires_iterations.append(len(metric_values))


# Callback invoked when the IterationEvent happens, update our data and display new figure.
def plot_values(registration_method):
    global metric_values, multires_iterations

    metric_values.append(registration_method.GetMetricValue())
    # Clear the output area (wait=True, to reduce flickering), and plot current data
    clear_output(wait=True)
    # Plot the similarity metric values
    plt.plot(metric_values, "r")
    plt.plot(
        multires_iterations,
        [metric_values[index] for index in multires_iterations],
        "b*",
    )
    plt.xlabel("Iteration Number", fontsize=12)
    plt.ylabel("Metric Value", fontsize=12)
    plt.show()


def command_iteration(method):
    print(
        "{0:3} = {1:10.5f} : {2}".format(
            method.GetOptimizerIteration(),
            method.GetMetricValue(),
            method.GetOptimizerPosition(),
        )
    )


def register_test(INPUT, fixed_index, moving_index):
    pixelType = sitk.sitkFloat32
    fixed_file = os.path.join(INPUT, f"{fixed_index}.tif")
    moving_file = os.path.join(INPUT, f"{moving_index}.tif")
    fixed = sitk.ReadImage(fixed_file, pixelType)
    moving = sitk.ReadImage(moving_file, pixelType)

    initial_transform = sitk.CenteredTransformInitializer(
        fixed,
        moving,
        sitk.Euler2DTransform(),
        sitk.CenteredTransformInitializerFilter.MOMENTS,
    )

    R = sitk.ImageRegistrationMethod()
    R.SetInitialTransform(initial_transform, inPlace=True)
    R.SetMetricAsCorrelation()  # -0439
    # R.SetMetricAsMeanSquares()
    # R.SetMetricAsMattesMutualInformation()
    R.SetMetricSamplingStrategy(R.REGULAR)  # random = 0.442 # regular -0.439
    R.SetMetricSamplingPercentage(0.2)
    R.SetInterpolator(sitk.sitkLinear)
    # Optimizer settings.
    R.SetOptimizerAsRegularStepGradientDescent(
        learningRate=1,
        minStep=1e-4,
        numberOfIterations=100,
        gradientMagnitudeTolerance=1e-8,
    )
    R.SetOptimizerScalesFromPhysicalShift()

    # Connect all of the observers so that we can perform plotting during registration.
    R.AddCommand(sitk.sitkStartEvent, start_plot)
    R.AddCommand(sitk.sitkEndEvent, end_plot)
    R.AddCommand(
        sitk.sitkMultiResolutionIterationEvent, update_multires_iterations
    )
    R.AddCommand(sitk.sitkIterationEvent, lambda: plot_values(R))

    final_transform = R.Execute(
        sitk.Cast(fixed, sitk.sitkFloat32), sitk.Cast(moving, sitk.sitkFloat32)
    )

    return final_transform, fixed, moving, R


def resample(image, transform):
    # Output image Origin, Spacing, Size, Direction are taken from the reference
    # image in this call to Resample
    reference_image = image
    interpolator = sitk.sitkCosineWindowedSinc
    default_value = 100.0
    return sitk.Resample(
        image, reference_image, transform, interpolator, default_value
    )


def find_principle_vector(mask):
    moments = cv2.moments(mask)
    x = moments["m10"] / moments["m00"]
    y = moments["m01"] / moments["m00"]
    u20 = moments["m20"] / moments["m00"] - x**2
    u11 = moments["m11"] / moments["m00"] - x * y
    u02 = moments["m02"] / moments["m00"] - y**2
    theta = 0.5 * np.arctan(2 * u11 / (u20 - u02)) + (u20 < u02) * np.pi / 2
    x = moments["m10"] / moments["m00"]
    y = moments["m01"] / moments["m00"]
    center = np.array([x, y]).astype(int)
    return theta, center


def find_skewness_along_X(image):
    inds = np.argwhere(image > np.mean(image))
    return skew(inds[:, 1])


def rotate_and_align_image(moving, fixed):
    moving_mask = np.array((np.array(moving) > np.mean(moving)) * 255).astype(
        "uint8"
    )
    fixed_mask = np.array((np.array(fixed) > np.mean(fixed)) * 255).astype(
        "uint8"
    )
    theta_moving, center_moving = find_principle_vector(moving_mask)
    theta_fixed, center_fixed = find_principle_vector(fixed_mask)
    T = parameters_to_rigid_transform(
        rotation=-theta_moving,
        xshift=0,
        yshift=0,
        center=np.flip(center_moving),
    )
    straight_moving = affine_transform(moving, T)
    T = parameters_to_rigid_transform(
        rotation=-theta_fixed, xshift=0, yshift=0, center=np.flip(center_fixed)
    )
    straight_fixed = affine_transform(fixed, T)
    skewness_moving = find_skewness_along_X(straight_moving)
    skewness_fixed = find_skewness_along_X(straight_fixed)
    if np.sign(skewness_fixed) != np.sign(skewness_moving):
        theta_moving = (theta_moving + np.pi) % (2 * np.pi)
    rotation_angle = theta_fixed - theta_moving
    offset = center_fixed - center_moving
    rotation_angle = (theta_fixed - theta_moving) % (2 * np.pi)
    return rotation_angle, np.flip(offset), np.flip(center_moving)

def align_elastix(fixed, moving, moving_index, tries=10):
    for _ in range(tries):
        try:
            elastixImageFilter = sitk.ElastixImageFilter()
            elastixImageFilter.SetFixedImage(fixed)
            elastixImageFilter.SetMovingImage(moving)
            rigid_params = elastixImageFilter.GetDefaultParameterMap("rigid")

            rigid_params["AutomaticTransformInitializationMethod"] = [
                "GeometricalCenter"
            ]
            rigid_params["ShowExactMetricValue"] = ["false"]
            rigid_params["CheckNumberOfSamples"] = ["true"]
            rigid_params["NumberOfSpatialSamples"] = ["5000"]
            rigid_params["SubtractMean"] = ["true"]
            rigid_params["MaximumNumberOfSamplingAttempts"] = ["0"]
            rigid_params["SigmoidInitialTime"] = ["0"]
            rigid_params["MaxBandCovSize"] = ["192"]
            rigid_params["NumberOfBandStructureSamples"] = ["10"]
            rigid_params["UseAdaptiveStepSizes"] = ["true"]
            rigid_params["AutomaticParameterEstimation"] = ["true"]
            rigid_params["MaximumStepLength"] = ["10"]
            rigid_params["NumberOfGradientMeasurements"] = ["0"]
            rigid_params["NumberOfJacobianMeasurements"] = ["1000"]
            rigid_params["NumberOfSamplesForExactGradient"] = ["100000"]
            rigid_params["SigmoidScaleFactor"] = ["0.1"]
            rigid_params["ASGDParameterEstimationMethod"] = ["Original"]
            rigid_params["UseMultiThreadingForMetrics"] = ["true"]
            rigid_params["SP_A"] = ["20"]
            rigid_params["UseConstantStep"] = ["false"]
            ## The internal pixel type, used for internal computations
            ## Leave to float in general.
            ## NB: this is not the type of the input images! The pixel
            ## type of the input images is automatically read from the
            ## images themselves.
            ## This setting can be changed to "short" to save some memory
            ## in case of very large 3D images.
            rigid_params["FixedInternalImagePixelType"] = ["float"]
            rigid_params["MovingInternalImagePixelType"] = ["float"]
            ## note that some other settings may have to specified
            ## for each dimension separately.
            rigid_params["FixedImageDimension"] = ["2"]
            rigid_params["MovingImageDimension"] = ["2"]
            ## Specify whether you want to take into account the so-called
            ## direction cosines of the images. Recommended: true.
            ## In some cases, the direction cosines of the image are corrupt,
            ## due to image format conversions for example. In that case, you
            ## may want to set this option to "false".
            rigid_params["UseDirectionCosines"] = ["true"]
            ## **************** Main Components **************************
            ## The following components should usually be left as they are:
            rigid_params["Registration"] = ["MultiResolutionRegistration"]
            rigid_params["Interpolator"] = ["BSplineInterpolator"]
            rigid_params["ResampleInterpolator"] = ["FinalBSplineInterpolator"]
            rigid_params["Resampler"] = ["DefaultResampler"]
            ## These may be changed to Fixed/MovingSmoothingImagePyramid.
            ## See the manual.
            ##(FixedImagePyramid "FixedRecursiveImagePyramid']
            ##(MovingImagePyramid "MovingRecursiveImagePyramid']
            rigid_params["FixedImagePyramid"] = ["FixedSmoothingImagePyramid"]
            rigid_params["MovingImagePyramid"] = [
                "MovingSmoothingImagePyramid"
            ]
            ## The following components are most important:
            ## The optimizer AdaptiveStochasticGradientDescent (ASGD) works
            ## quite ok in general. The Transform and Metric are important
            ## and need to be chosen careful for each application. See manual.
            rigid_params["Optimizer"] = ["AdaptiveStochasticGradientDescent"]
            rigid_params["Transform"] = ["EulerTransform"]
            ##(Metric "AdvancedMattesMutualInformation")
            ## testing 17 dec
            rigid_params["Metric"] = ["AdvancedNormalizedCorrelation"]
            ## ***************** Transformation **************************
            ## Scales the rotations compared to the translations, to make
            ## sure they are in the same range. In general, it's best to
            ## use automatic scales estimation:
            rigid_params["AutomaticScalesEstimation"] = ["true"]
            ## Automatically guess an initial translation by aligning the
            ## geometric centers of the fixed and moving.
            rigid_params["AutomaticTransformInitialization"] = ["true"]
            ## Whether transforms are combined by composition or by addition.
            ## In generally, Compose is the best option in most cases.
            ## It does not influence the results very much.
            rigid_params["HowToCombineTransforms"] = ["Compose"]
            ## ******************* Similarity measure *********************
            ## Number of grey level bins in each resolution level,
            ## for the mutual information. 16 or 32 usually works fine.
            ## You could also employ a hierarchical strategy:
            ##(NumberOfHistogramBins 16 32 64)
            rigid_params["NumberOfHistogramBins"] = ["32"]
            ## If you use a mask, this option is important.
            ## If the mask serves as region of interest, set it to false.
            ## If the mask indicates which pixels are valid, then set it to true.
            ## If you do not use a mask, the option doesn't matter.
            rigid_params["ErodeMask"] = ["false"]
            ## ******************** Multiresolution **********************
            ## The number of resolutions. 1 Is only enough if the expected
            ## deformations are small. 3 or 4 mostly works fine. For large
            ## images and large deformations, 5 or 6 may even be useful.
            rigid_params["NumberOfResolutions"] = ["6"]
            ##(FinalGridSpacingInVoxels 8.0 8.0)
            ##(GridSpacingSchedule 6.0 6.0 4.0 4.0 2.5 2.5 1.0 1.0)
            ## The downsampling/blurring factors for the image pyramids.
            ## By default, the images are downsampled by a factor of 2
            ## compared to the next resolution.
            ## So, in 2D, with 4 resolutions, the following schedule is used:
            ##(ImagePyramidSchedule 4 4  2 2  1 1 )
            ## And in 3D:
            ##(ImagePyramidSchedule 8 8 8  4 4 4  2 2 2  1 1 1 )
            ## You can specify any schedule, for example:
            ##(ImagePyramidSchedule 4 4  4 3  2 1  1 1 )
            ## Make sure that the number of elements equals the number
            ## of resolutions times the image dimension.
            ## ******************* Optimizer ****************************
            ## Maximum number of iterations in each resolution level:
            ## 200-500 works usually fine for rigid registration.
            ## For more robustness, you may increase this to 1000-2000.
            ## 80 good results, 7 minutes on basalis with 4 jobs
            ## 200 good results except for 1st couple were not aligned, 12 minutes
            ## 500 is best, including first sections, basalis took 21 minutes
            rigid_params["MaximumNumberOfIterations"] = [ITERATIONS]
            ## The step size of the optimizer, in mm. By default the voxel size is used.
            ## which usually works well. In case of unusual high-resolution images
            ## (eg histology) it is necessary to increase this value a bit, to the size
            ## of the "smallest visible structure" in the image:
            ##(MaximumStepLength 4)
            ## **************** Image sampling **********************
            ## Number of spatial samples used to compute the mutual
            ## information (and its derivative) in each iteration.
            ## With an AdaptiveStochasticGradientDescent optimizer,
            ## in combination with the two options below, around 2000
            ## samples may already suffice.
            ##(NumberOfSpatialSamples 2048)
            ## Refresh these spatial samples in every iteration, and select
            ## them randomly. See the manual for information on other sampling
            ## strategies.
            rigid_params["NewSamplesEveryIteration"] = ["true"]
            rigid_params["ImageSampler"] = ["Random"]
            ## ************* Interpolation and Resampling ****************
            ## Order of B-Spline interpolation used during registration/optimisation.
            ## It may improve accuracy if you set this to 3. Never use 0.
            ## An order of 1 gives linear interpolation. This is in most
            ## applications a good choice.
            rigid_params["BSplineInterpolationOrder"] = ["1"]
            ## Order of B-Spline interpolation used for applying the final
            ## deformation.
            ## 3 gives good accuracy; recommended in most cases.
            ## 1 gives worse accuracy (linear interpolation)
            ## 0 gives worst accuracy, but is appropriate for binary images
            ## (masks, segmentations); equivalent to nearest neighbor interpolation.
            rigid_params["FinalBSplineInterpolationOrder"] = ["3"]
            ##Default pixel value for pixels that come from outside the picture:
            rigid_params["DefaultPixelValue"] = ["0"]
            ## Choose whether to generate the deformed moving image.
            ## You can save some time by setting this to false, if you are
            ## only interested in the final (nonrigidly) deformed moving image
            ## for example.
            rigid_params["WriteResultImage"] = ["false"]
            ## The pixel type and format of the resulting deformed moving image
            rigid_params["ResultImagePixelType"] = ["unsigned char"]
            rigid_params["ResultImageFormat"] = ["tif"]
            rigid_params["RequiredRatioOfValidSamples"] = ["0.05"]
            elastixImageFilter.SetParameterMap(rigid_params)
            elastixImageFilter.LogToConsoleOff()
        except RuntimeError:
            continue
        break
    elastixImageFilter.Execute()
    
    return (elastixImageFilter.GetTransformParameterMap()[0]["TransformParameters"])



def align_principle_axis(moving,fixed):
    rotation_angle,offset,center_moving = rotate_and_align_image(sitk.GetArrayFromImage(moving),sitk.GetArrayFromImage(fixed))
    initial_transform = sitk.Euler2DTransform()
    initial_transform.SetParameters([rotation_angle,*offset.astype(float)])
    initial_transform.SetFixedParameters(center_moving.astype(float))
    moving = resample(moving,initial_transform)
    initial_transform = parse_sitk_rigid_transform(initial_transform)
    return moving,initial_transform


def register_simple(INPUT, fixed_index, moving_index, debug=False):
    pixelType = sitk.sitkFloat32
    fixed_file = os.path.join(INPUT, f"{fixed_index}.tif")
    moving_file = os.path.join(INPUT, f"{moving_index}.tif")
    fixed = sitk.ReadImage(fixed_file, pixelType)
    moving = sitk.ReadImage(moving_file, pixelType)
    initial_transform = sitk.Euler2DTransform()
    initial_transform = parse_sitk_rigid_transform(initial_transform)
    # moving,initial_transform = align_principle_axis(moving,fixed)
    elastix_transform = align_elastix(fixed, moving, moving_index)
    return (elastix_transform,initial_transform)

def parse_sitk_rigid_transform(sitk_rigid_transform):
    rotation, xshift, yshift = sitk_rigid_transform.GetParameters()
    center = sitk_rigid_transform.GetFixedParameters()
    return rotation, xshift, yshift, center
