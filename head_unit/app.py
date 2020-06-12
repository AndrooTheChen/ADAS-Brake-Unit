from flask import Flask, jsonify
from flask import send_file, render_template
from flask_cors import CORS

from server_for_head_unit import get_rcv_msg, get_rcv_dist

app = Flask(__name__)
CORS(app)


@app.route('/data/image', methods=['GET'])
def send_most_recent_image_data():
    base64_str = get_rcv_msg()
    return base64_str

@app.route('/data/brake', methods=['GET'])
def send_most_recent_brake_data():

    result = get_rcv_dist()
    distance = int(result)

    print(distance)
    fake_signal_is_on = True

    data_dict = {
        'distance': distance,
        'signal_on': fake_signal_is_on
    }

    return jsonify(data_dict)


@app.route('/head-unit', methods=['GET'])
def send_head_unit_page():
    return render_template('head_unit.html')


app.run(port=8080)


