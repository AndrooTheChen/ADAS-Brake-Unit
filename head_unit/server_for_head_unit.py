#!/usr/bin/env python3

import socket
import sys
import base64
import time
import threading

last_rcv_msg = 'NO IMAGE YET'
last_rcv_dist = -1

# Updates global variable last_rcv_msg to the given parameter
def update_rcv_msg(new_msg):
    global last_rcv_msg
    last_rcv_msg = new_msg

# Returns whatever variable is currently stored in last_rcv_msg
def get_rcv_msg():
    global last_rcv_msg
    return last_rcv_msg

# Updates global variable last_rcv_dist to the given parameter
def update_rcv_dist(new_dist):
    global last_rcv_dist
    last_rcv_dist = new_dist

# Returns whatever variable is currently stored in last_rcv_dist
def get_rcv_dist():
    global last_rcv_dist
    return last_rcv_dist

# Worker thread to constantly polling socket for image
def rcv_image_worker(): 
    PORT = 65432

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    s.bind(('', PORT))


    x = 0

    while True:

        mess = ""
            
        while True:
            print('\nwaiting to receive message')
                
            data, address = s.recvfrom(72000)

            print("GOT IMAGE DATA YO")

            
            # The sending socket will sent an empty string to mark the end of the image
            if len(data) != 0:
                mess = mess + str(data.decode("ASCII"))
            else:
                break

        # padding to make sure whole message is a multiple of 4 (valid base64 string)
        mess += "=" * ((4 - len(mess) % 4) % 4)


        # UPDATE GLOBAL
        update_rcv_msg(mess)

    # close socket
    s.close()


# Worker thread to constantly poll socket for distance
def rcv_dist_worker(): 
    DIST_PORT = 9999
    
    dist_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    dist_server.bind(('', DIST_PORT))

    while True:
        # poll for distance data
        dist = dist_server.recvfrom(1024)[0]
        print("GOT DISTANCE DATA YO")
        update_rcv_dist(dist)

    # close distance polling socket
    dist_server.close()

# initialize threads
image_receiver_thread = threading.Thread(target = rcv_image_worker, args = ())
dist_receiver_thread = threading.Thread(target = rcv_dist_worker, args = ())

# start listener threads to receive image and distance
image_receiver_thread.start()
dist_receiver_thread.start()

