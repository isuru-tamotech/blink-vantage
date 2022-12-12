### Vantage Docker commands

To build the docker container: 

```
sudo docker build -f Dockerfile -t va-blink-engine .
```

To run the rabbitmq server

```
sudo docker run -d --name va-mq --net=host rabbitmq:3-management
```

To run the engine 

```
sudo docker run -d --name va-blink-engine --net=host --env-file env.list va-blink-engine
```

### Create environment to run demo input and output apps

```
python -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```
Run inputs with videos, first copy a video to the videos folder (avi,mp4)
Get a new terminal and run these commands

```
export INPUTQ=input_queue
export QUEUE_USERNAME=guest
export QUEUE_PASSWORD=guest
export QUEUE_HOST=localhost
export QUEUE_PORT=5672
export EXCHANGE_NAME=test_exchange
./venv/bin/python input_app_video.py
```

Run inputs with camera
Get a new terminal and run these commands. If you want to change the camera change CAM_ID in input_app_camera

```
export INPUTQ=input_queue
export QUEUE_USERNAME=guest
export QUEUE_PASSWORD=guest
export QUEUE_HOST=localhost
export QUEUE_PORT=5672
export EXCHANGE_NAME=test_exchange
./venv/bin/python input_app_camera.py
```

To run the output app. Get a new terminal and run these commands

```
export OUTPUTQ=output_queue
export QUEUE_USERNAME=guest
export QUEUE_PASSWORD=guest
export QUEUE_HOST=localhost
export QUEUE_PORT=5672
./venv/bin/python output_app.py
```

### To create the tar file for sending

sudo docker save va-blink-engine > engine.tar