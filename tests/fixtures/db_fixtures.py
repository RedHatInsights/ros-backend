import codecs
import datetime
import json
import os
import pytest
from ros.lib.app import app
from ros.extensions import db
from sqlalchemy_utils import database_exists, create_database, drop_database
from ros.lib.models import RhAccount, System, PerformanceProfile, Rule, PerformanceProfileHistory
from base64 import b64encode


@pytest.fixture(scope="session")
def auth_token():
    identity = {
        "identity": {
            "account_number": "12345",
            "type": "User",
            "user": {
                "username": "tuser@redhat.com",
                "email": "tuser@redhat.com",
                "first_name": "test",
                "last_name": "user",
                "is_active": True,
                "is_org_admin": False,
                "is_internal": True,
                "locale": "en_US"
            },
            "org_id": "000001",
            "internal": {
                "org_id": "000001"
            }
        }
    }
    auth_token = codecs.decode(b64encode(json.dumps(identity).encode('utf-8')))
    return auth_token


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
    account = RhAccount(id=1, account='12345', org_id='000001')
    db.session.add(account)
    db.session.commit()


@pytest.fixture(scope="function")
def db_create_system(db_create_account):
    system = System(
        id=1,
        tenant_id=1,
        inventory_id='ee0b9978-fe1b-4191-8408-cbadbd47f7a3',
        display_name='ip-172-31-11-67.ap-south-1.compute.internal',
        fqdn='ip-172-31-11-67.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Idling',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        cpu_states=['CPU_UNDERSIZED', 'CPU_UNDERSIZED_BY_PRESSURE'],
        io_states=['IO_UNDERSIZED_BY_PRESSURE'],
        memory_states=['MEMORY_UNDERSIZED', 'MEMORY_UNDERSIZED_BY_PRESSURE'],
        groups=[]
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
        psi_enabled=False,
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
            "states": {'idle': ['IDLE']},
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
            "states": {'idle': ['IDLE']},
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


@pytest.fixture(scope="function")
def db_create_performance_profile_for_under_pressure():
    # dummy record values
    performance_record = {
      "hinv.ncpu": 2.0,
      "total_cpus": 1,
      "mem.physmem": 825740.0,
      "disk.dev.total": {
        "xvda": {"val": 0.314, "units": "count / sec"}
      },
      "mem.util.available": 725040.0,
      "kernel.all.cpu.idle": 1.797,
      "kernel.all.pressure.io.full.avg": {
        "1 minute": {"val": 21.0, "units": "none"}
      },
      "kernel.all.pressure.io.some.avg": {
        "1 minute": {"val": 210.0, "units": "none"}
      },
      "kernel.all.pressure.cpu.some.avg": {
        "1 minute": {"val": 21.06, "units": "none"}
      },
      "kernel.all.pressure.memory.full.avg": {
        "1 minute": {"val": 21.0, "units": "none"}
      },
      "kernel.all.pressure.memory.some.avg": {
        "1 minute": {"val": 21.0, "units": "none"}
      }
    }
    performance_utilization = {
      "io": {"xvda": 0.314},
      "cpu": 10,
      "max_io": 0.314,
      "memory": 12
    }
    performance_profile = PerformanceProfile(
        system_id=1,
        state='Idling',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[{
          "rule_id": "ros_instance_evaluation|INSTANCE_OPTIMIZED_UNDER_PRESSURE",
          "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
          "key": "INSTANCE_OPTIMIZED_UNDER_PRESSURE",
          "type": "rule",
          "details": {
            "rhel": "8.4",
            "cloud_provider": "aws",
            "instance_type": "t2.micro",
            "region": "us-east-1",
            "price": 0.0116,
            "states": {
                "cpu": [
                    "CPU_OVERSIZED",
                    "CPU_UNDERSIZED_BY_PRESSURE"
                ],
                "io": [
                    "IO_UNDERSIZED_BY_PRESSURE"
                ],
                "memory": [
                    "MEMORY_OVERSIZED",
                    "MEMORY_UNDERSIZED_BY_PRESSURE"
                ]
            },
            "type": "rule",
            "error_key": "INSTANCE_OPTIMIZED_UNDER_PRESSURE",
            "candidates": [
              [
                "t2.small",
                0.023
              ],
              [
                "m1.small",
                0.044
              ]
            ]
          },
          "tags": [],
          "links": {
            "jira": [
              "https://issues.redhat.com/browse/CEECBA-5875"
            ],
            "kcs": []
          },
          "system_id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a3"
        }]
    )
    db.session.add(performance_profile)
    db.session.commit()


def clean_tables():
    db.session.expire_all()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture
def db_create_idle_system(db_create_account):
    system = System(
        id=5,
        tenant_id=1,
        inventory_id='ee0b9978-cccc-4191-8408-cbadbd47f7a3',
        display_name='idle.ap-south-1.compute.internal',
        fqdn='idle.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Idling',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        groups=[]
    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture
def db_create_performance_profile_for_idle():
    # dummy record values
    performance_record = {
        "hinv.ncpu": 2.0,
        "total_cpus": 1,
        "mem.physmem": 825740.0,
        "disk.dev.total": {
            "xvda": {"val": 0.314, "units": "count / sec"}
        },
        "mem.util.available": 825040.0,
        "kernel.all.cpu.idle": 1.997,
        "kernel.all.pressure.io.full.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.io.some.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.cpu.some.avg": {
            "1 minute": {"val": 0.06, "units": "none"}
        },
        "kernel.all.pressure.memory.full.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.memory.some.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        }
    }
    performance_utilization = {
        "io": {"xvda": 0.314},
        "cpu": 0,
        "max_io": 0.314,
        "memory": 0
    }
    performance_profile = PerformanceProfile(
        system_id=5,
        state='Idling',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[
            {"key": "INSTANCE_IDLE",
             "tags": [],
             "type": "rule",
             "links": {"kcs": [], "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]},
             "details": {
                 "rhel": "8.4",
                 "type": "rule",
                 "price": 0.0116,
                 "region": "us-east-1",
                 "states": {"idle": ["IDLE"]},
                 "error_key": "INSTANCE_IDLE",
                 "candidates": [["t2.nano", 0.0058]], "instance_type": "t2.micro", "cloud_provider": "aws"},
             "rule_id": "ros_instance_evaluation|INSTANCE_IDLE",
             "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
             "system_id": "ee0b9978-cccc-4191-8408-cbadbd47f7a3"}],
        top_candidate="t2.nano",
        top_candidate_price=0.0058
    )
    db.session.add(performance_profile)
    db.session.commit()


@pytest.fixture
def db_create_undersized_system(db_create_account):
    system = System(
        id=6,
        tenant_id=1,
        inventory_id='ee0b9978-dddd-4191-8408-cbadbd47f7a3',
        display_name='undersized.ap-south-1.compute.internal',
        fqdn='undersized.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Undersized',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        cpu_states=['CPU_UNDERSIZED', 'CPU_UNDERSIZED_BY_PRESSURE'],
        io_states=['IO_UNDERSIZED_BY_PRESSURE'],
        memory_states=['MEMORY_UNDERSIZED', 'MEMORY_UNDERSIZED_BY_PRESSURE'],
        groups=[]
    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture
def db_create_performance_profile_for_undersized():
    # dummy record values
    performance_record = {
        "hinv.ncpu": 2.0,
        "total_cpus": 1,
        "mem.physmem": 825740.0,
        "disk.dev.total": {
            "xvda": {"val": 0.314, "units": "count / sec"}
        },
        "mem.util.available": 25040.0,
        "kernel.all.cpu.idle": 0.197,
        "kernel.all.pressure.io.full.avg": {
            "1 minute": {"val": 21.0, "units": "none"}
        },
        "kernel.all.pressure.io.some.avg": {
            "1 minute": {"val": 210, "units": "none"}
        },
        "kernel.all.pressure.cpu.some.avg": {
            "1 minute": {"val": 21.06, "units": "none"}
        },
        "kernel.all.pressure.memory.full.avg": {
            "1 minute": {"val": 21.0, "units": "none"}
        },
        "kernel.all.pressure.memory.some.avg": {
            "1 minute": {"val": 21.0, "units": "none"}
        }
    }
    performance_utilization = {
        "io": {"xvda": 0.314},
        "cpu": 90,
        "max_io": 0.314,
        "memory": 97
    }
    performance_profile = PerformanceProfile(
        system_id=6,
        state='Undersized',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[
            {"key": "INSTANCE_UNDERSIZED",
             "tags": [],
             "type": "rule",
             "links": {"kcs": [], "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]},
             "details": {
                 "rhel": "8.4",
                 "type": "rule",
                 "price": 0.0116,
                 "region": "us-east-1",
                 "states": {
                     "io": ["IO_UNDERSIZED_BY_PRESSURE"],
                     "cpu": ["CPU_UNDERSIZED", "CPU_UNDERSIZED_BY_PRESSURE"],
                     "memory": ["MEMORY_UNDERSIZED", "MEMORY_UNDERSIZED_BY_PRESSURE"]},
                 "error_key": "INSTANCE_UNDERSIZED",
                 "candidates": [["t2.medium", 0.0464], ["t2.large", 0.0928], ["c1.medium", 0.13],
                                ["m1.large", 0.175], ["t2.xlarge", 0.1856], ["m2.xlarge", 0.245],
                                ["m1.xlarge", 0.35], ["t2.2xlarge", 0.3712], ["m2.2xlarge", 0.49],
                                ["c1.xlarge", 0.52], ["g4dn.xlarge", 0.558], ["g4dn.2xlarge", 0.797],
                                ["m2.4xlarge", 0.98], ["g4dn.4xlarge", 1.276], ["g4dn.8xlarge", 2.307],
                                ["g4dn.12xlarge", 4.147], ["g4dn.16xlarge", 4.613]],
                 "instance_type": "t2.micro", "cloud_provider": "aws"},
             "rule_id": "ros_instance_evaluation|INSTANCE_UNDERSIZED",
             "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
             "system_id": "ee0b9978-dddd-4191-8408-cbadbd47f7a3"}],
        top_candidate="t2.medium",
        top_candidate_price=0.0464

    )
    db.session.add(performance_profile)
    db.session.commit()


@pytest.fixture
def db_create_optimized_system(db_create_account):
    system = System(
        id=7,
        tenant_id=1,
        inventory_id='ee0b9978-aaaa-4191-8408-cbadbd47f7a3',
        display_name='optimized.ap-south-1.compute.internal',
        fqdn='optimized.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Optimized',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        groups=[]
    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture
def db_create_performance_profile_for_optimized():
    # dummy record values
    performance_record = {
        "hinv.ncpu": 2.0,
        "total_cpus": 1,
        "mem.physmem": 825740.0,
        "disk.dev.total": {
            "xvda": {"val": 0.314, "units": "count / sec"}
        },
        "mem.util.available": 525040.0,
        "kernel.all.cpu.idle": 0.997,
        "kernel.all.pressure.io.full.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.io.some.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.cpu.some.avg": {
            "1 minute": {"val": 0.06, "units": "none"}
        },
        "kernel.all.pressure.memory.full.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.memory.some.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        }
    }
    performance_utilization = {
        "io": {"xvda": 0.314},
        "cpu": 50,
        "max_io": 0.314,
        "memory": 36
    }
    performance_profile = PerformanceProfile(
        system_id=7,
        state='Optimized',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[]
    )
    db.session.add(performance_profile)
    db.session.commit()


@pytest.fixture
def db_create_no_pcp_system(db_create_account):
    system = System(
        id=8,
        tenant_id=1,
        inventory_id='ee0b9978-bbbb-4191-8408-cbadbd47f7a3',
        display_name='nopcp.ap-south-1.compute.internal',
        fqdn='nopcp.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Waiting for data',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        groups=[]
    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture
def db_create_performance_profile_for_no_pcp():
    # dummy record values
    performance_record = {
        "total_cpus": 1,
    }
    performance_utilization = {
        "io": {},
        "cpu": -1,
        "max_io": -1,
        "memory": -1
    }
    performance_profile = PerformanceProfile(
        system_id=8,
        state='Waiting for data',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[{
            "rule_id": "ros_instance_evaluation|NO_PCP_DATA",
            "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report_no_data",
            "key": "NO_PCP_DATA",
            "type": "rule",
            "details": {
                "rhel": "8.4",
                "cloud_provider": "aws",
                "instance_type": "t2.micro",
                "region": "us-east-1",
                "price": 0.0116,
                "type": "rule",
                "error_key": "NO_PCP_DATA",
            },
            "tags": [],
            "links": {
                "jira": [
                    "https://issues.redhat.com/browse/CEECBA-5875"
                ],
                "kcs": []
            },
            "system_id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a3"
        }]
    )
    db.session.add(performance_profile)
    db.session.commit()


@pytest.fixture
def db_create_underpressure_system(db_create_account):
    system = System(
        id=9,
        tenant_id=1,
        inventory_id='ee0b9978-eeee-4191-8408-cbadbd47f7a3',
        display_name='underpressure.ap-south-1.compute.internal',
        fqdn='underpressure.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Under pressure',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        groups=[]
    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture
def db_create_performance_profile_for_underpressure():
    # dummy record values
    performance_record = {
        "total_cpus": 1,
    }
    performance_utilization = {
        "io": {"xvda": 0.314},
        "cpu": 10,
        "max_io": 0.314,
        "memory": 12
    }
    performance_profile = PerformanceProfile(
        system_id=9,
        state='Under pressure',
        operating_system={"name": "RHEL", "major": 8, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[
            {"key": "INSTANCE_OPTIMIZED_UNDER_PRESSURE",
             "tags": [],
             "type": "rule",
             "links": {"kcs": [], "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]},
             "details": {
                 "rhel": "8.4",
                 "type": "rule",
                 "price": 0.0116,
                 "region": "us-east-1",
                 "states": {
                     "io": ["IO_UNDERSIZED_BY_PRESSURE"],
                     "cpu": ["CPU_OVERSIZED", "CPU_UNDERSIZED_BY_PRESSURE"],
                     "memory": ["MEMORY_OVERSIZED", "MEMORY_UNDERSIZED_BY_PRESSURE"]},
                 "error_key": "INSTANCE_OPTIMIZED_UNDER_PRESSURE",
                 "candidates": [["t2.small", 0.023], ["m1.small", 0.044], ["t2.medium", 0.0464], ["m1.medium", 0.087],
                                ["t2.large", 0.0928], ["c1.medium", 0.13], ["m1.large", 0.175], ["t2.xlarge", 0.1856],
                                ["m2.xlarge", 0.245], ["m1.xlarge", 0.35], ["t2.2xlarge", 0.3712], ["m2.2xlarge", 0.49],
                                ["c1.xlarge", 0.52], ["g4dn.xlarge", 0.558], ["g4dn.2xlarge", 0.797],
                                ["m2.4xlarge", 0.98], ["g4dn.4xlarge", 1.276], ["g4dn.8xlarge", 2.307],
                                ["g4dn.12xlarge", 4.147], ["g4dn.16xlarge", 4.613]],
                 "instance_type": "t2.micro", "cloud_provider": "aws"},
             "rule_id": "ros_instance_evaluation|INSTANCE_OPTIMIZED_UNDER_PRESSURE",
             "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
             "system_id": "ee0b9978-eeee-4191-8408-cbadbd47f7a3"}],
        top_candidate="t2.small",
        top_candidate_price=0.023
    )
    db.session.add(performance_profile)
    db.session.commit()


@pytest.fixture
def db_create_idle_system_two(db_create_account):
    system = System(
        id=10,
        tenant_id=1,
        inventory_id='ee0b9978-cccc-4191-aaaa-cbadbd47f7a3',
        display_name='idle_two.ap-south-1.compute.internal',
        fqdn='idle_two.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Idling',
        region='ap-south-1',
        operating_system={"name": "RHEL", "major": 7, "minor": 4},
        groups=[]
    )

    db.session.add(system)
    db.session.commit()


@pytest.fixture
def db_create_performance_profile_for_idle_two():
    # dummy record values
    performance_record = {
        "hinv.ncpu": 2.0,
        "total_cpus": 1,
        "mem.physmem": 825740.0,
        "disk.dev.total": {
            "xvda": {"val": 0.314, "units": "count / sec"}
        },
        "mem.util.available": 825040.0,
        "kernel.all.cpu.idle": 1.997,
        "kernel.all.pressure.io.full.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.io.some.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.cpu.some.avg": {
            "1 minute": {"val": 0.06, "units": "none"}
        },
        "kernel.all.pressure.memory.full.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        },
        "kernel.all.pressure.memory.some.avg": {
            "1 minute": {"val": 0.0, "units": "none"}
        }
    }
    performance_utilization = {
        "io": {"xvda": 0.314},
        "cpu": 0,
        "max_io": 0.314,
        "memory": 0
    }
    performance_profile = PerformanceProfile(
        system_id=10,
        state='Idling',
        operating_system={"name": "RHEL", "major": 7, "minor": 4},
        performance_record=performance_record,
        performance_utilization=performance_utilization,
        report_date=datetime.datetime.utcnow(),
        number_of_recommendations=1,
        psi_enabled=True,
        rule_hit_details=[
            {"key": "INSTANCE_IDLE",
             "tags": [],
             "type": "rule",
             "links": {"kcs": [], "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]},
             "details": {
                 "rhel": "7.4",
                 "type": "rule",
                 "price": 0.0116,
                 "region": "us-east-1",
                 "states": {"idle": ["IDLE"]},
                 "error_key": "INSTANCE_IDLE",
                 "candidates": [["t2.nano", 0.0058]], "instance_type": "t2.micro", "cloud_provider": "aws"},
             "rule_id": "ros_instance_evaluation|INSTANCE_IDLE",
             "component": "telemetry.rules.plugins.ros.ros_instance_evaluation.report",
             "system_id": "ee0b9978-cccc-4191-aaaa-cbadbd47f7a3"}],
        top_candidate="t2.nano",
        top_candidate_price=0.0058
    )
    db.session.add(performance_profile)
    db.session.commit()
