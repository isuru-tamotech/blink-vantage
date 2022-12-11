# sample code for output-app.py
import pika
import sys
import os
import io
import argparse
import json

OUTPUTQ = os.getenv('OUTPUTQ')
QUEUE_USERNAME = os.getenv('QUEUE_USERNAME')
QUEUE_PASSWORD = os.getenv('QUEUE_PASSWORD')
QUEUE_HOST = os.getenv('QUEUE_HOST')
QUEUE_PORT = os.getenv('QUEUE_PORT')

def main(argv):

    # setup MQ connection
    credentials = pika.PlainCredentials(QUEUE_USERNAME,
    QUEUE_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(QUEUE_HOST, QUEUE_PORT, '/', credentials))

    # connect to output queue
    outputChannel = connection.channel()
    outputChannel.queue_declare(OUTPUTQ)
    for method_frame, header_frame, body in outputChannel.consume(OUTPUTQ):
        # acknowledge delivery
        outputChannel.basic_ack(method_frame.delivery_tag)
        # convert results message to json object
        data = json.loads(body)
        # print out results for verification
        print(data)

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print("Receiver Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)