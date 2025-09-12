# ROS Development environment.
Below are the instructions to setup ROS development environment

## Setup

1. **Optional**: To access services from your host machine, you can either:
   - Use the mapped ports: `localhost:9092` (Kafka), `localhost:9000` (Minio)
   - Or add entries to `/etc/hosts` for convenience (NOT recommended as it breaks container networking):

   ```
   # WARNING: Adding these entries will break container-to-container communication
   # Only use if you specifically need to access services by name from the host
   # Remove these entries if containers fail to connect to each other
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
docker-compose up --build insights-inventory-web db-ros insights-engine
```

## Usage
Following commands are expected to be run from the repository root (not within the *scripts* directory).
### Enter into the poetry(poetry shell) environment
```bash
poetry install
poetry shell
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
