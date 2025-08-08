"""
Test fixtures for Rules Engine testing.

This module provides comprehensive test data and fixtures for testing
the rules engine components including mock data for various system states
and performance metrics.
"""

import pytest
from unittest.mock import Mock
from collections import namedtuple


# CloudInstance namedtuple for consistent testing
CloudInstance = namedtuple(
    'CloudInstance', ['provider', 'type', 'mic', 'region']
)


@pytest.fixture
def mock_cloud_instance_aws():
    """Mock AWS cloud instance metadata."""
    return CloudInstance(
        provider="aws",
        type="t2.micro",
        mic=None,
        region="us-east-1"
    )


@pytest.fixture
def mock_cloud_instance_aws_larger():
    """Mock larger AWS cloud instance metadata."""
    return CloudInstance(
        provider="aws",
        type="m5.large",
        mic=None,
        region="us-west-2"
    )


@pytest.fixture
def mock_pmlog_summary_idle():
    """Mock PmLogSummary data for idle system."""
    mock_pm = Mock()

    # Setup hinv data
    mock_pm.get.return_value = {'ncpu': {'val': 2.0}}

    # Setup detailed performance data
    mock_pm.__getitem__ = Mock(side_effect=lambda key: {
        'hinv': {'ncpu': {'val': 2.0}},
        'kernel': {
            'all': {
                'cpu': {'idle': {'val': 1.95}},  # Very idle system
                'pressure': {
                    'io': {
                        'some': {'avg': {'1 minute': {'val': 0.1}}},
                        'full': {'avg': {'1 minute': {'val': 0.0}}}
                    },
                    'cpu': {
                        'some': {'avg': {'1 minute': {'val': 0.5}}}
                    },
                    'memory': {
                        'some': {'avg': {'1 minute': {'val': 0.2}}},
                        'full': {'avg': {'1 minute': {'val': 0.0}}}
                    }
                }
            }
        },
        'mem': {
            'physmem': {'val': 1000.0},
            'util': {'available': {'val': 950.0}}  # Very low memory usage
        },
        'disk': {
            'dev': {
                'total': {
                    'xvda': {'val': 5.0},  # Very low I/O
                    'xvdb': {'val': 2.0}
                }
            }
        }
    }[key])

    return mock_pm


@pytest.fixture
def mock_pmlog_summary_undersized():
    """Mock PmLogSummary data for undersized system."""
    mock_pm = Mock()

    # Setup hinv data
    mock_pm.get.return_value = {'ncpu': {'val': 2.0}}

    # Setup detailed performance data for high utilization
    mock_pm.__getitem__ = Mock(side_effect=lambda key: {
        'hinv': {'ncpu': {'val': 2.0}},
        'kernel': {
            'all': {
                'cpu': {'idle': {'val': 0.2}},  # Very busy system
                'pressure': {
                    'io': {
                        'some': {
                            'avg': {'1 minute': {'val': 25.0}}
                        },  # High I/O pressure
                        'full': {'avg': {'1 minute': {'val': 5.0}}}
                    },
                    'cpu': {
                        'some': {
                            'avg': {'1 minute': {'val': 30.0}}
                        }  # High CPU pressure
                    },
                    'memory': {
                        'some': {
                            'avg': {'1 minute': {'val': 25.0}}
                        },  # High memory pressure
                        'full': {'avg': {'1 minute': {'val': 2.0}}}
                    }
                }
            }
        },
        'mem': {
            'physmem': {'val': 1000.0},
            'util': {'available': {'val': 50.0}}  # Very high memory usage
        },
        'disk': {
            'dev': {
                'total': {
                    'xvda': {'val': 1000.0},  # Very high I/O
                    'xvdb': {'val': 800.0}
                }
            }
        }
    }[key])

    return mock_pm


@pytest.fixture
def mock_pmlog_summary_oversized():
    """Mock PmLogSummary data for oversized system."""
    mock_pm = Mock()

    # Setup hinv data
    mock_pm.get.return_value = {'ncpu': {'val': 8.0}}

    # Setup detailed performance data for very low utilization
    mock_pm.__getitem__ = Mock(side_effect=lambda key: {
        'hinv': {'ncpu': {'val': 8.0}},
        'kernel': {
            'all': {
                'cpu': {'idle': {'val': 7.8}},  # Very low CPU usage
                'pressure': {
                    'io': {
                        'some': {'avg': {'1 minute': {'val': 1.0}}},
                        'full': {'avg': {'1 minute': {'val': 0.0}}}
                    },
                    'cpu': {
                        'some': {'avg': {'1 minute': {'val': 1.0}}}
                    },
                    'memory': {
                        'some': {'avg': {'1 minute': {'val': 1.0}}},
                        'full': {'avg': {'1 minute': {'val': 0.0}}}
                    }
                }
            }
        },
        'mem': {
            'physmem': {'val': 16000.0},
            'util': {'available': {'val': 15000.0}}  # Very low memory usage
        },
        'disk': {
            'dev': {
                'total': {
                    'xvda': {'val': 10.0},  # Very low I/O
                    'xvdb': {'val': 5.0}
                }
            }
        }
    }[key])

    return mock_pm


@pytest.fixture
def mock_pmlog_summary_optimized():
    """Mock PmLogSummary data for optimized system."""
    mock_pm = Mock()

    # Setup hinv data
    mock_pm.get.return_value = {'ncpu': {'val': 2.0}}

    # Setup detailed performance data for optimal utilization
    mock_pm.__getitem__ = Mock(side_effect=lambda key: {
        'hinv': {'ncpu': {'val': 2.0}},
        'kernel': {
            'all': {
                'cpu': {'idle': {'val': 1.0}},  # 50% CPU usage - optimal
                'pressure': {
                    'io': {
                        'some': {'avg': {'1 minute': {'val': 10.0}}},
                        'full': {'avg': {'1 minute': {'val': 0.0}}}
                    },
                    'cpu': {
                        'some': {'avg': {'1 minute': {'val': 10.0}}}
                    },
                    'memory': {
                        'some': {'avg': {'1 minute': {'val': 10.0}}},
                        'full': {'avg': {'1 minute': {'val': 0.0}}}
                    }
                }
            }
        },
        'mem': {
            'physmem': {'val': 1000.0},
            'util': {'available': {'val': 400.0}}  # 60% memory usage - optimal
        },
        'disk': {
            'dev': {
                'total': {
                    'xvda': {'val': 100.0},  # Moderate I/O
                    'xvdb': {'val': 80.0}
                }
            }
        }
    }[key])

    return mock_pm


@pytest.fixture
def mock_lscpu():
    """Mock LsCPU parser data."""
    mock_lscpu = Mock()
    mock_lscpu.info = {
        'CPUs': '2',
        'Architecture': 'x86_64',
        'CPU MHz': '2400.000',
        'Model name': 'Intel(R) Xeon(R) CPU'
    }
    return mock_lscpu


@pytest.fixture
def mock_cmdline_psi_enabled():
    """Mock CmdLine with PSI enabled."""
    mock_cmdline = Mock()
    mock_cmdline.__contains__ = Mock(return_value=True)
    mock_cmdline.__getitem__ = Mock(return_value=['1'])
    return mock_cmdline


@pytest.fixture
def mock_cmdline_psi_disabled():
    """Mock CmdLine with PSI disabled."""
    mock_cmdline = Mock()
    mock_cmdline.__contains__ = Mock(return_value=True)
    mock_cmdline.__getitem__ = Mock(return_value=['0'])
    return mock_cmdline


@pytest.fixture
def mock_insights_client_conf_ros_enabled():
    """Mock InsightsClientConf with ROS enabled."""
    mock_conf = Mock()
    mock_conf.has_option.return_value = True
    mock_conf.getboolean.return_value = True
    return mock_conf


@pytest.fixture
def mock_insights_client_conf_ros_disabled():
    """Mock InsightsClientConf with ROS disabled."""
    mock_conf = Mock()
    mock_conf.has_option.return_value = False
    mock_conf.getboolean.return_value = False
    return mock_conf


@pytest.fixture
def mock_aws_instance_doc():
    """Mock AWS instance document."""
    return {
        'instanceType': 't2.micro',
        'region': 'us-east-1',
        'instanceId': 'i-1234567890abcdef0',
        'accountId': '123456789012'
    }


@pytest.fixture
def mock_cloud_provider_aws():
    """Mock CloudProvider for AWS."""
    mock_cp = Mock()
    mock_cp.cloud_provider = "aws"
    mock_cp.AWS = "aws"
    return mock_cp


@pytest.fixture
def mock_rhel_release():
    """Mock RHEL release information."""
    mock_rhel = Mock()
    mock_rhel.rhel = "8.4"
    mock_rhel.major = 8
    mock_rhel.minor = 4
    return mock_rhel


@pytest.fixture
def mock_ec2_instance_types():
    """Mock EC2 instance types data."""
    return {
        "t2.nano": {
            "ram": 0.5,
            "extra": {
                "vcpu": "1",
                "physicalProcessor": "Intel Xeon Family"
            }
        },
        "t2.micro": {
            "ram": 1,
            "extra": {
                "vcpu": "1",
                "physicalProcessor": "Intel Xeon Family"
            }
        },
        "t2.small": {
            "ram": 2,
            "extra": {
                "vcpu": "1",
                "physicalProcessor": "Intel Xeon Family"
            }
        },
        "t2.medium": {
            "ram": 4,
            "extra": {
                "vcpu": "2",
                "physicalProcessor": "Intel Xeon Family"
            }
        },
        "t2.large": {
            "ram": 8,
            "extra": {
                "vcpu": "2",
                "physicalProcessor": "Intel Xeon Family"
            }
        },
        "m5.large": {
            "ram": 8,
            "extra": {
                "vcpu": "2",
                "physicalProcessor": "Intel Xeon Platinum 8175"
            }
        },
        "m5.xlarge": {
            "ram": 16,
            "extra": {
                "vcpu": "4",
                "physicalProcessor": "Intel Xeon Platinum 8175"
            }
        }
    }


@pytest.fixture
def mock_ec2_pricing():
    """Mock EC2 pricing data."""
    return {
        "t2.nano": {"us-east-1": 0.0058, "us-west-2": 0.0059},
        "t2.micro": {"us-east-1": 0.0116, "us-west-2": 0.0118},
        "t2.small": {"us-east-1": 0.023, "us-west-2": 0.0235},
        "t2.medium": {"us-east-1": 0.0464, "us-west-2": 0.0472},
        "t2.large": {"us-east-1": 0.0928, "us-west-2": 0.0944},
        "m5.large": {"us-east-1": 0.096, "us-west-2": 0.098},
        "m5.xlarge": {"us-east-1": 0.192, "us-west-2": 0.196}
    }


@pytest.fixture
def sample_rule_hit_idle():
    """Sample rule hit data for idle system."""
    return [{
        "key": "INSTANCE_IDLE",
        "tags": [],
        "type": "rule",
        "links": {
            "kcs": [],
            "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]
        },
        "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.0116,
            "region": "us-east-1",
            "states": {"idle": ["IDLE"]},
            "error_key": "INSTANCE_IDLE",
            "candidates": [
                ["t2.nano", 0.0058]
            ],
            "instance_type": "t2.micro",
            "cloud_provider": "aws"
        },
        "rule_id": "ros_instance_evaluation|INSTANCE_IDLE",
        "component": (
            "telemetry.rules.plugins.ros.ros_instance_evaluation.report"
        )
    }]


@pytest.fixture
def sample_rule_hit_undersized():
    """Sample rule hit data for undersized system."""
    return [{
        "key": "INSTANCE_UNDERSIZED",
        "tags": [],
        "type": "rule",
        "links": {
            "kcs": [],
            "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]
        },
        "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.0116,
            "region": "us-east-1",
            "states": {
                "cpu": ["CPU_UNDERSIZED", "CPU_UNDERSIZED_BY_PRESSURE"],
                "memory": [
                    "MEMORY_UNDERSIZED",
                    "MEMORY_UNDERSIZED_BY_PRESSURE"
                ],
                "io": ["IO_UNDERSIZED_BY_PRESSURE"]
            },
            "error_key": "INSTANCE_UNDERSIZED",
            "candidates": [
                ["t2.medium", 0.0464],
                ["t2.large", 0.0928],
                ["m5.large", 0.096]
            ],
            "instance_type": "t2.micro",
            "cloud_provider": "aws"
        },
        "rule_id": "ros_instance_evaluation|INSTANCE_UNDERSIZED",
        "component": (
            "telemetry.rules.plugins.ros.ros_instance_evaluation.report"
        )
    }]


@pytest.fixture
def sample_rule_hit_oversized():
    """Sample rule hit data for oversized system."""
    return [{
        "key": "INSTANCE_OVERSIZED",
        "tags": [],
        "type": "rule",
        "links": {
            "kcs": [],
            "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]
        },
        "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.192,
            "region": "us-east-1",
            "states": {
                "cpu": ["CPU_OVERSIZED"],
                "memory": ["MEMORY_OVERSIZED"],
                "io": ["IO_OVERSIZED"]
            },
            "error_key": "INSTANCE_OVERSIZED",
            "candidates": [
                ["t2.small", 0.023],
                ["t2.micro", 0.0116],
                ["t2.nano", 0.0058]
            ],
            "instance_type": "m5.xlarge",
            "cloud_provider": "aws"
        },
        "rule_id": "ros_instance_evaluation|INSTANCE_OVERSIZED",
        "component": (
            "telemetry.rules.plugins.ros.ros_instance_evaluation.report"
        )
    }]


@pytest.fixture
def sample_rule_hit_under_pressure():
    """Sample rule hit data for under pressure system."""
    return [{
        "key": "INSTANCE_OPTIMIZED_UNDER_PRESSURE",
        "tags": [],
        "type": "rule",
        "links": {
            "kcs": [],
            "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]
        },
        "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.0116,
            "region": "us-east-1",
            "states": {
                "cpu": ["CPU_UNDERSIZED_BY_PRESSURE"],
                "memory": ["MEMORY_UNDERSIZED_BY_PRESSURE"],
                "io": ["IO_UNDERSIZED_BY_PRESSURE"]
            },
            "error_key": "INSTANCE_OPTIMIZED_UNDER_PRESSURE",
            "candidates": [
                ["t2.small", 0.023],
                ["t2.medium", 0.0464]
            ],
            "instance_type": "t2.micro",
            "cloud_provider": "aws"
        },
        "rule_id": "ros_instance_evaluation|INSTANCE_OPTIMIZED_UNDER_PRESSURE",
        "component": (
            "telemetry.rules.plugins.ros.ros_instance_evaluation.report"
        )
    }]


@pytest.fixture
def sample_rule_hit_no_pcp():
    """Sample rule hit data for no PCP data."""
    return [{
        "key": "NO_PCP_DATA",
        "tags": [],
        "type": "rule",
        "links": {
            "kcs": [],
            "jira": ["https://issues.redhat.com/browse/CEECBA-5875"]
        },
        "details": {
            "rhel": "8.4",
            "type": "rule",
            "price": 0.0116,
            "region": "us-east-1",
            "error_key": "NO_PCP_DATA",
            "instance_type": "t2.micro",
            "cloud_provider": "aws"
        },
        "rule_id": "ros_instance_evaluation|NO_PCP_DATA",
        "component": (
            "telemetry.rules.plugins.ros."
            "ros_instance_evaluation.report_no_data"
        )
    }]


class MockSystemStateData:
    """Helper class to generate consistent system state test data."""

    @staticmethod
    def create_performance_record(cpu_idle=1.0, mem_available=500.0,
                                  mem_total=1000.0, io_vals=None,
                                  psi_data=None):
        """Create a performance record with specified values."""
        if io_vals is None:
            io_vals = {"xvda": 100.0, "xvdb": 50.0}

        if psi_data is None:
            psi_data = {
                "io_some": 10.0, "io_full": 0.0,
                "cpu_some": 5.0,
                "mem_some": 8.0, "mem_full": 0.0
            }

        return {
            "hinv.ncpu": 2.0,
            "total_cpus": 2,
            "mem.physmem": mem_total,
            "mem.util.available": mem_available,
            "kernel.all.cpu.idle": cpu_idle,
            "disk.dev.total": {
                dev: {"val": val, "units": "count / sec"}
                for dev, val in io_vals.items()
            },
            "kernel.all.pressure.io.some.avg": {
                "1 minute": {"val": psi_data["io_some"], "units": "none"}
            },
            "kernel.all.pressure.io.full.avg": {
                "1 minute": {"val": psi_data["io_full"], "units": "none"}
            },
            "kernel.all.pressure.cpu.some.avg": {
                "1 minute": {"val": psi_data["cpu_some"], "units": "none"}
            },
            "kernel.all.pressure.memory.some.avg": {
                "1 minute": {"val": psi_data["mem_some"], "units": "none"}
            },
            "kernel.all.pressure.memory.full.avg": {
                "1 minute": {"val": psi_data["mem_full"], "units": "none"}
            }
        }

    @staticmethod
    def create_performance_utilization(cpu_percent=50, mem_percent=50,
                                       io_vals=None):
        """Create performance utilization with specified percentages."""
        if io_vals is None:
            io_vals = {"xvda": 100.0, "xvdb": 50.0}

        max_io = max(io_vals.values()) if io_vals else 0.0

        return {
            "cpu": cpu_percent,
            "memory": mem_percent,
            "io": io_vals,
            "max_io": max_io
        }


@pytest.fixture
def mock_system_state_data():
    """Provide MockSystemStateData helper class."""
    return MockSystemStateData
