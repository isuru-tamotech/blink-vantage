import os  # nopep8
import platform
import sys  # nopep8
import time
import subprocess

import pika
import io
import argparse
import json
import base64 
import cv2
from PIL import Image

from progress.bar import Bar

sys.path.append(os.path.join(sys.path[0], ".."))  # nopep8
from python_prototype.GChannelExtractor.GChannelExtractor import GChannelExtractor
from python_prototype.utils.exception_decor import exception
from python_prototype.utils.exception_logger import logger
from python_prototype.luminance_meter.luminance import LuminanceMeter
from python_prototype.cppg_reconstruction.cppg_reconstructor import cPPGReconstructor
from python_prototype.waveform_analysis.waveform_analysis import WaveformAnalysis
from python_prototype.waveform_analysis.waveform_manager import WaveformManager
from python_prototype.GChannelExtractor.GChannelManager import GChannelManager
from python_prototype.face_tracking.face_tracking import FaceTracker
from python_prototype.session_manager.SessionManager import SessionManager
from python_prototype.utils.frame_providers import VideoFrameProvider, CameraFrameProvider, CameraFrameProviderThreaded, PickleFrameProvider, VideoMetaFrameProvider
from python_prototype.hrv.hrv_params import *
from python_prototype.respiration.respiration_rate_calculation import *
from python_prototype.green.green import *
from python_prototype.spo2.spo2_measurement import *
from python_prototype.utils.gather_data import DataGatherer
from python_prototype.ner_data_gathering.utils import load_config
from python_prototype.schema import *
from python_prototype.data_gethering.prepare_rppg_cppg import *
from python_prototype.data_gethering.clean import *


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

def stringToImage(base64_string):
    imgdata = base64.b64decode(base64_string)
    return np.array(Image.open(io.BytesIO(imgdata)))

@exception(logger, show_message=False)
def vantage_engine(face_detect_method, landmark_method, model_proto, detector_path, tracking_method, print_results, threshold,
                                extractor_definitions, config, cppg_models_path="./models/"):

    ppg_manager = GChannelManager(extractor_definitions)
    ppg_manager.threshold = threshold
    hr_calculator = GreenChannelHRCalculator()
    hr_calculator.set_threshold(threshold)
    br_calculator = RespirationRateCalculator()
    spo2_calculator = SpO2Calculator()
    hrv_calculator = HRVCalculator()
    waveform_manager = WaveformManager()
    cppg_reconstructor = cPPGReconstructor("dnn", cppg_models_path)
    luminance_meter = LuminanceMeter(method=LuminanceMeter.calculate_by_hsv)
    waveform_analysis = WaveformAnalysis(sample_r=-1, memory_len=15)

    face_tracker = FaceTracker(False, 0 ,fps=30, video_dir='.', record_videos=False, cover_eyes_mouth=False, tracking_method=tracking_method,
     detector_method=face_detect_method, landmark_method=landmark_method, proto_path=model_proto, detector_path=detector_path, landmarks_path=None, frame_scale=1, fourcc_format='',save_images=False)

    session_manager = SessionManager(face_tracker=face_tracker,
                                     hr_calculator=hr_calculator,
                                     br_calculator=br_calculator,
                                     hrv_calculator=hrv_calculator,
                                     spo2_calculator=spo2_calculator,
                                     ppg_manager=ppg_manager,
                                     luminance_meter=luminance_meter,
                                     waveform_manager=waveform_manager,
                                     cppg_reconstructor=cppg_reconstructor,
                                     waveform_analysis=waveform_analysis)


    session_manager.blink_counter_on()

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

    # consume from input queue
    count = 0
    blinks = 0
    first_timestamp = 0

    for method_frame, header_frame, body in inputChannel.consume(INPUTQ):

        # acknowledge delivery
        inputChannel.basic_ack(method_frame.delivery_tag)

        # convert input message to json object
        data = json.loads(body)

        # check if input frame exists
        if ('base64' in data) and ('timing' in data):

            frame = stringToImage(data['base64'])
            timestamp = data['timing']

            if first_timestamp == 0:
                first_timestamp = timestamp
            
            timestamp = timestamp - first_timestamp 
            
            session_manager.add_frame(frame, timestamp)
            count += 1

            blinks = session_manager.get_blinks()

            luminance_meter.calculate_luminance(frame)
            if count > 250:

                if count % 60 == 0:
                    results_to_print = session_manager.get_results()

                    if print_results: print(results_to_print)

                    data_out = {'hr':results_to_print.heart_rate, 'hq_hr':results_to_print.heart_rate_hq, 
                                'SNN':results_to_print.snn,'RMSSD':results_to_print.rmsdd,
                                'PNN50':results_to_print.pnn50,'RR':results_to_print.respiration_rate,'SpO2':results_to_print.spo2,'SpO2_hq':results_to_print.hq_spo2}

                    payload = json.dumps(data_out)
                    print("publish result to output queue")
                    outputChannel.basic_publish(exchange='',routing_key=OUTPUTQ, body=payload,
                                                    properties=pika.BasicProperties(delivery_mode=2))

    return 
    
@exception(logger, show_message=False, exit_script=False)
def config_and_compute(argv):

    print_results, threshold = True, 1.0

    dnn_proto_path = "models/dnn_model/deploy.prototxt"
    dnn_model_path = "models/dnn_model/res10_300x300_ssd_iter_140000.caffemodel"

    config = load_config('config.yaml')

    os.makedirs(config['project_path'] + config['videos_path'], exist_ok=True)

    os.makedirs(config['project_path'] + config['cppg_path'] + config['raw_signal'], exist_ok=True)
    os.makedirs(config['project_path'] + config['cppg_path'] + config['prepared_signal'], exist_ok=True)
    os.makedirs(config['project_path'] + config['rppg_path'] + config['prepared_signal'], exist_ok=True)

    roi_method = config['roi']

    if roi_method == 'all':
        regions = [Region.SMALL_FOREHEAD, Region.LEFT_CHEEK, Region.RIGHT_CHEEK, Region.ALL_SKIN]
    elif roi_method == 'fas':
        regions = [Region.SMALL_FOREHEAD, Region.ALL_SKIN]

    extractor_definitions = [(GChannelExtractor, region) for region in regions]


    face_detect_method = 'dnn'
    model_proto = dnn_proto_path
    detector_path = dnn_model_path

   
    face_landmark_method = 'ratio'
    tracking_method = 'lucas_kanade'

            
    vantage_engine(face_detect_method, face_landmark_method, model_proto, detector_path, tracking_method, print_results, threshold,
                                extractor_definitions, config)

    return


if __name__ == "__main__":

    try:
        config_and_compute(sys.argv[1:])
    except KeyboardInterrupt:
        print("Receiver Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

    
