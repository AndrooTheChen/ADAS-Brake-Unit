import numpy as np
import tensorflow as tf
import cv2
import os
import json
import math
# tf.contrib.resampler

# To support bounding boxes with labels, we need to add the 
#   directory containing the Tensorflow models repo to the Python interpreter's path
# See README for more information
import sys
if os.environ.get('TENSORFLOW_MODELS_REPO_DIR', None):
  sys.path.append(os.path.join(os.environ['TENSORFLOW_MODELS_REPO_DIR'], "research"))
  sys.path.append(os.path.join(os.environ['TENSORFLOW_MODELS_REPO_DIR'], "research", "object_detection"))

  from utils import visualization_utils as tf_vis_utils


class ObjectRecognition:
    """Class to perform object recognition using pretrained Tensorflow models
    """

    def __init__(self, root_model_dir, model_name):
        """Initialize a new ObjectRecognition object

            Arguments:
                root_model_dir - The absolute filepath to the directory containing all the models
                model_name - The name of the model to use (and name of child directory directly under root_model_dir)
        """
        # All of the models should come from https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md
        #    (the link given in the CS 498 IoT lab handout)
        self.tf_graph = self._load_tensorflow_graph(root_model_dir, model_name)
        self.session = tf.Session(graph=self.tf_graph)

        self.coco_label_map = self._load_coco_labels()

        # Named tensors in the graph used to force computation in the graph
        # input image tensor
        self.image_tensor = self.tf_graph.get_tensor_by_name("image_tensor:0")
        # percentage-based bounding boxes for detected objects
        # As per: https://cloud.google.com/blog/products/gcp/performing-prediction-with-tensorflow-object-detection-models-on-google-cloud-machine-learning-engine
        #   The bounding box values are normalized to [0, 1) and are ordered ymin, xmin, ymax, xmax 
        self.boxes = self.tf_graph.get_tensor_by_name("detection_boxes:0")
        # classification scores for each detection (from 0 to 1)
        self.scores = self.tf_graph.get_tensor_by_name("detection_scores:0")
        # integer ids of the detected classes w.r.t COCO class labels
        self.classes = self.tf_graph.get_tensor_by_name("detection_classes:0")
        # number of non-zero score detections
        self.num_detections = self.tf_graph.get_tensor_by_name("num_detections:0")

    def _perform_inference(self, input_image):
        """Perform inference on a given image

            Arguments:
                input_image: A numpy array of the image. See detect_objects() for required array shape

            Returns:
                A tuple of the form (res_boxes, res_scores, res_classes, res_num_detections) where
                res_boxes - The bounding boxes of each detected object
                res_scores - The confidence scores of each detection
                res_classes - The class ids of the detected objects
                res_num_detections - The number of non-zero-confidence detections

                and all arrays are parallel (i.e. res_boxes[i], res_scores[i], res_classes[i] all
                    refer to the i'th detection) and detections are sorted in decreasing
                    score
        """
        # Use a batch size of just one image
        feed_dict = {
                self.image_tensor: np.expand_dims(input_image, axis=0)
        }

        # Actually perform inference
        # Note that the detection scores tensor is sorted by probability
        x = self.session.run(
                [self.boxes, self.scores, self.classes, self.num_detections],
                feed_dict=feed_dict
        )

        # Unpack the results of the inference
        res_boxes, res_scores, res_classes, res_num_detections = x
        # Use np.squeeze to remove single-dimensonal entries from the sahpe of the array
        res_boxes, res_scores, res_classes, res_num_detections = map(
                    np.squeeze,
                    [res_boxes, res_scores, res_classes, res_num_detections]
        )
        res_classes = res_classes.astype(int)
        res_num_detections = int(res_num_detections)
        return (res_boxes, res_scores, res_classes, res_num_detections)

    def detect_objects(self, input_image, score_threshold=0.2, boxes_with_labels=False):
        """Detect objects in a given image and draw bounding boxes on the detected objects

            Arguments:
                input_image - An RBG image as a numpy array of shape (vertical_resolution, horizontal_resolution, 3)
                    You may want to resize your image using cv2.resize to a smaller square resolution like 
                    (300x300) or (600x600) to increase speed of inference at some cost of worse accuracy
                score_threshold - The score threshold to use to filter out valid detections (from 0.0 to 1.0)
                boxes_with_labels - If True, use tensorflow visualization utilities to draw bounding boxes with
                    class labels and scores embedded within the image. If False, just draw bounding boxes with
                    no extra information embedded within the image

            Returns:
                A tuple of the form (annotated_image, valid_classes, valid_scores) where:

                annotated_image - A copy of input_image with bounding boxes drawn for each detected object
                valid_classes - The human readable class names of the detected objects (e.g. "tv", "stop_sign").
                    Note that classes in valid_classes may appear more than once
                valid_scores - The corresponding score given for each class in valid_classes (i.e.
                    valid_scores[i] is the score calculated for class valid_classes[i]).
        """
        # Actually perform the inference
        res_boxes, res_scores, res_classes, res_num_detections = self._perform_inference(input_image)


        # For each valid detected class, draw the bounding box on a copy of the input image
        valid_classes = []
        valid_scores = []
        annotated_image = input_image.copy()

        # Filter out classes as "detected" iff their score is above the specified threshold
        for idx in range(res_num_detections):
            detected_score = res_scores[idx]
            if detected_score < score_threshold:
                continue
                
            detected_class = self.coco_label_map[res_classes[idx]]

            valid_classes.append(detected_class)
            valid_scores.append(detected_score)


        if boxes_with_labels:
            self._draw_boxes_with_labels_tf(
                annotated_image,
                res_boxes,
                res_classes,
                res_scores,
                score_threshold
            )
        else:
            for idx in range(res_num_detections):
                self._draw_bounding_box(annotated_image, res_boxes[idx])



        return (annotated_image, valid_classes, valid_scores) 

    def _load_tensorflow_graph(self, root_model_dir, model_name):
        """Load the pretrained tensorflow graph from a .pb file on disk
        """
        # The frozen graph filename depends on the specific model used
        # frozen_graph_filename = os.path.join(ROOT_MODEL_DIR, MODEL_NAME, "tflite_graph.pb")
        frozen_graph_filename = os.path.join(root_model_dir, model_name, "frozen_inference_graph.pb")

        lab_graph = tf.Graph()
        with lab_graph.as_default():
            worker_graph_def = tf.GraphDef()
            with tf.gfile.GFile(frozen_graph_filename, 'rb') as graph_file:
                worker_graph_def.ParseFromString(graph_file.read())
                
            tf.import_graph_def(worker_graph_def, name='')

        return lab_graph

    def _load_coco_labels(self):
        """Return a dictionary mapping integers (class ids) to strings (human-readable class names like "stop_sign")
        """
        # This JSON was generated by parsing the .pbtxt for COCO models as specified in tensorflow.models Github repository
        coco_raw_json = """{"1": "person", "2": "bicycle", "3": "car", "4": "motorcycle", "5": "airplane", "6": "bus", "7": "train", "8": "truck", "9": "boat", "10": "traffic", "11": "fire", "13": "stop", "14": "parking", "15": "bench", "16": "bird", "17": "cat", "18": "dog", "19": "horse", "20": "sheep", "21": "cow", "22": "elephant", "23": "bear", "24": "zebra", "25": "giraffe", "27": "backpack", "28": "umbrella", "31": "handbag", "32": "tie", "33": "suitcase", "34": "frisbee", "35": "skis", "36": "snowboard", "37": "sports", "38": "kite", "39": "baseball", "40": "baseball", "41": "skateboard", "42": "surfboard", "43": "tennis", "44": "bottle", "46": "wine", "47": "cup", "48": "fork", "49": "knife", "50": "spoon", "51": "bowl", "52": "banana", "53": "apple", "54": "sandwich", "55": "orange", "56": "broccoli", "57": "carrot", "58": "hot", "59": "pizza", "60": "donut", "61": "cake", "62": "chair", "63": "couch", "64": "potted", "65": "bed", "67": "dining", "70": "toilet", "72": "tv", "73": "laptop", "74": "mouse", "75": "remote", "76": "keyboard", "77": "cell", "78": "microwave", "79": "oven", "80": "toaster", "81": "sink", "82": "refrigerator", "84": "book", "85": "clock", "86": "vase", "87": "scissors", "88": "teddy", "89": "hair", "90": "toothbrush"}"""
        coco_label_map = json.loads(coco_raw_json)
        coco_label_map = {int(k):v for (k,v) in coco_label_map.items()}
        return coco_label_map

    def _draw_bounding_box(self, image_arr, bounds):
        """Draw a bounding box on an image, using bounding boxes given by the Tensorflow model
	
            Arguments:
                  image_arr - The image we will draw the bounding box within (done in-place)
                  bounds - An array with 4 entries (first 2 are coordinates of first point of 
                      bounding box w.r.t. the Tensorflow model's output, last 2 are coordinates of
                      the second point of the bounding box)
            
        """
        width = image_arr.shape[0]
        height = image_arr.shape[1]

        pt1_x = math.floor(bounds[0] * width)
        pt1_y = math.floor(bounds[1] * height)
        
        pt2_x = math.floor(bounds[2] * width)
        pt2_y = math.floor(bounds[3] * height)
        
        
        # x and y are swapped from Tensorflow's bounds to opencv coordinates
        cv2.rectangle(image_arr, (pt1_y, pt1_x), (pt2_y, pt2_x), (255, 0, 0), thickness=2)

    def _draw_boxes_with_labels_tf(self, image, boxes, classes, scores, score_threshold):
        """Use Tensorflow's utility functions to draw detected objects with a bounding-box,
            class label, and score within the image (modified in place)

            Arguments:
                image - the image to annotate, modified in place
                boxes - See visualize_boxes_and_labels_on_image_array()
                classes - See visualize_boxes_and_labels_on_image_array()
                scores - See visualize_boxes_and_labels_on_image_array()
                score_threshold - Score threshold to use for visualization
        """
        category_index = {int(k):{'name': v, 'id': int(k)} for (k,v) in self.coco_label_map.items()}

        tf_vis_utils.visualize_boxes_and_labels_on_image_array(
            image,
            np.squeeze(boxes),
            np.squeeze(classes),
            np.squeeze(scores),
            category_index,
            line_thickness=4,
            use_normalized_coordinates=True,
            min_score_thresh=score_threshold
        )
                  
