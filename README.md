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

To run the input app

```
export INPUTQ=input_queue
export QUEUE_USERNAME=guest
export QUEUE_PASSWORD=guest
export QUEUE_HOST=localhost
export QUEUE_PORT=5672
export EXCHANGE_NAME=test_exchange
python3 input-app.py
```

To run the output app

```
export OUTPUTQ=output_queue
export QUEUE_USERNAME=guest
export QUEUE_PASSWORD=guest
export QUEUE_HOST=localhost
export QUEUE_PORT=5672
python3 output-app.py
```