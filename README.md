# ROS-backend

Backend for Resource Optimization Service

The Red Hat Insights resource optimization service enables RHEL customers to assess and monitor their public cloud usage and optimization. The service exposes workload metrics for CPU, memory, and disk-usage and compares them to resource limits recommended by the public cloud provider.
Currently ROS only provides suggestions for AWS RHEL instances. To enable ROS, customers need to perform a few prerequisite steps on targeted systems via Ansible playbook.

Underneath, ROS uses Performance Co-Pilot (PCP) to monitor and report workload metrics.

## How it works

### Architecture Overview

ROS currently supports two architectures running in parallel:
- **ROS V1** - Legacy Architecture 
- **ROS V2** - New Architecture

### ROS V2 Components

The new architecture consists of the following components:

#### 1. **Suggestions Engine**
- **Consumes from**: `platform.inventory.events`
- **Produces to**: `ros.events`
- **Responsibilities**:
  - Listens to inventory create/update events
  - Downloads and extracts system archives containing PCP data
  - Runs `pmlogextract` and `pmlogsummary` commands to process PCP metrics
  - Executes ROS rules engine to generate recommendations
  - Produces events with performance profiles and rule hits
  - Handles both systems with and without PCP data

#### 2. **Report Processor Consumer**
- **Consumes from**: `ros.events`
- **Responsibilities**:
  - Processes events produced by Suggestions Engine
  - Creates/updates system records in the database
  - Manages performance profiles and history
  - Processes API-triggered system updates

#### 3. **System Eraser**
- **Consumes from**: `platform.inventory.events`
- **Responsibilities**:
  - Listens for system deletion events from Inventory
  - Removes systems and associated data from ROS database
  - Ensures data consistency with inventory service

### ROS V1 Components (Legacy Architecture)

![UML](http://www.plantuml.com/plantuml/png/dLLDJzj04BtxLuosXruI5zfRX288f1KIa2WcI9H4riQxILROkzP-12Bg_zxPh5qbDU401sI_VJDlPlQDSsuirTOLUMI5pJbCHWaCQFRC9OEnLXatHiWL_CpLIrGYKsIYfDB2UY4YBZ5c2sLExLBf8XPoWv3IsvZx1tCGG8GqOhMsPYQvN0d9IIi-uB7cnkKOlL2lGFRg8V3bncSOv8v7W7-7wHjn2E8pMORobIPjTf2287N8zPsZTCIefGjgUAZXQa0YxBdRFzfj3zRAsEu_60MtkQ8iEXhHxRypb3RKQBOcr8E6smq7RSc301JygF4xPV70vmErXAEQRrXXwIpfmTdx3VSxCqdijkH88Qx4EN96AWJVI9s4-2ncQomlFAVWblffUpYEguPQAhsZpkGJlhgSfuBXwrUjJ8gDMoepdl8DpHsrGia_PybZSZ-yJPFxY_jXlvfZ5GmpYpmamRgReAOu-pqkHAOLyHLhli8i7dOuJugTdUvmZB4SK_WCMUcGy4GknzDqz32S9DU_XrUa0oIEoToJ2rxW97QSs-7jQFBuFaqeJxaUfTExg_eu7JocuyamIQQJuRnJLVEgYZwuhRDkOyiU_E8MQ9Of9otK7SDIgm8cwxJ63Q2PSnurGHX-F7SFBZN7fk4RJ7VN1-6kGCYbmd-Gx5u_btFCjRULlmV_WLcAtFCpfHaW3hJHcaaXzybf6SX1DFvuguv_2uxPl9N6MxGvJ1k7raQgX-fNe9cxTCM2wtu7pudJkJ-QJcx0Ac3gHVgr0AgpjTZmS3N9Zy0L9jNA6zHgnxtpYL-gMYUCekcy1hDSEUQnZM3S3vRG5-FD5JOcGAKhhL8U5SpN8bY_sb_BJFFTMYBs__gXz_Qkj3NBpnjb9YyOG-e3rsAvRHoR2WPKCb1wXOy-gErQyonaIJKjOA1UnvGn_vDqUd8IdNF9N97_1G00)

These components serve customers not yet migrated to ROS V2 and will be deprecated once migration is complete:

#### 1. **Inventory Events Processor**
- Processor handling inventory events
- **Consumes from**: `platform.inventory.events`
- Combines data processing and database operations in a single service

#### 2. **Engine Result Processor**
- Processes results from Insights Engine
- **Consumes from**: `platform.engine.results`

### Shared Components

These components are shared by both V1 and V2 architectures:

#### **API Service**
- REST API providing access to optimization recommendations
- OpenAPI specification available at `/api/ros/v1/openapi.json`
- Handles RBAC and Kessel authorization
- Serves data from the same database regardless of which architecture processed it

#### **Garbage Collector**
- Periodic cleanup of outdated system data
- Configurable via `GARBAGE_COLLECTION_INTERVAL` and `DAYS_UNTIL_STALE`
- Works with data from both V1 and V2 processing

  
## DB Schema
![UML](http://www.plantuml.com/plantuml/png/tLJDRjmW4BxxARXLgfeyG1L5KLJrqaEhvW4GXjdrDC1G63PritdtOfDQ45chdkk39Rxlcny-HdENM4NEpWwCR45y__eWxfL-16_4ftlne2TmQdWd9ZGWU0AH0l7ViyQeBGpbg4w4HeH8emMNn1Fo99G_MZ12HtfAuW30Gtf47rHKJbZqm7C0GP4d6WRmZ3mBLQ97rF84CI5vyJm8yVxr87rsukRcsvVRM_5HeEVXPOkBarHQK_QSQWoQNYh4rLNvlOeAoF1hGIaU9PfwRXC6Y0UAJdaDCaGwe8MQECs9mSdz_5rO14rnIVqZaH_Va9dHuc_5IBvHH0WKMHh5K5161ucL2uKfTnyXIZgiQPq3RzRWjDLFNADEAkf9nO9GALX4_YXhqssXR45EM4e1AxIfxJAX1Az62wQW8v7zK52c8BNo1arVfMSMhr0llA5SCbmsj3IGcE9yqTZ2jAvKhZNd_xQ-SR1cIfV6cqkqv-hXvvP5VmA_U5s7FMSq1TMMibbUuuG6OdS1WobODKklN7-pmq_ZEm1zujLNdaChRMrf40joC_UDqH6EIFvVVTGXoxL2wjkXFTI1AvVVOuwHSjWUeR5xUQUBowI-99hUDqWwObY7Qrio4LJgpubixZMQlC46QZhfnqvMGourLhtQ6OCI2aQESzFAccmJw0YhHF6Rjyd1x14lG_bgkIHUwFhwV6vtyKQTpmkrjmGkIlezqKdfUT-NuQu0sTa_)
## Getting Started

This project uses poetry to manage the development and production environments.

Once you have poetry installed, do the following:

The latest version is supported on Python 3.11, install it and then switch to 3.11 version:
```bash
poetry env use python3.11
```

There are some package dependencies, install those:
```bash
dnf install tar gzip gcc python3.11-devel libpq-devel
```

Install the required dependencies:
```bash
poetry install
```

Afterwards you can activate the virtual environment by running:
```bash
poetry shell
```

A list of configurable environment variables is present inside `.env.example` file.

### Configuration

#### Kafka Topics

ROS V2 uses the following Kafka topics:
- `platform.inventory.events` - Input topic for inventory system events (create, update, delete)
- `ros.events` - Internal topic for communication between Suggestions Engine and Report Processor

#### Feature Flags

ROS V2 functionality is controlled by Unleash feature flags for gradual migration:
- `ros.v2` - Flag to enable/disable ROS V2 architecture
  - When **enabled**: System uses V2 architecture (Suggestions Engine → Report Processor flow)
  - When **disabled**: System uses V1 architecture (Inventory Events Processor flow)
  - Uses `org_id` for controlled rollout

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
In order to properly run the application from the host machine, you may optionally modify your `/etc/hosts` file for convenience. 
Check the README.md file in scripts directory for details and important networking considerations.

#### Initialize the database
Run the following commands to execute the db migration scripts.
```bash
export FLASK_APP=manage.py
flask db upgrade
flask seed
```

#### Running ROS V2 Components Locally (New Architecture)

##### Suggestions Engine

```bash
python -m ros.processor.suggestions_engine
```

##### Report Processor

```bash
python -m ros.processor.report_processor_consumer
```

##### System Eraser
```bash
python -m ros.processor.system_eraser
```

#### Running ROS V1 Components Locally (Legacy Architecture)

##### Inventory Events Processor

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
poetry install
poetry run pytest --cov=ros tests
```

## Available API endpoints

Resource Optimization REST API documentation can be found at `/api/ros`. It is accessible at raw OpenAPI definition [here](https://raw.githubusercontent.com/RedHatInsights/ros-backend/refs/heads/main/ros/openapi/openapi.json).
On a local instance it can be accessed on http://localhost:8000/api/ros/v1/openapi.json.

For local development setup, remember to use the `x-rh-identity` header encoded from account number and org_id, the one used while running `make insights-upload-data` command.
