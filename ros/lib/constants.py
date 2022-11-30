
from enum import Enum


class SubStates(Enum):
    """
    Static substate values for cpu, io, memory
    Source: insights-rules/insights-plugins/-/blob/master/telemetry/rules/plugins/ros/__init__.py#L48
    """
    CPU_UNDERSIZED = 'CPU_UNDERSIZED'
    MEMORY_UNDERSIZED = 'MEMORY_UNDERSIZED'
    IO_UNDERSIZED = 'IO_UNDERSIZED'
    CPU_UNDER_PRESSURE = 'CPU_UNDERSIZED_BY_PRESSURE'
    MEMORY_UNDER_PRESSURE = 'MEMORY_UNDERSIZED_BY_PRESSURE'
    IO_UNDER_PRESSURE = 'IO_UNDERSIZED_BY_PRESSURE'
    CPU_OVERSIZED = 'CPU_OVERSIZED'
    MEMORY_OVERSIZED = 'MEMORY_OVERSIZED'
    IO_OVERSIZED = 'IO_OVERSIZED'
    CPU_IDLING = 'CPU_IDLING'


BUNDLE = "rhel"
APPLICATION = "resource-optimization"
EVENT_TYPE = "new-suggestion"
