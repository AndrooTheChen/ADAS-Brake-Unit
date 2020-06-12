import logging
import os

import numpy as np


class PiCameraWrapper:
  def capture_continuous(camera, post_capture_callback, array_resolution, format, logger):
    """Capture images from this PiCamera as fast as possible,
        invoking a specified callback after an image has been
        captured by the camera so the callback can manipulate 
        the image (represented by a numpy array)


        This is slightly more efficient than PiCameraWrapper.capture() since 
          we don't re-allocate memory for the numpy array on each iteration


       Arguments:
         camera - The PiCamera to perform continuous capture with
         post_capture_callback - A function that takes as its sole argument
            a numpy array (see array_resolution for this array's shape), with
            dtype=np.uint8
         array_resolution - a tuple of ints of the form
            (horizontal_resolution, vertical_resolution) to specify the y and x
            dimensions of the numpy array that will contain the captured image
            and what is passed to post_capture callback (the third dimension has
            length 3)

            Note that if camera.resolution
            is rounded by PiCamera when capturing, so if you have a non-standard
            camera.resolution, then array_resolution will need to be the rounded-up 
            version of camera.resolution (and the extra array entries will remain
            unitialized). See https://picamera.readthedocs.io/en/release-1.13/recipes2.html
            for information on rounding considerations
         format - Passed to picamera.capture_continuous() as the format argument
         logger - The logging.Logger to use for logging
    """

    horizontal_resolution, vertical_resolution = array_resolution

    capture_numpy_arr = np.empty((vertical_resolution, horizontal_resolution, 3), dtype=np.uint8)

    logger.info("Beginning capture")
    capture_count = 0

    for most_recent_img_filepath in camera.capture_continuous(capture_numpy_arr, format):
      capture_count += 1
      logger.info("Captured the {0}'th picture".format(capture_count))

      logger.info("Invoking callback")
      post_capture_callback(most_recent_img_filepath)
      logger.info("Callback completed")

      


   # Captures only one image and returns a numpy array with the shape defined
   #  in PiCameraWrapper.capture_continuous(). See that function for parameter definitions
  def capture(camera, array_resolution, format):
    horizontal_resolution, vertical_resolution = array_resolution
    capture_numpy_arr = np.empty((vertical_resolution, horizontal_resolution, 3), dtype=np.uint8)
    camera.capture(capture_numpy_arr, format)

    return capture_numpy_arr








    

