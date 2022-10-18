# ROS-backend

Backend for Resource Optimization Service


## Getting Started

This project uses pipenv to manage the development and production environments.

Once you have pipenv installed, do the following:

```bash
pipenv install
```
Afterwards you can activate the virtual environment by running:
```bash
pipenv shell
```

A list of configurable environment variables is present inside `.env.example` file.

### Dependencies
The application depends on several parts of the insights platform. These dependencies are provided by the 
`docker-compose.yml` file in the *scripts* directory.

To run the dependencies, just run following command:
```bash
cd scripts && docker-compose up insights-inventory-mq db-ros insights-engine
```
## Running the ROS application
### Within docker
To run the full application ( With ros components within docker)
```bash
docker-compose up ros-processor ros-api
```

### On host machine
In order to properly run the application from the host machine, you need to have modified your `/etc/hosts` file. Check the
README.md file in scripts directory.

#### Initialize the database
Run the following commands to excute the db migration scripts.
```bash
python manage.py db upgrade
python manage.py seed 
```

#### Running the processor locally
The processor component connects to kafka, and listens on topics for system archive uploads/ system deletion messages.
```bash
python -m ros.processor.main
```

#### Running the web api locally
The web api component provides a REST api view of the app database.
```bash
python -m ros.api.main
```

#### Running the Tests
It is possible to run the tests using pytest:
```bash
pipenv install --dev
pytest --cov=ros tests
```

## Running Inventory API with xjoin pipeline
To run full inventory api with xjoin , run the following command:
```bash
docker-compose up insights-inventory-web xjoin
make configure-xjoin 
```
Note - Before running the above commands make sure kafka and db-host-inventory containers are up and running.

## Available v1 API endpoints

### Request
`GET /api/ros/v1/status` Shows the status of the server

    curl -v -H "Content-Type: application/json" https://cloud.redhat.com/api/ros/v1/status

### Response

    HTTP/1.1 200 OK
    Date: Thu, 24 Feb 2011 12:36:30 GMT
    Status: 200 OK
    Connection: close
    Content-Type: application/json
    Content-Length: 2

    {"status": "Application is running!"}



### Request
`GET /api/ros/v1/systems` Shows list of all systems from Host Inventory having a Performance Profile

    curl -v -H "Content-Type: application/json" https://cloud.redhat.com/api/ros/v1/systems -u rhn-username:redhat

### Response

    HTTP/1.1 200 OK
    Date: Thu, 24 Feb 2011 12:36:30 GMT
    Status: 200 OK
    Connection: close
    Content-Type: application/json
    Content-Length: 2

    [{
      "fqdn": "string",
      "display_name": "string",
      "inventory_id": "string",
      "account": "string",
      "org_id": "string",
      "number_of_suggestions": 0,
      "state": "string",
      "performance_utilization": {
        "memory": 0,
        "cpu": 0,
        "io": 0
      },
      "cloud_provider": "string",
      "instance_type": "string",
      "idling_time": 0,
      "os": "string",
      "report_date": "string"
    }]


For local dev setup, please remember to use the x-rh-identity header encoded from your account number and org_id, the one used while running `make insights-upload-data` and `make ros-upload-data` commands.
