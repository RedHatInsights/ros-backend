# Rules Engine Unit Tests

This directory contains comprehensive unit and integration tests for the ROS Rules Engine. The test suite covers all major components and provides thorough validation of the rules engine functionality.

## 📁 Test Files Structure

```
tests/
├── test_rules_engine.py                    # Core unit tests
├── test_rules_engine_integration.py        # Integration tests
├── fixtures/
│   └── rules_engine_fixtures.py           # Test fixtures and mock data
└── README_RULES_ENGINE_TESTS.md           # This file
```

## 🧪 Test Coverage

### Unit Tests (`test_rules_engine.py`)

#### **Condition Functions**
- `TestCloudMetadata` - Tests cloud provider metadata extraction
- `TestNopmlogSummary` - Tests PCP data availability detection
- `TestCpuUtilization` - Tests CPU utilization calculation
- `TestMemUtilization` - Tests memory utilization calculation
- `TestIoUtilization` - Tests I/O utilization calculation
- `TestPsiEnabled` - Tests PSI (Pressure Stall Information) detection
- `TestPsiUtilization` - Tests PSI metrics extraction

#### **Evaluation Functions**
- `TestEvaluationFunctions` - Tests all evaluation logic:
  - Idle system detection
  - CPU undersized/oversized evaluation
  - Memory undersized/oversized evaluation
  - PSI pressure evaluation

#### **Candidate Generation**
- `TestCandidateFunctions` - Tests instance type recommendation logic:
  - CPU-based candidate filtering
  - Memory-based candidate filtering
  - I/O candidate generation
  - Cross-resource candidate intersection

#### **Rule Functions**
- `TestFindSolution` - Tests complete solution finding algorithm
- `TestRuleFunctions` - Tests report generation functions
- `TestUtilityFunctions` - Tests helper functions

#### **Configuration & Constants**
- `TestRosThresholds` - Validates threshold configurations
- `TestRosKeys` - Validates flag system integrity
- `TestErrorKeys` - Validates error key constants

### Integration Tests (`test_rules_engine_integration.py`)

#### **End-to-End Workflows**
- `TestRulesEngineIntegration` - Complete workflow tests:
  - Idle system analysis and recommendations
  - Undersized system analysis and recommendations  
  - Oversized system analysis and recommendations
  - Optimized system validation
  - Full rule execution pipeline

#### **Error Handling**
- `TestRulesEngineErrorHandling` - Error condition tests:
  - Missing data scenarios
  - Invalid input handling
  - Unsupported configurations

#### **Performance & Edge Cases**
- `TestRulesEnginePerformance` - Performance and boundary tests:
  - Large dataset handling
  - Threshold boundary conditions
  - Memory and CPU efficiency

### Test Fixtures (`fixtures/rules_engine_fixtures.py`)

#### **Mock Data Providers**
- Cloud instance metadata for AWS (ROS only supports AWS)
- PCP performance data for different system states
- Mock parser objects (LsCPU, CmdLine, etc.)
- EC2 instance types and pricing data
- Sample rule hit data for all system states

#### **Helper Classes**
- `MockSystemStateData` - Generates consistent test data
- Various pytest fixtures for different scenarios


## 🎯 Test Scenarios Covered

### System State Analysis
- **Idle Systems**: Very low CPU and memory utilization
- **Undersized Systems**: High utilization requiring more resources
- **Oversized Systems**: Very low utilization with excess resources
- **Under Pressure Systems**: Resource pressure detected via PSI
- **Optimized Systems**: Balanced resource utilization
- **No PCP Data**: Systems without performance monitoring data

### Resource Types
- **CPU**: Utilization percentage and pressure metrics
- **Memory**: Usage patterns and pressure detection
- **I/O**: Disk performance and pressure analysis
- **Combined**: Multi-resource evaluation and optimization

### Cloud Platforms
- **AWS EC2**: Instance types, pricing, and recommendations

- **Multi-cloud**: Platform-agnostic evaluation logic

### Edge Cases
- Missing or incomplete performance data
- Threshold boundary conditions
- Large instance type datasets
- Invalid or unsupported configurations

## 🔧 Test Data and Mocking

### Mock Strategy
The tests use comprehensive mocking to isolate components:

- **Red Hat Insights Framework**: Mocked to test rule logic independently
- **Performance Data**: Controlled PCP metrics for predictable testing
- **Cloud APIs**: Mocked instance type and pricing data
- **External Dependencies**: All external calls are mocked

### Test Data Patterns
- **Realistic Values**: Test data reflects real-world performance metrics
- **Boundary Testing**: Values at and around thresholds
- **Error Conditions**: Invalid, missing, or malformed data
- **Performance Scenarios**: Various system load patterns
