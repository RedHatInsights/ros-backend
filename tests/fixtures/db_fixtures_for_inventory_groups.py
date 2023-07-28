import pytest
from ros.extensions import db
from ros.lib.models import System, PerformanceProfile
import datetime


@pytest.fixture
def system_with_example_group():
    system = System(
        id=2,
        tenant_id=1,
        inventory_id='12345678-fe1b-4191-8408-cbadbd47f7a3',
        display_name='ip-181-30-31-32.ap-north-1.compute.internal',
        fqdn='ip-181-30-31-32.ap-north-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Idling',
        region='ap-north-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 9},
        cpu_states=['CPU_UNDERSIZED', 'CPU_UNDERSIZED_BY_PRESSURE'],
        io_states=['IO_UNDERSIZED_BY_PRESSURE'],
        memory_states=['MEMORY_UNDERSIZED', 'MEMORY_UNDERSIZED_BY_PRESSURE'],
        groups=[{"id": "12345678-fe1b-4191-8408-cbadbd47f7a3", "name": "example-group"}]
    )
    db.session.add(system)
    db.session.commit()


@pytest.fixture
def system_with_test_group():
    system = System(
        id=3,
        tenant_id=1,
        inventory_id='99999999-d97e-4ed0-9095-ef07d73b4839',
        display_name='ip-181-33-34-35.ap-north-1.compute.internal',
        fqdn='ip-181-33-34-35.ap-north-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        state='Idling',
        region='ap-north-1',
        operating_system={"name": "RHEL", "major": 8, "minor": 9},
        cpu_states=['CPU_UNDERSIZED', 'CPU_UNDERSIZED_BY_PRESSURE'],
        io_states=['IO_UNDERSIZED_BY_PRESSURE'],
        memory_states=['MEMORY_UNDERSIZED', 'MEMORY_UNDERSIZED_BY_PRESSURE'],
        groups=[{"id": "abcdefgh-d97e-4ed0-9095-ef07d73b4839", "name": "test-group"}]
    )
    db.session.add(system)
    db.session.commit()


@pytest.fixture
def create_performance_profiles():
    for sys_id in range(2, 4):
        db_create_performance_profile(sys_id)


def db_create_performance_profile(sys_id):

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
        system_id=sys_id,
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
