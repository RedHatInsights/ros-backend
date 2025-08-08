"""
Integration tests for the Rules Engine.

These tests verify the complete workflow of the rules engine,
testing the interaction between different components and the
end-to-end rule execution process.
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


class TestRulesEngineIntegration:
    """Integration tests for complete rules engine workflow."""

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    @patch('ros.rules.rules_engine.Ec2LinuxPrices')
    def test_complete_workflow_idle_system(self, mock_pricing, mock_instances,
                                           mock_rhel_release, mock_cloud_instance_aws,
                                           mock_ec2_instance_types, mock_ec2_pricing):
        """Test complete workflow for an idle system."""
        # Setup mocks using comprehensive fixtures
        mock_instances.get.return_value = mock_ec2_instance_types["t2.micro"]
        mock_instances.items.return_value = mock_ec2_instance_types.items()
        mock_instances.keys.return_value = mock_ec2_instance_types.keys()

        pricing_instance = Mock()
        pricing_instance.get.return_value = mock_ec2_pricing["t2.micro"]
        mock_pricing.return_value = pricing_instance

        # Mock performance data for idle system
        cpu_ut = (0.025, 1.975)  # Very low CPU utilization
        mem_ut = (0.04, 40.0)  # Very low memory utilization
        io_ut = {"xvda": 5.0}    # Low I/O
        psi_ut = (1.0, 0.0, 1.0, 2.0, 0.0)  # Low pressure values

        # Test CPU evaluation
        cpu_eval = rules_engine.cpu_evaluation(cpu_ut)
        assert cpu_eval[0] & RosKeys.CPU_OVERSIZED

        # Test memory evaluation
        mem_eval = rules_engine.mem_evaluation(mem_ut)
        assert mem_eval[0] & RosKeys.MEMORY_OVERSIZED

        # Test idle evaluation
        idle_eval = rules_engine.idle_evaluation(cpu_ut, mem_ut)
        assert idle_eval == RosKeys.IDLE

        # Test PSI evaluation
        psi_eval = rules_engine.psi_evaluation(psi_ut)
        assert psi_eval == RosKeys.OPTIMIZED  # No pressure

        # Test I/O evaluation
        io_eval = rules_engine.io_evaluation(io_ut)
        assert io_eval == RosKeys.OPTIMIZED

        # Test candidate generation
        cpu_candidates = rules_engine.cpu_candidates(mock_cloud_instance_aws, cpu_eval, psi_eval)
        mem_candidates = rules_engine.mem_candidates(mock_cloud_instance_aws, mem_eval, psi_eval)
        io_candidates = rules_engine.io_candidates(mock_cloud_instance_aws, io_eval)

        # Test find_solution
        solution = rules_engine.find_solution(
            mock_cloud_instance_aws, cpu_candidates, mem_candidates, io_candidates,
            idle_eval, psi_eval
        )

        err_key, cur_price, states, solution_w_price = solution
        assert err_key == "INSTANCE_IDLE"
        assert cur_price == mock_ec2_pricing["t2.micro"]["us-east-1"]
        assert "idle" in states
        assert len(solution_w_price) > 0

        # Test report generation
        report_result = rules_engine.report(mock_rhel_release, mock_cloud_instance_aws, solution)
        assert report_result is not None

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    @patch('ros.rules.rules_engine.Ec2LinuxPrices')
    def test_complete_workflow_undersized_system(self, mock_pricing, mock_instances,
                                                 mock_rhel_release, mock_cloud_instance_aws,
                                                 mock_ec2_instance_types, mock_ec2_pricing):
        """Test complete workflow for an undersized system."""
        # Setup mocks using comprehensive fixtures
        mock_instances.get.return_value = mock_ec2_instance_types["t2.micro"]
        mock_instances.items.return_value = mock_ec2_instance_types.items()
        mock_instances.keys.return_value = mock_ec2_instance_types.keys()

        pricing_instance = Mock()
        pricing_instance.get.return_value = mock_ec2_pricing["t2.micro"]
        mock_pricing.return_value = pricing_instance

        # Mock performance data for undersized system
        cpu_ut = (0.9, 0.2)      # Very high CPU utilization
        mem_ut = (0.95, 950.0)   # Very high memory utilization
        io_ut = {"xvda": 1000.0}  # High I/O
        psi_ut = (25.0, 5.0, 30.0, 25.0, 2.0)  # High pressure values

        # Test evaluations
        cpu_eval = rules_engine.cpu_evaluation(cpu_ut)
        assert cpu_eval[0] & RosKeys.CPU_UNDERSIZED

        mem_eval = rules_engine.mem_evaluation(mem_ut)
        assert mem_eval[0] & RosKeys.MEMORY_UNDERSIZED

        idle_eval = rules_engine.idle_evaluation(cpu_ut, mem_ut)
        assert idle_eval == RosKeys.OPTIMIZED  # Not idle

        psi_eval = rules_engine.psi_evaluation(psi_ut)
        assert psi_eval & RosKeys.CPU_UNDERSIZED_BY_PRESSURE
        assert psi_eval & RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE
        assert psi_eval & RosKeys.IO_UNDERSIZED_BY_PRESSURE

        # Test candidate generation
        cpu_candidates = rules_engine.cpu_candidates(mock_cloud_instance_aws, cpu_eval, psi_eval)
        mem_candidates = rules_engine.mem_candidates(mock_cloud_instance_aws, mem_eval, psi_eval)
        io_candidates = rules_engine.io_candidates(
            mock_cloud_instance_aws, rules_engine.io_evaluation(io_ut)
        )

        # Test find_solution
        solution = rules_engine.find_solution(
            mock_cloud_instance_aws, cpu_candidates, mem_candidates, io_candidates,
            idle_eval, psi_eval
        )

        err_key, cur_price, states, solution_w_price = solution
        assert err_key == "INSTANCE_UNDERSIZED"
        assert cur_price == mock_ec2_pricing["t2.micro"]["us-east-1"]
        assert "cpu" in states or "memory" in states
        assert len(solution_w_price) > 0

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    @patch('ros.rules.rules_engine.Ec2LinuxPrices')
    def test_complete_workflow_oversized_system(self, mock_pricing, mock_instances,
                                                mock_rhel_release, mock_cloud_instance_aws_larger,
                                                mock_ec2_instance_types, mock_ec2_pricing):
        """Test complete workflow for an oversized system."""
        # Setup mocks using comprehensive fixtures
        mock_instances.get.return_value = mock_ec2_instance_types["m5.xlarge"]
        mock_instances.items.return_value = mock_ec2_instance_types.items()
        mock_instances.keys.return_value = mock_ec2_instance_types.keys()

        pricing_instance = Mock()
        # Higher price for larger instance
        pricing_instance.get.return_value = mock_ec2_pricing["m5.xlarge"]
        mock_pricing.return_value = pricing_instance

        # Mock performance data for oversized system
        cpu_ut = (0.03, 3.88)    # Very low CPU utilization (3%)
        mem_ut = (0.04, 640.0)   # Very low memory utilization (4%)
        io_ut = {"xvda": 10.0}   # Low I/O
        psi_ut = (1.0, 0.0, 1.0, 1.0, 0.0)  # Very low pressure values

        # Test evaluations
        cpu_eval = rules_engine.cpu_evaluation(cpu_ut)
        assert cpu_eval[0] & RosKeys.CPU_OVERSIZED

        mem_eval = rules_engine.mem_evaluation(mem_ut)
        assert mem_eval[0] & RosKeys.MEMORY_OVERSIZED

        idle_eval = rules_engine.idle_evaluation(cpu_ut, mem_ut)
        assert idle_eval == RosKeys.IDLE  # Should be idle

        psi_eval = rules_engine.psi_evaluation(psi_ut)
        assert psi_eval == RosKeys.OPTIMIZED  # No pressure

        # Test candidate generation
        cpu_candidates = rules_engine.cpu_candidates(mock_cloud_instance_aws_larger, cpu_eval, psi_eval)
        mem_candidates = rules_engine.mem_candidates(mock_cloud_instance_aws_larger, mem_eval, psi_eval)
        io_candidates = rules_engine.io_candidates(
            mock_cloud_instance_aws_larger, rules_engine.io_evaluation(io_ut)
        )

        # Test find_solution
        solution = rules_engine.find_solution(
            mock_cloud_instance_aws_larger, cpu_candidates, mem_candidates, io_candidates,
            idle_eval, psi_eval
        )

        err_key, cur_price, states, solution_w_price = solution
        assert err_key in ["INSTANCE_IDLE", "INSTANCE_OVERSIZED"]
        assert cur_price == mock_ec2_pricing["m5.xlarge"]["us-west-2"]
        assert len(solution_w_price) > 0

        # For oversized/idle, candidates should be cheaper
        for candidate, price in solution_w_price:
            assert price <= cur_price

    def test_complete_workflow_optimized_system(self):
        """Test complete workflow for an optimized system."""
        # Create test data for optimized system
        cpu_ut = (0.6, 0.8)      # Good CPU utilization
        mem_ut = (0.6, 600.0)    # Good memory utilization
        # io_ut = {"xvda": 100.0}  # Moderate I/O - unused in this test
        psi_ut = (10.0, 0.0, 10.0, 10.0, 0.0)  # Moderate pressure values

        # Test evaluations - all should be optimized
        cpu_eval = rules_engine.cpu_evaluation(cpu_ut)
        assert cpu_eval[0] == RosKeys.OPTIMIZED

        mem_eval = rules_engine.mem_evaluation(mem_ut)
        assert mem_eval[0] == RosKeys.OPTIMIZED

        idle_eval = rules_engine.idle_evaluation(cpu_ut, mem_ut)
        assert idle_eval == RosKeys.OPTIMIZED  # Not idle

        psi_eval = rules_engine.psi_evaluation(psi_ut)
        assert psi_eval == RosKeys.OPTIMIZED  # No significant pressure

    @patch('ros.rules.rules_engine.insights_run')
    def test_run_rules_integration(self, mock_insights_run):
        """Test the run_rules function with mocked insights framework."""
        # Mock the insights_run function
        mock_insights_run.return_value = {
            'report_metadata': {
                'type': 'metadata',
                'cloud_provider': 'aws',
                'cpu_utilization': '60',
                'mem_utilization': '70',
                'psi_enabled': True
            },
            'report': {
                'type': 'rule',
                'error_key': 'INSTANCE_UNDERSIZED',
                'rhel': '8.4',
                'cloud_provider': 'aws',
                'instance_type': 't2.micro',
                'region': 'us-east-1',
                'price': 0.0116,
                'candidates': [['t2.medium', 0.0464], ['t2.large', 0.0928]],
                'states': {
                    'cpu': ['CPU_UNDERSIZED'],
                    'memory': ['MEMORY_UNDERSIZED']
                }
            }
        }

        # Test run_rules
        extracted_dir = "/tmp/test_extraction"
        result = rules_engine.run_rules(extracted_dir)

        # Verify insights_run was called correctly
        mock_insights_run.assert_called_once()
        args, kwargs = mock_insights_run.call_args

        # Check that the correct rules were passed
        rules_list = args[0]
        assert len(rules_list) == 2  # report_metadata and report
        assert rules_engine.report_metadata in rules_list
        assert rules_engine.report in rules_list

        # Check that the root parameter was set correctly
        assert kwargs['root'] == extracted_dir

        # Check the result
        assert result == mock_insights_run.return_value
        assert 'report_metadata' in result
        assert 'report' in result

    def test_readable_evaluation_comprehensive(self):
        """Test readable_evaluation with various flag combinations."""
        test_cases = [
            # (input_flags, expected_error_key, expected_states_keys)
            (RosKeys.IDLE, "INSTANCE_IDLE", ["idle"]),
            (RosKeys.CPU_UNDERSIZED, "INSTANCE_UNDERSIZED", ["cpu"]),
            (RosKeys.MEMORY_UNDERSIZED | RosKeys.IO_UNDERSIZED,
             "INSTANCE_UNDERSIZED", ["memory", "io"]),
            (RosKeys.CPU_OVERSIZED | RosKeys.MEMORY_OVERSIZED,
             "INSTANCE_OVERSIZED", ["cpu", "memory"]),
            (RosKeys.CPU_UNDERSIZED_BY_PRESSURE,
             "INSTANCE_OPTIMIZED_UNDER_PRESSURE", ["cpu"]),
            (RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE |
             RosKeys.IO_UNDERSIZED_BY_PRESSURE,
             "INSTANCE_OPTIMIZED_UNDER_PRESSURE", ["memory", "io"]),
        ]

        for flags, expected_error, expected_states in test_cases:
            err_key, states = rules_engine.readable_evalution(flags)
            assert err_key == expected_error

            # Check that expected state categories are present
            for state_key in expected_states:
                if state_key == "idle":
                    # Idle excludes other states
                    assert state_key in states
                    break
                else:
                    assert state_key in states

    def test_topmost_candidate_comprehensive(self):
        """Test topmost_candidate_from_rule_hit with various scenarios."""
        # Test with optimized state
        result = topmost_candidate_from_rule_hit([], "OPTIMIZED")
        assert result == [None, None]

        # Test with no PCP data
        result = topmost_candidate_from_rule_hit([], "NO_PCP_DATA")
        assert result == [None, None]

        # Test with actual candidates
        reports = [{
            'details': {
                'candidates': [
                    ['t2.small', 0.023],
                    ['t2.medium', 0.046],
                    ['t2.large', 0.092]
                ]
            }
        }]

        result = topmost_candidate_from_rule_hit(
            reports, "INSTANCE_UNDERSIZED"
        )
        assert result == ['t2.small', 0.023]

        # Test with empty candidates
        reports_empty = [{
            'details': {
                'candidates': []
            }
        }]

        with pytest.raises(IndexError):
            topmost_candidate_from_rule_hit(
                reports_empty, "INSTANCE_UNDERSIZED"
            )


class TestRulesEngineErrorHandling:
    """Test error handling and edge cases in rules engine."""

    def test_cpu_utilization_missing_pmlog_data(self):
        """Test CPU utilization when pmlog data is missing."""
        new_pm = Mock()
        new_pm.get.side_effect = KeyError("hinv")
        new_pm.__getitem__ = Mock(side_effect=KeyError("kernel"))

        lscpu = None

        with pytest.raises(SkipComponent):
            rules_engine.cpu_utilization(new_pm, lscpu)

    def test_mem_utilization_missing_data(self):
        """Test memory utilization when data is missing."""
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=KeyError("mem"))

        with pytest.raises(SkipComponent):
            rules_engine.mem_utilization(new_pm)

    def test_io_utilization_missing_data(self):
        """Test I/O utilization when data is missing."""
        new_pm = Mock()
        new_pm.__getitem__ = Mock(side_effect=KeyError("disk"))

        cm = Mock()

        with pytest.raises(SkipComponent):
            rules_engine.io_utilization(new_pm, cm)

    def test_psi_utilization_disabled(self):
        """Test PSI utilization when PSI is disabled."""
        psi = False
        new_pm = Mock()

        with pytest.raises(SkipComponent):
            rules_engine.psi_utilization(psi, new_pm)

    def test_cloud_metadata_unsupported_provider(self):
        """Test cloud metadata with unsupported provider."""
        cp = Mock()
        cp.cloud_provider = "gcp"  # Only AWS is supported by ROS
        cp.AWS = "aws"

        aws = {'instanceType': 't2.micro'}
        azure = None  # ROS only supports AWS

        with pytest.raises(SkipComponent):
            rules_engine.cloud_metadata(cp, aws, azure)

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    def test_find_solution_no_candidates(self, mock_instances):
        """Test find_solution when no candidates are found."""
        mock_instances.get.return_value = {"ram": 1}

        cm = Mock()
        cm.type = "t2.micro"
        cm.region = "us-east-1"

        # Mock evaluations with no overlapping candidates
        cpu = (RosKeys.CPU_UNDERSIZED, set())  # Empty candidate set
        mem = (RosKeys.MEMORY_UNDERSIZED, {"t2.medium"})
        io = (RosKeys.OPTIMIZED, {"t2.large"})
        idle = RosKeys.OPTIMIZED
        psi = RosKeys.OPTIMIZED

        with pytest.raises(SkipComponent):
            rules_engine.find_solution(cm, cpu, mem, io, idle, psi)


class TestRulesEnginePerformance:
    """Test performance-related aspects of rules engine."""

    @patch('ros.rules.rules_engine.EC2_INSTANCE_TYPES')
    def test_large_instance_type_dataset(self, mock_instances):
        """Test rules engine with a large dataset of instance types."""
        # Create a large mock dataset
        large_dataset = {}
        for i in range(1000):
            instance_name = f"test.instance{i}"
            large_dataset[instance_name] = {
                "ram": i + 1,
                "extra": {
                    "vcpu": str((i % 32) + 1),
                    "physicalProcessor": "Intel Xeon Family"
                }
            }

        mock_instances.items.return_value = large_dataset.items()
        mock_instances.get.return_value = large_dataset["test.instance1"]
        mock_instances.keys.return_value = large_dataset.keys()

        # Mock cloud metadata
        cm = Mock()
        cm.type = "test.instance1"
        cm.region = "us-east-1"

        # Test that the function can handle large datasets efficiently
        cpu_ut = (RosKeys.CPU_UNDERSIZED, 0.9)
        psi_ut = RosKeys.OPTIMIZED

        # This should complete without performance issues
        result_ut, candidates = rules_engine.cpu_candidates(cm, cpu_ut, psi_ut)

        assert result_ut & RosKeys.CPU_UNDERSIZED
        assert isinstance(candidates, set)

    def test_thresholds_boundary_conditions(self):
        """Test threshold boundary conditions."""
        # Test CPU evaluation at exact thresholds
        cpu_ut_at_upper_threshold = (
            RosThresholds.CPU_UTILIZATION_WARNING_UPPER_THRESHOLD, 0.4
        )
        cpu_eval = rules_engine.cpu_evaluation(cpu_ut_at_upper_threshold)
        # At exactly 0.8, should not be undersized (needs to be > 0.8)
        assert not (cpu_eval[0] & RosKeys.CPU_UNDERSIZED)

        cpu_ut_above_upper_threshold = (
            RosThresholds.CPU_UTILIZATION_WARNING_UPPER_THRESHOLD + 0.01, 0.39
        )
        cpu_eval = rules_engine.cpu_evaluation(cpu_ut_above_upper_threshold)
        # Above 0.8, should be undersized
        assert cpu_eval[0] & RosKeys.CPU_UNDERSIZED

        # Test memory evaluation at exact thresholds
        mem_ut_at_lower_threshold = (
            RosThresholds.MEMORY_UTILIZATION_WARNING_LOWER_THRESHOLD, 200.0
        )
        mem_eval = rules_engine.mem_evaluation(mem_ut_at_lower_threshold)
        # At exactly 0.2, should not be oversized (needs to be < 0.2)
        assert not (mem_eval[0] & RosKeys.MEMORY_OVERSIZED)

        mem_ut_below_lower_threshold = (
            RosThresholds.MEMORY_UTILIZATION_WARNING_LOWER_THRESHOLD - 0.01,
            190.0
        )
        mem_eval = rules_engine.mem_evaluation(mem_ut_below_lower_threshold)
        # Below 0.2, should be oversized
        assert mem_eval[0] & RosKeys.MEMORY_OVERSIZED


if __name__ == '__main__':
    pytest.main([__file__])
