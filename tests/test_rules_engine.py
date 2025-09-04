"""
Unit tests for the Rules Engine module.

This module tests all components of the rules engine including:
- Condition functions (cloud_metadata, cpu_utilization, mem_utilization, etc.)
- Evaluation functions (cpu_evaluation, mem_evaluation, psi_evaluation, etc.)
- Candidate functions (cpu_candidates, mem_candidates, io_candidates)
- Rule functions (report_metadata, report)
- Utility functions
"""

import pytest
from unittest.mock import Mock, patch

from insights import SkipComponent

from ros.rules import rules_engine
from ros.rules.helpers.rules_data import RosKeys, RosThresholds
from ros.processor.insights_engine_consumer import (
    topmost_candidate_from_rule_hit
)

# Import fixtures
pytest_plugins = ["tests.fixtures.rules_engine_fixtures"]


class TestCloudMetadata:
    """Test cloud_metadata condition function."""

    def test_cloud_metadata_aws_success(self, mock_cloud_provider_aws, mock_aws_instance_doc):
        """Test successful AWS cloud metadata extraction."""
        azure = None  # ROS only supports AWS

        result = rules_engine.cloud_metadata(mock_cloud_provider_aws, mock_aws_instance_doc, azure)

        assert result.provider == "aws"
        assert result.type == "t2.micro"
        assert result.mic is None  # IOPS issue mentioned in code
        assert result.region == "us-east-1"

    def test_cloud_metadata_unsupported_provider(self):
        """Test that unsupported cloud providers (non-AWS) raise SkipComponent."""
        cp = Mock()
        cp.cloud_provider = "gcp"  # Only AWS is supported by ROS
        cp.AWS = "aws"

        aws = {'instanceType': 't2.micro', 'region': 'us-east-1'}
        azure = None

        with pytest.raises(SkipComponent):
            rules_engine.cloud_metadata(cp, aws, azure)


class TestNopmlogSummary:
    """Test no_pmlog_summary condition function."""

    def test_no_pmlog_summary_with_ros_collect_enabled(self, mock_insights_client_conf_ros_enabled):
        """Test when ros_collect is enabled but no pmlog summary."""
        new_pm = None

        result = rules_engine.no_pmlog_summary(mock_insights_client_conf_ros_enabled, new_pm)
        assert result == "NO_PCP_DATA"

    def test_no_pmlog_summary_with_data_available(self, mock_insights_client_conf_ros_enabled):
        """Test when pmlog summary is available - should skip."""
        new_pm = Mock()  # Data is available

        with pytest.raises(SkipComponent):
            rules_engine.no_pmlog_summary(mock_insights_client_conf_ros_enabled, new_pm)

    def test_no_pmlog_summary_ros_collect_disabled(self, mock_insights_client_conf_ros_disabled):
        """Test when ros_collect is disabled - should skip."""
        new_pm = None

        with pytest.raises(SkipComponent):
            rules_engine.no_pmlog_summary(mock_insights_client_conf_ros_disabled, new_pm)


class TestCpuUtilization:
    """Test cpu_utilization condition function."""

    def test_cpu_utilization_from_pmlog(self):
        """Test CPU utilization calculation from pmlog data."""
        new_pm = Mock()
        new_pm.get.return_value = {'ncpu': {'val': 2.0}}
        new_pm.__getitem__ = Mock(side_effect=lambda key: {
            'hinv': {'ncpu': {'val': 2.0}},
            'kernel': {'all': {'cpu': {'idle': {'val': 1.6}}}}
        }[key])

        lscpu = None

        result = rules_engine.cpu_utilization(new_pm, lscpu)

        cpu_ut, idle = result
        assert cpu_ut == pytest.approx(0.2)  # 1.0 - (1.6 / 2.0) ~ 0.2
        assert idle == 1.6

    def test_cpu_utilization_with_lscpu_fallback(self, mock_lscpu):
        """Test CPU utilization with LsCPU fallback when pmlog has no ncpu."""
        new_pm = Mock()
        new_pm.get.return_value = {'ncpu': {'val': None}}
        new_pm.__getitem__ = Mock(side_effect=lambda key: {
            'hinv': {'ncpu': {'val': None}},
            'kernel': {'all': {'cpu': {'idle': {'val': 1.5}}}}
        }[key])

        # Update mock_lscpu to have CPUs field for this test
        mock_lscpu.info['CPUs'] = '4'

        result = rules_engine.cpu_utilization(new_pm, mock_lscpu)

        cpu_ut, idle = result
        assert cpu_ut == 0.625  # 1.0 - (1.5 / 4.0) = 0.625
        assert idle == 1.5

    def test_cpu_utilization_missing_data(self):
        """Test CPU utilization when data is missing."""
        new_pm = Mock()
        new_pm.get.side_effect = Exception("Missing data")

        lscpu = None

        with pytest.raises(SkipComponent):
            rules_engine.cpu_utilization(new_pm, lscpu)


class TestMemUtilization:
    """Test mem_utilization condition function."""

    def test_mem_utilization_success(self):
        """Test successful memory utilization calculation."""
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=lambda key: {
            'mem': {
                'physmem': {'val': 1000.0},
                'util': {'available': {'val': 300.0}}
            }
        }[key])

        result = rules_engine.mem_utilization(new_pm)

        mem_ut, in_use = result
        assert mem_ut == 0.7  # (1000 - 300) / 1000 = 0.7
        assert in_use == 700.0  # 1000 - 300

    def test_mem_utilization_missing_data(self):
        """Test memory utilization when data is missing."""
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=Exception("Missing data"))

        with pytest.raises(SkipComponent):
            rules_engine.mem_utilization(new_pm)


class TestIoUtilization:
    """Test io_utilization condition function."""

    def test_io_utilization_success(self):
        """Test successful I/O utilization calculation."""
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=lambda key: {
            'disk': {
                'dev': {
                    'total': {
                        'sda': {'val': 100.5},
                        'sdb': {'val': 200.7}
                    }
                }
            }
        }[key])

        cm = Mock()  # CloudInstance metadata

        result = rules_engine.io_utilization(new_pm, cm)

        assert result == {'sda': 100.5, 'sdb': 200.7}

    def test_io_utilization_missing_data(self):
        """Test I/O utilization when data is missing."""
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=Exception("Missing data"))

        cm = Mock()

        with pytest.raises(SkipComponent):
            rules_engine.io_utilization(new_pm, cm)


class TestPsiEnabled:
    """Test psi_enabled condition function."""

    def test_psi_enabled_true(self, mock_cmdline_psi_enabled):
        """Test PSI enabled when psi=1 in cmdline."""
        result = rules_engine.psi_enabled(mock_cmdline_psi_enabled)
        assert result is True

    def test_psi_enabled_false(self, mock_cmdline_psi_disabled):
        """Test PSI disabled when psi=0 in cmdline."""
        result = rules_engine.psi_enabled(mock_cmdline_psi_disabled)
        assert result is False

    def test_psi_not_in_cmdline(self):
        """Test PSI when not in cmdline."""
        cmdline = Mock()
        cmdline.__contains__ = Mock(return_value=False)

        result = rules_engine.psi_enabled(cmdline)
        assert result is False


class TestPsiUtilization:
    """Test psi_utilization condition function."""

    def test_psi_utilization_enabled(self):
        """Test PSI utilization when PSI is enabled."""
        psi = True
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=lambda key: {
            'kernel': {
                'all': {
                    'pressure': {
                        'io': {
                            'some': {'avg': {'1 minute': {'val': 10.5}}},
                            'full': {'avg': {'1 minute': {'val': 5.2}}}
                        },
                        'cpu': {
                            'some': {'avg': {'1 minute': {'val': 15.3}}}
                        },
                        'memory': {
                            'some': {'avg': {'1 minute': {'val': 8.7}}},
                            'full': {'avg': {'1 minute': {'val': 3.1}}}
                        }
                    }
                }
            }
        }[key])

        result = rules_engine.psi_utilization(psi, new_pm)

        io_avg, io_full, cpu_avg, mem_avg, mem_full = result
        assert io_avg == 10.5
        assert io_full == 5.2
        assert cpu_avg == 15.3
        assert mem_avg == 8.7
        assert mem_full == 3.1

    def test_psi_utilization_disabled(self):
        """Test PSI utilization when PSI is disabled."""
        psi = False
        new_pm = Mock()

        with pytest.raises(SkipComponent):
            rules_engine.psi_utilization(psi, new_pm)


class TestEvaluationFunctions:
    """Test evaluation functions for idle, CPU, memory, I/O, and PSI."""

    def test_idle_evaluation_true(self):
        """Test idle evaluation when system is idle."""
        cpu = (0.03, 1.97)  # Low CPU utilization
        mem = (0.03, 100.0)  # Low memory utilization

        result = rules_engine.idle_evaluation(cpu, mem)
        assert result == RosKeys.IDLE

    def test_idle_evaluation_false_high_cpu(self):
        """Test idle evaluation when CPU is not idle."""
        cpu = (0.6, 0.4)  # High CPU utilization
        mem = (0.03, 100.0)  # Low memory utilization

        result = rules_engine.idle_evaluation(cpu, mem)
        assert result == RosKeys.OPTIMIZED

    def test_idle_evaluation_false_high_memory(self):
        """Test idle evaluation when memory is not idle."""
        cpu = (0.03, 1.97)  # Low CPU utilization
        mem = (0.6, 800.0)  # High memory utilization

        result = rules_engine.idle_evaluation(cpu, mem)
        assert result == RosKeys.OPTIMIZED

    def test_cpu_evaluation_undersized(self):
        """Test CPU evaluation for undersized condition."""
        cpu_ut = (0.9, 0.1)  # High CPU utilization (90%)

        result, idle = rules_engine.cpu_evaluation(cpu_ut)
        assert result & RosKeys.CPU_UNDERSIZED
        assert idle == 0.1

    def test_cpu_evaluation_oversized(self):
        """Test CPU evaluation for oversized condition."""
        cpu_ut = (0.1, 1.9)  # Low CPU utilization (10%)

        result, idle = rules_engine.cpu_evaluation(cpu_ut)
        assert result & RosKeys.CPU_OVERSIZED
        assert idle == 1.9

    def test_cpu_evaluation_optimized(self):
        """Test CPU evaluation for optimized condition."""
        cpu_ut = (0.5, 1.0)  # Optimal CPU utilization (50%)

        result, idle = rules_engine.cpu_evaluation(cpu_ut)
        assert result == RosKeys.OPTIMIZED
        assert idle == 1.0

    def test_mem_evaluation_undersized(self):
        """Test memory evaluation for undersized condition."""
        mem_ut = (0.9, 900.0)  # High memory utilization (90%)

        result, in_use = rules_engine.mem_evaluation(mem_ut)
        assert result & RosKeys.MEMORY_UNDERSIZED
        assert in_use == 900.0

    def test_mem_evaluation_oversized(self):
        """Test memory evaluation for oversized condition."""
        mem_ut = (0.1, 100.0)  # Low memory utilization (10%)

        result, in_use = rules_engine.mem_evaluation(mem_ut)
        assert result & RosKeys.MEMORY_OVERSIZED
        assert in_use == 100.0

    def test_psi_evaluation_memory_pressure(self):
        """Test PSI evaluation for memory pressure."""
        # io_avg, io_full, cpu_avg, mem_avg, mem_full
        psi_ut = (5.0, 0.0, 5.0, 25.0, 5.0)  # High memory pressure

        result = rules_engine.psi_evaluation(psi_ut)
        assert result & RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE

    def test_psi_evaluation_cpu_pressure(self):
        """Test PSI evaluation for CPU pressure."""
        psi_ut = (5.0, 0.0, 25.0, 5.0, 0.0)  # High CPU pressure

        result = rules_engine.psi_evaluation(psi_ut)
        assert result & RosKeys.CPU_UNDERSIZED_BY_PRESSURE

    def test_psi_evaluation_io_pressure(self):
        """Test PSI evaluation for I/O pressure."""
        psi_ut = (25.0, 5.0, 5.0, 5.0, 0.0)  # High I/O pressure

        result = rules_engine.psi_evaluation(psi_ut)
        assert result & RosKeys.IO_UNDERSIZED_BY_PRESSURE


class TestCandidateFunctions:
    """Test candidate generation functions."""

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    def test_cpu_candidates_undersized(self, mock_instances, mock_cloud_instance_aws, mock_ec2_instance_types):
        """Test CPU candidate generation for undersized instances."""
        # Use the comprehensive fixtures
        mock_instances.get.return_value = mock_ec2_instance_types["t2.micro"]
        mock_instances.items.return_value = mock_ec2_instance_types.items()

        # Mock CPU evaluation (undersized)
        cpu_ut = (RosKeys.CPU_UNDERSIZED, 0.9)

        # Mock PSI evaluation
        psi_ut = RosKeys.OPTIMIZED

        result_ut, candidates = rules_engine.cpu_candidates(mock_cloud_instance_aws, cpu_ut, psi_ut)

        assert result_ut & RosKeys.CPU_UNDERSIZED
        # Should include larger instances with same processor type
        assert isinstance(candidates, set)

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    def test_mem_candidates_undersized(self, mock_instances, mock_cloud_instance_aws, mock_ec2_instance_types):
        """Test memory candidate generation for undersized instances."""
        # Use the comprehensive fixtures
        mock_instances.get.return_value = mock_ec2_instance_types["t2.micro"]
        mock_instances.items.return_value = mock_ec2_instance_types.items()

        # Mock memory evaluation (undersized)
        mem_ut = (RosKeys.MEMORY_UNDERSIZED, 900.0)  # 900 MB in use

        # Mock PSI evaluation
        psi_ut = RosKeys.OPTIMIZED

        result_ut, candidates = rules_engine.mem_candidates(mock_cloud_instance_aws, mem_ut, psi_ut)

        assert result_ut & RosKeys.MEMORY_UNDERSIZED
        assert isinstance(candidates, set)

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    def test_io_candidates(self, mock_instances, mock_cloud_instance_aws, mock_ec2_instance_types):
        """Test I/O candidate generation."""
        # Use the comprehensive fixtures
        mock_instances.keys.return_value = mock_ec2_instance_types.keys()

        # Mock I/O evaluation
        io_ut = RosKeys.OPTIMIZED

        result_ut, candidates = rules_engine.io_candidates(mock_cloud_instance_aws, io_ut)

        assert result_ut == RosKeys.OPTIMIZED
        assert isinstance(candidates, set)
        assert len(candidates) == len(mock_ec2_instance_types)  # All instance types returned


class TestFindSolution:
    """Test find_solution function that combines all evaluations."""

    @patch('ros.rules.rules_engine.Ec2LinuxPrices')
    def test_find_solution_idle(self, mock_pricing, mock_cloud_instance_aws, mock_ec2_pricing):
        """Test find solution for idle system."""
        # Mock pricing using fixture
        mock_pricing.return_value.get.return_value = mock_ec2_pricing["t2.micro"]

        # Mock evaluations
        cpu = (RosKeys.CPU_OVERSIZED, {"t2.nano", "t2.small"})
        mem = (RosKeys.MEMORY_OVERSIZED, {"t2.nano", "t2.small"})
        io = (RosKeys.OPTIMIZED, {"t2.nano", "t2.small"})
        idle = RosKeys.IDLE
        psi = RosKeys.OPTIMIZED

        result = rules_engine.find_solution(mock_cloud_instance_aws, cpu, mem, io, idle, psi)

        err_key, cur_price, states, solution_w_price = result
        assert err_key == "INSTANCE_IDLE"
        assert cur_price == mock_ec2_pricing["t2.micro"]["us-east-1"]
        assert isinstance(states, dict)
        assert isinstance(solution_w_price, list)

    @patch('ros.rules.rules_engine.Ec2LinuxPrices')
    def test_find_solution_undersized(self, mock_pricing, mock_cloud_instance_aws, mock_ec2_pricing):
        """Test find solution for undersized system."""
        # Mock pricing using fixture
        mock_pricing.return_value.get.return_value = mock_ec2_pricing["t2.micro"]

        # Mock evaluations
        cpu = (RosKeys.CPU_UNDERSIZED, {"t2.small", "t2.medium"})
        mem = (RosKeys.MEMORY_UNDERSIZED, {"t2.small", "t2.medium"})
        io = (RosKeys.OPTIMIZED, {"t2.small", "t2.medium"})
        idle = RosKeys.OPTIMIZED
        psi = RosKeys.OPTIMIZED

        result = rules_engine.find_solution(mock_cloud_instance_aws, cpu, mem, io, idle, psi)

        err_key, cur_price, states, solution_w_price = result
        assert err_key == "INSTANCE_UNDERSIZED"
        assert cur_price == mock_ec2_pricing["t2.micro"]["us-east-1"]
        assert isinstance(states, dict)
        assert isinstance(solution_w_price, list)


class TestRuleFunctions:
    """Test rule functions that generate the final reports."""

    def test_report_metadata(self, mock_rhel_release, mock_cloud_instance_aws):
        """Test report_metadata rule function."""
        psi = True
        cpu = (0.5, 1.0)
        mem = (0.7, 700.0)
        io = {"sda": 100.5, "sdb": 200.7}
        sys_id = "1671dcb3-821c-4a28-8b40-1c735f0c0014"

        result = rules_engine.report_metadata(mock_rhel_release, mock_cloud_instance_aws, psi, cpu, mem, io, sys_id)

        # Should return make_metadata result
        assert result is not None

    def test_report_rule(self, mock_rhel_release, mock_cloud_instance_aws):
        """Test report rule function."""
        solution = (
            "INSTANCE_UNDERSIZED",  # error_key
            0.0116,  # current price
            {"cpu": ["CPU_UNDERSIZED"]},  # states
            [("t2.small", 0.023)]  # candidates with prices
        )

        result = rules_engine.report(mock_rhel_release, mock_cloud_instance_aws, solution)

        # Should return make_fail result
        assert result is not None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_readable_evaluation_idle(self):
        """Test readable_evaluation for idle state."""
        ret = RosKeys.IDLE

        err_key, states = rules_engine.readable_evalution(ret)

        assert err_key == "INSTANCE_IDLE"
        assert "idle" in states
        assert "IDLE" in states["idle"]

    def test_readable_evaluation_undersized(self):
        """Test readable_evaluation for undersized state."""
        ret = RosKeys.CPU_UNDERSIZED | RosKeys.MEMORY_UNDERSIZED

        err_key, states = rules_engine.readable_evalution(ret)

        assert err_key == "INSTANCE_UNDERSIZED"
        assert "cpu" in states
        assert "memory" in states

    def test_readable_evaluation_oversized(self):
        """Test readable_evaluation for oversized state."""
        ret = (RosKeys.CPU_OVERSIZED | RosKeys.MEMORY_OVERSIZED |
               RosKeys.IO_OVERSIZED)

        err_key, states = rules_engine.readable_evalution(ret)

        assert err_key == "INSTANCE_OVERSIZED"
        assert "cpu" in states
        assert "memory" in states
        assert "io" in states

    def test_readable_evaluation_under_pressure(self):
        """Test readable_evaluation for under pressure state."""
        ret = RosKeys.CPU_UNDERSIZED_BY_PRESSURE

        err_key, states = rules_engine.readable_evalution(ret)

        assert err_key == "INSTANCE_OPTIMIZED_UNDER_PRESSURE"
        assert "cpu" in states

    def test_topmost_candidate_optimized(self):
        """Test topmost_candidate_from_rule_hit for optimized state."""
        reports = []
        state_key = "OPTIMIZED"

        result = topmost_candidate_from_rule_hit(reports, state_key)

        assert result == [None, None]

    def test_topmost_candidate_no_pcp_data(self):
        """Test topmost_candidate_from_rule_hit for no PCP data state."""
        reports = []
        state_key = "NO_PCP_DATA"

        result = topmost_candidate_from_rule_hit(reports, state_key)

        assert result == [None, None]

    def test_topmost_candidate_with_data(self):
        """Test topmost_candidate_from_rule_hit with actual data."""
        reports = [{
            'details': {
                'candidates': [
                    ['t2.small', 0.023],
                    ['t2.medium', 0.046]
                ]
            }
        }]
        state_key = "INSTANCE_UNDERSIZED"

        result = topmost_candidate_from_rule_hit(reports, state_key)

        assert result == ['t2.small', 0.023]


class TestRunRules:
    """Test the main run_rules function."""

    @patch('ros.rules.rules_engine.insights_run')
    def test_run_rules(self, mock_insights_run):
        """Test run_rules function execution."""
        # Mock insights_run return value
        mock_insights_run.return_value = {
            'report_metadata': {'result': 'metadata'},
            'report': {'result': 'report'},
            'performance_profile_rules': {'result': 'metadata'},
        }

        extracted_dir_root = "/path/to/extracted"

        result = rules_engine.run_rules(extracted_dir_root)

        mock_insights_run.assert_called_once()
        args, kwargs = mock_insights_run.call_args
        assert len(args[0]) == 3  # Three rules: [report_metadata, report, performance_profile_rules
        assert kwargs['root'] == extracted_dir_root
        assert result == mock_insights_run.return_value


class TestRosThresholds:
    """Test that ROS thresholds are properly defined."""

    def test_memory_thresholds(self):
        """Test memory threshold constants."""
        assert RosThresholds.MEMORY_UTILIZATION_WARNING_UPPER_THRESHOLD == 0.8
        assert RosThresholds.MEMORY_UTILIZATION_WARNING_LOWER_THRESHOLD == 0.2
        assert (RosThresholds.MEMORY_UTILIZATION_CRITICAL_UPPER_THRESHOLD
                == 0.95)
        assert (RosThresholds.MEMORY_UTILIZATION_CRITICAL_LOWER_THRESHOLD
                == 0.05)
        assert RosThresholds.MEMORY_PRESSURE_UPPER_AVERAGE_THRESHOLD == 20.0
        assert RosThresholds.MEMORY_PRESSURE_FULL_THRESHOLD == 0.0

    def test_cpu_thresholds(self):
        """Test CPU threshold constants."""
        assert RosThresholds.CPU_UTILIZATION_WARNING_UPPER_THRESHOLD == 0.8
        assert RosThresholds.CPU_UTILIZATION_WARNING_LOWER_THRESHOLD == 0.2
        assert RosThresholds.CPU_UTILIZATION_CRITICAL_UPPER_THRESHOLD == 0.95
        assert RosThresholds.CPU_UTILIZATION_CRITICAL_LOWER_THRESHOLD == 0.05
        assert RosThresholds.CPU_PRESSURE_UPPER_AVERAGE_THRESHOLD == 20.0

    def test_io_thresholds(self):
        """Test I/O threshold constants."""
        assert RosThresholds.IO_UTILIZATION_WARNING_UPPER_THRESHOLD == 0.8
        assert RosThresholds.IO_UTILIZATION_WARNING_LOWER_THRESHOLD == 0.2
        assert RosThresholds.IO_UTILIZATION_CRITICAL_UPPER_THRESHOLD == 0.95
        assert RosThresholds.IO_UTILIZATION_CRITICAL_LOWER_THRESHOLD == 0.05
        assert RosThresholds.IO_PRESSURE_UPPER_AVERAGE_THRESHOLD == 20.0
        assert RosThresholds.IO_PRESSURE_FULL_THRESHOLD == 0.0


class TestRosKeys:
    """Test that ROS keys are properly defined."""

    def test_ros_keys_values(self):
        """Test ROS key flag values."""
        assert RosKeys.OPTIMIZED == 0
        assert RosKeys.MEMORY_OVERSIZED == 1
        assert RosKeys.MEMORY_UNDERSIZED == 2
        assert RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE == 4
        assert RosKeys.CPU_OVERSIZED == 8
        assert RosKeys.CPU_UNDERSIZED == 16
        assert RosKeys.CPU_UNDERSIZED_BY_PRESSURE == 32
        assert RosKeys.CPU_IDLING == 64
        assert RosKeys.IO_OVERSIZED == 128
        assert RosKeys.IO_UNDERSIZED == 256
        assert RosKeys.IO_UNDERSIZED_BY_PRESSURE == 512
        assert RosKeys.CONSUMPTION == 1024
        assert RosKeys.RIGHTSIZING == 2048
        assert RosKeys.IDLE == 4096

    def test_ros_keys_combinations(self):
        """Test ROS key flag combinations."""
        combined = RosKeys.CPU_UNDERSIZED | RosKeys.MEMORY_UNDERSIZED
        assert combined & RosKeys.CPU_UNDERSIZED
        assert combined & RosKeys.MEMORY_UNDERSIZED
        assert not (combined & RosKeys.CPU_OVERSIZED)


class TestErrorKeys:
    """Test error key constants."""

    def test_error_key_constants(self):
        """Test that error key constants are defined correctly."""
        assert rules_engine.ERROR_KEY_NO_DATA == "NO_PCP_DATA"
        assert rules_engine.ERROR_KEY_IDLE == "INSTANCE_IDLE"
        assert rules_engine.ERROR_KEY_OVERSIZED == "INSTANCE_OVERSIZED"
        assert rules_engine.ERROR_KEY_UNDERSIZED == "INSTANCE_UNDERSIZED"
        assert (rules_engine.ERROR_KEY_UNDER_PRESSURE ==
                "INSTANCE_OPTIMIZED_UNDER_PRESSURE")


if __name__ == '__main__':
    pytest.main([__file__])
