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
cd scripts && docker-compose up insights-inventory-web db-ros
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

## Available v0 API endpoints

### Request
`GET /api/ros/v0/systems` Shows list of all systems from Host Inventory having a Performance Profile

    curl -v -H "Content-Type: application/json" https://cloud.redhat.com/api/ros/v0/systems -u rhn-username:redhat

### Response

    HTTP/1.1 200 OK
    Date: Thu, 24 Feb 2011 12:36:30 GMT
    Status: 200 OK
    Connection: close
    Content-Type: application/json
    Content-Length: 2

    [{
        'fqdn': 'machine1.local.company.com',
        'display_name': 'machine1-rhel_test123',
        'id': '12345-57575757',
        'account': '12345',
        'vm_uuid': '12345a1',
        'state': 'Crashloop',
        'recommendation_count': 5,
        'organization_id': 1,
        'performance_score': {
            'cpu_score': 20,
            'memory_score': 20,
            'io_score': 20
        },
        'facts': {
            'cloud_provider': 'AWS',
            'instance_type': 'm4large',
            'idling_time': '20',
            'io_wait': '180'
        }
    }]


### Request
`GET /api/ros/v0/systems/<host_id>` To get the individual system details using their <host_id>

    curl -v -H "Content-Type: application/json" https://cloud.redhat.com/api/ros/v0/systems/<host_id>

### Response

    HTTP/1.1 200 OK
    Date: Thu, 24 Feb 2011 12:36:30 GMT
    Status: 200 OK
    Connection: close
    Content-Type: application/json
    Content-Length: 2

    {"host_id": "12345-57575757", "performance_record": "{'avg_memory': '3998008.000', 'avg_memory_used': '2487908.973'}", "performance_score": "{'memory_score': 62}"}


### Request
`GET /api/ros/v0/status` Shows the status of the server

    curl -v -H "Content-Type: application/json" https://cloud.redhat.com/api/ros/v0/status

### Response

    HTTP/1.1 200 OK
    Date: Thu, 24 Feb 2011 12:36:30 GMT
    Status: 200 OK
    Connection: close
    Content-Type: application/json
    Content-Length: 2

    {"status": "Application is running!"}


For local dev setup, please remember to use the x-rh-identity header encoded from your account number, the one used while running `make insights-upload-data` and `make ros-upload-data` commands.
