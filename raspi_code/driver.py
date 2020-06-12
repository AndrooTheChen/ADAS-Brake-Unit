# Main script to continuously capture images from
#  the Pi's camera, run object recognition on it, 
#  and communicate with brake sensor and head unit
import logging
import math
import os
import socket
import threading
import time
from picamera import PiCamera
import cv2
import base64
import io
from PIL import Image

from picam_wrapper import PiCameraWrapper
from object_recognition import ObjectRecognition
from client_for_RaspPi import send_image_str_over_udp

# ================= INITIALIZATION ==========================

# Init logging
LOGGER_NAME = "LAB1_LOGGER"
LOG_FILE = "/tmp/lab1.log"

logger = logging.getLogger(LOGGER_NAME)

fh = logging.FileHandler(LOG_FILE)
log_formatter = logging.Formatter("%(asctime)s - %(message)s")
fh.setFormatter(log_formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


# Init Raspberry Pi's camera
# https://www.raspberrypi.org/documentation/hardware/camera/ for resolution/fps tradeoffs
# PiCamera crashed with 1080p
logger.info("Initializing camera")
format = 'rgb'
camera = PiCamera()
CAMERA_HORIZONTAL_RESOLUTION = 720
CAMERA_VERTICAL_RESOLUTION = 1280
camera.resolution = (CAMERA_VERTICAL_RESOLUTION, CAMERA_HORIZONTAL_RESOLUTION)

# See PiCameraWrapper.capture_continuous() for what "array resolution" is
CAPTURE_ARRAY_RESOLUTION = (CAMERA_VERTICAL_RESOLUTION, CAMERA_HORIZONTAL_RESOLUTION)

# Init object recognition

if os.environ.get('TENSORFLOW_MODELS_REPO_DIR', None) is None:
    logger.warn("""TENSORFLOW_MODELS_REPO_DIR environment variable is not defined.
        Set this variable to enable drawing bounding boxes with labels and scores
        embedded into the image""")


logger.info("Initializing ObjectRecognition object")
MODEL_ROOT_DIR = os.path.join(os.getcwd(), "models")
# Not using a quantized model at the moment since the quantized models 
#   now use Tensorflow Lite and there isn't a pretty binary to use 
#   for Tensorflow Lite on Pi (See Discord for more discussion)
MODEL_NAME = "ssdlite_mobilenet_v2_coco_2018_05_09"

# The minimum threshold to use for *detecting* objects. Note that this
#  is not necessarily the threshold used for determining to send
#  the brake signal or not
SCORE_THRESHOLD = 0.2
object_recognition_model = ObjectRecognition(MODEL_ROOT_DIR, MODEL_NAME)



# Callback for deciding whether or not to send the brake signal
# returns True if we decide to brake, false otherwise
def decide_to_brake(distance_cm, detected_classes, detected_classes_probs):

  if distance_cm < 15:
    return True
  else:
    return False




# Initialize Networking

# Socket for sending image data to the head unit (used in main thread)
HEAD_UNIT_IP_ADDR = '10.0.0.4'
head_unit_send_image_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
head_unit_send_image_socket.connect((HEAD_UNIT_IP_ADDR, 65432))



# Global variable that the thread listening to the Arduino socket
#   will write to
DISTANCE_IN_CM = -1.0
# Global variable for detected classes as strings
DETECTED_CLASSES = []
# Global variable for detectd classes' probabilities
DETECTED_CLASSES_PROBABILITIES = []



# Decode ascii string from socket for ultrasonic sensor
def decode_distance_data(binary_ascii_string):
  one_digit_char = binary_ascii_string[0]
  tens_digit_char = binary_ascii_string[1]
  hundreds_digit_char = binary_ascii_string[2]

  ones_digit = int(chr(one_digit_char))
  tens_digit = int(chr(tens_digit_char))
  hundreds_digit = int(chr(hundreds_digit_char))

  distance = (hundreds_digit*100) + (tens_digit*10) + ones_digit

  return distance


def send_brake_signal(brake_socket, turn_signal_on):
  """Send the appropriate UDP packet to turn on the brake LED

      Arguments:
        brake_socket: The socket to send the brake signal to
        turn_signal_on: If True, we tell the LED to turn on. If False, we tell the LED to turn off
  """

  packet_data = "RP0".encode()
  if turn_signal_on:
    packet_data = "RP1".encode()

  brake_socket.send(packet_data)


# Send the head unit an update with the distance
def send_head_unit_distance_update(head_unit_socket, distance, brake_signal):
  # update_message = (str(distance) + "@@@" + str(brak_signal)).encode()
  update_message = (str(distance)).encode()
  head_unit_socket.send(update_message)



def brake_receiver_worker():
  """Entry point for worker thread listening for the distance data

    This thread receives the brake distance data, decides if we want to break,
      then sends a signal to the LED brake to turn on or off

    Reads globals DISTANCE_IN_CM, DETECTED_CLASSES, and DETECTED_CLASSES_PROBABILITIES
  """

  global logger
  global DISTANCE_IN_CM

  # Init listener socket with brake Arduino (listening for distance)
  brake_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
  brake_listener_socket.bind(("", 9000))
  logger.info("Worker thread listening for distance data is running")

  # Init sender socket with brake Arudino (to send LED brake signal)
  ipaddr = "10.0.0.3"
  port = 8888
  brake_sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
  brake_sender_socket.connect((ipaddr, port))

  # Init socket for sending distance data to the head unit
  head_unit_send_distance_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  head_unit_send_distance_socket.connect((HEAD_UNIT_IP_ADDR, 9999))

  while True:
    received_data = brake_listener_socket.recvfrom(1024)

    # received_data is a tuple...first component is binary data, second component contains 
    #   information about the other host connected to this socket
    distance_ascii_string = received_data[0][0:3]
    DISTANCE_IN_CM = decode_distance_data(distance_ascii_string)

    # print("Received distance {0}".format(DISTANCE_IN_CM))

    # print(DETECTED_CLASSES_PROBABILITIES)
    if decide_to_brake(DISTANCE_IN_CM, DETECTED_CLASSES, DETECTED_CLASSES_PROBABILITIES):
      # print("Sending TRUE to brake")
      send_brake_signal(brake_sender_socket, True)
      send_head_unit_distance_update(head_unit_send_distance_socket, DISTANCE_IN_CM, True)
    else:
      # print("Sending FALSE to brake")
      send_brake_signal(brake_sender_socket, False)
      send_head_unit_distance_update(head_unit_send_distance_socket, DISTANCE_IN_CM, False)


  brake_listener_socket.close()
  brake_sender_socket.close()


# Start thread to receieve distance data from the brake module
logger.info("Starting brake receiver thread")
brake_receiver_thread = threading.Thread(target=brake_receiver_worker, args=())
brake_receiver_thread.start()


# ================= INITIALIZATION ==========================




# =================== CORE LOOP =============================

# Trying to perform inference on a high resolution image will take too long
#  and the models were trained on lower-resolution images like (300x300) or 
#  (600x600). So we will first resize the raw image captured from the 
#  camera to these dimensions before passing the resized image to the 
#  module that performs object recognition
RESIZED_HORIZONTAL_RESOLUTION = 300
RESIZED_VERTICAL_RESOLUTION = 300

# Not using PiCameraWrapper.capture_continuous() for demonstration purposes
#  and we may need finer control for multi-threading/networking purposes
logger.info("Starting continous camera capture")



while True:

    logger.info("Capturing image")
    raw_capture_arr = PiCameraWrapper.capture(
        camera,
        CAPTURE_ARRAY_RESOLUTION,
        format
    )

    resized_capture_arr = cv2.resize(
        raw_capture_arr,
        (RESIZED_HORIZONTAL_RESOLUTION, RESIZED_VERTICAL_RESOLUTION),
        interpolation=cv2.INTER_LINEAR
    )

    logger.info("Performing inference")

    annotated_image = resized_capture_arr

    # boxes_with_labels=False for just the bounding box
    # boxes_with_labels=True for bounding box with labels and scores embedded in image
    annotated_image, valid_classes, valid_scores = object_recognition_model.detect_objects(
            resized_capture_arr,
            SCORE_THRESHOLD,
            boxes_with_labels=True
    )

    DETECTED_CLASSES = valid_classes
    DETECTED_CLASSES_PROBABILITIES = valid_scores

    logger.info("Detected classes {0}".format(DETECTED_CLASSES))
    logger.info("Detected classes' probabilities {0}".format(DETECTED_CLASSES_PROBABILITIES))

    logger.info("We performed inference")


    im = Image.fromarray(annotated_image.astype('uint8'))
    raw_bytes = io.BytesIO()
    im.save(raw_bytes, "jpeg")
    raw_bytes.seek(0)
    buff = raw_bytes.read()
    encoded_str = base64.b64encode(buff) 
    send_image_str_over_udp(head_unit_send_image_socket, encoded_str)
    logger.info("Sent whole image")



logger.info("Stopped continous camera capture")
camera.close()


