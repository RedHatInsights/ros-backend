# ROS Development environment.
Below are the instructions to setup ROS development environment

## Setup

1. If you want to access the containers from host machine, update /etc/hosts

```
127.0.0.1       kafka
127.0.0.1       minio
```

3. Clone ros-backend repository.
```bash
git clone https://github.com/RedHatInsights/ros-backend.git
cd scripts
docker login quay.io
```

4. Start dependency containers (insight-sinventory-web has dependency on all platform containers, so they can be started with a single command).
The db-ros container just provides a PostgreSQL database for the ROS application
```bash
docker-compose up --build insights-inventory-web db-ros
```

## Usage
Following commands are expected to be run from the repository root (not within the *scripts* directory).
### Enter the pipenv environment
```bash
pipenv install --dev 
pipenv shell
```
### Run ros-api application
```
python -m ros.api.main
```

### Run the ros-processor application
```bash
python -m ros.processor.main
```

### Sending report to ingress/kafka topic(platform.upload.advisor) and registering system in host inventory. 
```
make insights-upload-data
```
