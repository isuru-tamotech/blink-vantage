# set the base image (host OS)
FROM python:3.8
# set the working directory in the container
WORKDIR /eye_blink_detection
# copy the dependencies file to the working directory
COPY . /eye_blink_detection/
# install the dependencies
RUN pip install -U pip wheel cmake
RUN pip install -r requirements.txt

RUN apt-get update
# RUN apt-get install ffmpeg libsm6 libxext6  -y

# copy the content of the local src directory to the working directory
# COPY nervotec_vantage.py .

ENV PYTHONPATH /eye_blink_detection

# command to run on container start
CMD [ "python", "-u", "./eye_blink_detection_vantage.py" ]
