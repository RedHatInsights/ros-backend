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

## Initialize the database
Run the following commands to excute the db migration scripts.
```bash
python manage.py db upgrade
```

## Running the server locally

```bash
python run.py
```

## v0 API endpoints available

| API endpoint                  | description                                                                |
| ------------                  | -----------                                                                |
| /api/v0/ros/systems           | Shows list of all systems from Host Inventory having a Performance Profile |
| /api/v0/ros/systems/<host_id> | Shows the Performance Profile of the selected <host_id>                    |
| /api/v0/ros/status            | Shows the status of the server                                             |

To run via API:
```
curl -v -H "x-rh-identity: <identity-header-value>" -H "Content-Type: application/json" http://localhost:8080/api/ros/v0/systems
curl -v -H "x-rh-identity: <identity-header-value>" -H "Content-Type: application/json" http://localhost:8080/api/ros/v0/status
curl -v -H "x-rh-identity: <identity-header-value>" -H "Content-Type: application/json" http://localhost:8080/api/ros/v0/systems/<host_id>
```
For local dev setup, please note that use the x-rh-identity header encoded from your account number, the one used while running `make insights-upload-data` and `make ros-upload-data` commands.
