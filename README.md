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