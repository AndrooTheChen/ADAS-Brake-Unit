# Running The ADAS on a Raspberry Pi

1. Use pip to install tensorflow, opencv, and pillow for the Python interpreter of the Pi

2. Connect the camera module to the Pi and make sure the camera is enabled (`raspi_config`)

3. Set the IP address of the Pi to 10.0.0.2/24

4. To draw the bounding boxes with labels and scores on detected objects, we use a utility function from the Tensorflow models repository: https://github.com/tensorflow/models  You'll need to clone this repository and export the directory you cloned the repo to as the environment variable TENSORFLOW_MODELS_REPO_DIR. On our Pi, the models repo is stored at /home/pi/Workspace/models, so we would run `export TENSORFLOW_MODELS_REPO_DIR=/home/pi/Workspace/models`

5. To start the ADAS, run `python3 driver.py`. Note you'll have to start the head unit first before running driver.py. It takes a couple seconds to load in the Tensorflow graph and perform inference on the first image, but after the first image the images are processed at around 1FPS. You can monitor the progress of the ADAS by looking at the logs at /tmp/lab1.log (such as with the command `tail -F /tmp/lab1.log`)

