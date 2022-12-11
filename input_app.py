# sample code for input-app.py
import pika
import sys
import os
import io
import argparse
import json
import base64
import time
INPUTQ = os.getenv('INPUTQ')
QUEUE_USERNAME = os.getenv('QUEUE_USERNAME')
QUEUE_PASSWORD = os.getenv('QUEUE_PASSWORD')
QUEUE_HOST = os.getenv('QUEUE_HOST')
QUEUE_PORT = os.getenv('QUEUE_PORT')

EXCHANGE_NAME = os.getenv('EXCHANGE_NAME')
TEST_IMAGE_DIR = "images/"

def main(argv):

    # setup MQ connection
    credentials = pika.PlainCredentials(QUEUE_USERNAME, QUEUE_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(QUEUE_HOST,QUEUE_PORT, '/', credentials))

    # connect to input exchange and queue
    inputChannel = connection.channel()
    inputChannel.exchange_declare(exchange=EXCHANGE_NAME,exchange_type='fanout')
    inputChannel.queue_declare(queue=INPUTQ, passive=False, durable=True, exclusive=False, auto_delete=False)
    inputChannel.queue_bind(exchange=EXCHANGE_NAME, queue=INPUTQ)

    for (dirpath, dirnames, filenames) in os.walk(TEST_IMAGE_DIR):
        for filename in filenames:
            with open(dirpath + filename, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                data = {
                    "base64": encoded_string.decode("utf-8"),
                    "timing": round(time.time(), 3)
                }
                print(round(time.time(), 3))
                payload = json.dumps(data)

                inputChannel.basic_publish(exchange=EXCHANGE_NAME,routing_key=INPUTQ, body=payload, properties=pika.BasicProperties(delivery_mode=2))
                time.sleep(1/25)
        break

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print("Receiver Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)