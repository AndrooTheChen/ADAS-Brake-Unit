import socket
import time
import sys
import base64
from PIL import Image
import requests

def send_image_str_over_udp(sock, encoded_string):
    """Helper function to send a string that may be longer than one UDP packet over
        the network


        Arguments:
          sock - The UDP socket to use for sending
          encoded_string - The data to send
    """

    x = 0
    a = min(65000, len(encoded_string))

    while True:

        if x >= len(encoded_string):
            break

        sent = sock.sendall(encoded_string[x:x+a])

        x = x + a
        
        if x + a > len(encoded_string):
            a = len(encoded_string) - x


    # Send an empty string to denote the end of the message (think null-terminator in C)
    sent = sock.sendall(b'')



