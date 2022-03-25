import datetime
import json
import os
import pytest
from ros.lib.app import app, db
from sqlalchemy_utils import database_exists, create_database, drop_database
from ros.lib.models import RhAccount, System, PerformanceProfile, Rule, PerformanceProfileHistory


@pytest.fixture(scope="session")
def database():
    DB_USER = os.getenv("ROS_DB_USER", "postgres")
    DB_PASSWORD = os.getenv("ROS_DB_PASS", "postgres")
    DB_HOST = os.getenv("ROS_DB_HOST", "localhost")
    DB_PORT = os.getenv("ROS_DB_PORT", "15432")
    DB_NAME = os.getenv("DB_NAME", "ros_db_test")
    DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}"\
             f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    if not database_exists(DB_URI):
        create_database(DB_URI)

    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
    app.testing = True
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        drop_database(DB_URI)


@pytest.fixture(scope="function")
def db_setup(database):
    yield
    clean_tables()


@pytest.fixture(scope="function")
def db_create_account(db_setup):
    account = RhAccount(id=1, account='12345')
    db.session.add(account)
    db.session.commit()


@pytest.fixture(scope="function")
def db_create_system(db_create_account):
    system = System(
        id=1,
        account_id=1,
        inventory_id='ee0b9978-fe1b-4191-8408-cbadbd47f7a3',
        display_name='ip-172-31-11-67.ap-south-1.compute.internal',
        fqdn='ip-172-31-11-67.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Idling',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},

    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture(scope="function")
def db_create_performance_profile():
    # dummy record values
    performance_record = {
      "hinv.ncpu": 2.0,
      "total_cpus": 1,
      "mem.physmem": 825740.0,
      "instance_type": "t2.micro",
      "disk.dev.total": {
        "xvda": {
          "val": 0.314,
          "units": "count / sec"
        }
      },
      "mem.util.available": 825040.0,
      "kernel.all.cpu.idle": 1.997,
      "kernel.all.pressure.io.full.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      },
      "kernel.all.pressure.io.some.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      },
      "kernel.all.pressure.cpu.some.avg": {
        "1 minute": {
          "val": 0.06,
          "units": "none"
        }
      },
      "kernel.all.pressure.memory.full.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      },
      "kernel.all.pressure.memory.some.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      }
    }
    performance_utilization = {"io": {"xvda": 314}, "cpu": 0, "max_io": 314, "memory": 0}
    performance_profile = PerformanceProfile(
        system_id=1,
        state='Idling',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        rule_hit_details=[{
          "key": "INSTANCE_IDLE",
          "tags": [],
          "type": "rule",
          "links": {
            "kcs": [],
            "jira": [
              "https://issues.redhat.com/browse/CEECBA-5875"
            ]
          },
          "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.0116,
            "region": "us-east-1",
            "summary": [
              "System is IDLE"
            ],
            "error_key": "INSTANCE_IDLE",
            "candidates": [
              [
                "t2.nano",
                0.0058
              ]
            ],
            "instance_type": "t2.micro",
            "cloud_provider": "Amazon Web Services"
          },
          "rule_id": "ros_instance_evaluation|INSTANCE_IDLE",
          "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
          "system_id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a3"
        }]
    )
    db.session.add(performance_profile)
    db.session.commit()


@pytest.fixture(scope="function")
def db_create_performance_profile_history():
    # dummy record values
    performance_record = {
      "hinv.ncpu": 2.0,
      "total_cpus": 1,
      "mem.physmem": 825740.0,
      "instance_type": "t2.micro",
      "disk.dev.total": {
        "xvda": {
          "val": 0.314,
          "units": "count / sec"
        }
      },
      "mem.util.available": 825040.0,
      "kernel.all.cpu.idle": 1.997,
      "kernel.all.pressure.io.full.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      },
      "kernel.all.pressure.io.some.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      },
      "kernel.all.pressure.cpu.some.avg": {
        "1 minute": {
          "val": 0.06,
          "units": "none"
        }
      },
      "kernel.all.pressure.memory.full.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      },
      "kernel.all.pressure.memory.some.avg": {
        "1 minute": {
          "val": 0.0,
          "units": "none"
        }
      }
    }
    performance_utilization = {"io": {"xvda": 314}, "cpu": 0, "max_io": 314, "memory": 0}
    performance_profile_history = PerformanceProfileHistory(
        system_id=1,
        state='Idling',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        rule_hit_details=[{
          "key": "INSTANCE_IDLE",
          "tags": [],
          "type": "rule",
          "links": {
            "kcs": [],
            "jira": [
              "https://issues.redhat.com/browse/CEECBA-5875"
            ]
          },
          "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.0116,
            "region": "us-east-1",
            "summary": [
              "System is IDLE"
            ],
            "error_key": "INSTANCE_IDLE",
            "candidates": [
              [
                "t2.nano",
                0.0058
              ]
            ],
            "instance_type": "t2.micro",
            "cloud_provider": "Amazon Web Services"
          },
          "rule_id": "ros_instance_evaluation|INSTANCE_IDLE",
          "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
          "system_id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a3"
        }]
    )
    db.session.add(performance_profile_history)
    db.session.commit()


@pytest.fixture(scope="function")
def db_instantiate_rules(db_setup):
    with open("seed.d/rules.json") as f:
        rules = json.loads(f.read())
        for data in rules:
            rule = Rule(
                rule_id=data['rule_id'],
                description=data['description'],
                reason=data['reason'],
                resolution=data['resolution'],
                condition=data['condition']
            )
            db.session.add(rule)
        db.session.commit()


def clean_tables():
    db.session.expire_all()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
