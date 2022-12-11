from imutils.video import VideoStream
import cv2
import time
import f_detector
import imutils
import numpy as np

import pika
import io
import argparse
import json
import base64 
import sys
import os 

from PIL import Image

def stringToImage(base64_string):
    imgdata = base64.b64decode(base64_string)
    return np.array(Image.open(io.BytesIO(imgdata)))

def vantage_engine(argv):

    detector = f_detector.eye_blink_detector()

    COUNTER = 0
    TOTAL = 0

    # Set environment variables
    INPUTQ = os.getenv('INPUTQ')
    OUTPUTQ = os.getenv('OUTPUTQ')
    QUEUE_USERNAME = os.getenv('QUEUE_USERNAME')
    QUEUE_PASSWORD = os.getenv('QUEUE_PASSWORD')
    QUEUE_HOST = os.getenv('QUEUE_HOST')
    QUEUE_PORT = os.getenv('QUEUE_PORT')
    EXCHANGE_NAME = os.getenv('EXCHANGE_NAME')
    ENGINE_TYPE = os.getenv('ENGINE_TYPE')
    CHAINED_ENGINE = os.getenv('CHAINED_ENGINE')
    CHAINED_INPUT_TYPE = os.getenv('CHAINED_INPUT_TYPE')

    # engine specific inputs
    ENGINE_SETTING_1 = os.getenv('ENGINE_SETTING_1')


    # setup MQ connection
    credentials = pika.PlainCredentials(QUEUE_USERNAME,QUEUE_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(QUEUE_HOST, QUEUE_PORT, '/', credentials))

    # connect to input exchange and queue
    inputChannel = connection.channel()
    inputChannel.exchange_declare(exchange=EXCHANGE_NAME,exchange_type='fanout')
    inputChannel.queue_declare(queue=INPUTQ, passive=False,durable=True, exclusive=False, auto_delete=False)
    inputChannel.queue_bind(exchange=EXCHANGE_NAME,queue=INPUTQ)

    # connect to output queue
    outputChannel = connection.channel()
    outputChannel.queue_declare(OUTPUTQ)

    for method_frame, header_frame, body in inputChannel.consume(INPUTQ):

        # acknowledge delivery
        inputChannel.basic_ack(method_frame.delivery_tag)

        # convert input message to json object
        data = json.loads(body)

        # check if input frame exists
        if 'base64' in data:

            im = stringToImage(data['base64'])
            
            im = cv2.flip(im, 1)
            im = imutils.resize(im, width=720)
            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            # detectar_rostro    
            rectangles = detector.detector_faces(gray, 0)
            boxes_face = f_detector.convert_rectangles2array(rectangles,im)
            if len(boxes_face)!=0:
                # seleccionar el rostro con mas area
                areas = f_detector.get_areas(boxes_face)
                index = np.argmax(areas)
                rectangles = rectangles[index]

                COUNTER,TOTAL = detector.eye_blink(gray,rectangles,COUNTER,TOTAL)

                data_out = {'blinks':TOTAL}

                payload = json.dumps(data_out)
                print("publish result to output queue")
                outputChannel.basic_publish(exchange='',routing_key=OUTPUTQ, body=payload,
                                            properties=pika.BasicProperties(delivery_mode=2))

    return

if __name__ == "__main__":

    try:
        vantage_engine(sys.argv[1:])
    except KeyboardInterrupt:
        print("Receiver Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
