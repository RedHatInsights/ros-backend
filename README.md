# ROS-backend

Backend for Resource Optimization Service

The Red Hat Insights resource optimization service enables RHEL customers to assess and monitor their public cloud usage and optimization. The service exposes workload metrics for CPU, memory, and disk-usage and compares them to resource limits recommended by the public cloud provider.
Currently ROS only provides suggestions for AWS RHEL instances. To enable ROS, a customer needs to perform a few prerequisite steps on targeted systems via Ansible playbook.

Underneath, ROS uses Performance Co-Pilot (PCP) to monitor and report workload metrics.

## How it works

![UML](http://www.plantuml.com/plantuml/png/dLLDJzj04BtxLuosXruI5zfRX288f1KIa2WcI9H4riQxILROkzP-12Bg_zxPh5qbDU401sI_VJDlPlQDSsuirTOLUMI5pJbCHWaCQFRC9OEnLXatHiWL_CpLIrGYKsIYfDB2UY4YBZ5c2sLExLBf8XPoWv3IsvZx1tCGG8GqOhMsPYQvN0d9IIi-uB7cnkKOlL2lGFRg8V3bncSOv8v7W7-7wHjn2E8pMORobIPjTf2287N8zPsZTCIefGjgUAZXQa0YxBdRFzfj3zRAsEu_60MtkQ8iEXhHxRypb3RKQBOcr8E6smq7RSc301JygF4xPV70vmErXAEQRrXXwIpfmTdx3VSxCqdijkH88Qx4EN96AWJVI9s4-2ncQomlFAVWblffUpYEguPQAhsZpkGJlhgSfuBXwrUjJ8gDMoepdl8DpHsrGia_PybZSZ-yJPFxY_jXlvfZ5GmpYpmamRgReAOu-pqkHAOLyHLhli8i7dOuJugTdUvmZB4SK_WCMUcGy4GknzDqz32S9DU_XrUa0oIEoToJ2rxW97QSs-7jQFBuFaqeJxaUfTExg_eu7JocuyamIQQJuRnJLVEgYZwuhRDkOyiU_E8MQ9Of9otK7SDIgm8cwxJ63Q2PSnurGHX-F7SFBZN7fk4RJ7VN1-6kGCYbmd-Gx5u_btFCjRULlmV_WLcAtFCpfHaW3hJHcaaXzybf6SX1DFvuguv_2uxPl9N6MxGvJ1k7raQgX-fNe9cxTCM2wtu7pudJkJ-QJcx0Ac3gHVgr0AgpjTZmS3N9Zy0L9jNA6zHgnxtpYL-gMYUCekcy1hDSEUQnZM3S3vRG5-FD5JOcGAKhhL8U5SpN8bY_sb_BJFFTMYBs__gXz_Qkj3NBpnjb9YyOG-e3rsAvRHoR2WPKCb1wXOy-gErQyonaIJKjOA1UnvGn_vDqUd8IdNF9N97_1G00)

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
Run the following commands to execute the db migration scripts.
```bash
export FLASK_APP=manage.py
flask db upgrade
flask seed
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
poetry install
poetry run pytest --cov=ros tests
```

## Running Inventory API with xjoin pipeline
To run full inventory api with xjoin , run the following command:
```bash
docker-compose up insights-inventory-web xjoin
make configure-xjoin 
```
Note - Before running the above commands make sure kafka and db-host-inventory containers are up and running.

## Available API endpoints

Our REST API documentation can be found at /api/ros. You may access the raw OpenAPI definition [here](https://raw.githubusercontent.com/RedHatInsights/ros-backend/refs/heads/main/ros/openapi/openapi.json).
On a local instance it can be accessed on http://localhost:8000/api/ros/v1/openapi.json.

For local dev setup, please remember to use the x-rh-identity header encoded from your account number and org_id, the one used while running `make insights-upload-data` command.
