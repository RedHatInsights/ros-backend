# ROS Development environment.
Below are the instructions to setup ROS development environment

## Setup

1. Update /etc/hosts

```
127.0.0.1       kafka
127.0.0.1       minio
```
2. Create require directories for minio.
```
mkdir -p /usr/share/minio/{minio-conf,minio-data}
```

3. Clone ros-backend repository and start necessary services in container.
```
# git clone https://github.com/RedHatInsights/ros-backend.git
# cd scripts
# docker login quay.io
# . .env-minio
# docker-compose --env-file .env-minio  up
```

4) Wait for insights-inventory container to get started and after that follow the below steps to start inventory API server.
```
# docker exec -it <insights-inventory-container-id> bash
# python run_gunicorn.py
```

## Usage

### Run ros-backend flask application.

```
pipenv install --dev
FLASK_APP=ros/app.py flask run
```

### Sending data to ingress/kafka topic(platform.upload.resource-optimization)
```
make insights-upload-data
```


## Useful commands.

1. Monitor resource-optimization kafka topic
```
docker-compose exec kafka kafka-console-consumer --topic=platform.upload.resource-optimization --bootstrap-server=localhost:29092

```