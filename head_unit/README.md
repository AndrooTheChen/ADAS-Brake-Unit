# Running The Head Unit

1. Set the static IP address of the device acting as the head unit to 10.0.0.4/24

2. Install Flask http://flask.pocoo.org/ and Flask-CORS https://flask-cors.readthedocs.io/en/latest/ for your preferred Python interpreter (or virtual environment)

3. Run `python app.py` inside a terminal

4. Start the Raspberry Pi following the instructions in the `raspi_code` folder if you have not already

4. Open up a web browser and set the URL to "http://localhost:8080/head-unit". If everything is set up correctly, you should start seeing updates to both the detected distance and annotated images that are coming from the Raspberry Pi. Note that the web browser initially needs Internet access to download JQuery from a CDN, but once that is cached you don't require Internet access to receive updates from the Raspberry Pi
