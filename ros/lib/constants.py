
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


class CloudProvider(Enum):
    """Supported cloud providers"""
    AWS = 'aws'


class OperatingSystem(Enum):
    """Supported Operating Systems"""
    RHEL = 'RHEL'


class SystemStatesWithKeys(Enum):
    INSTANCE_OVERSIZED = "Oversized"
    INSTANCE_UNDERSIZED = "Undersized"
    INSTANCE_IDLE = "Idling"
    INSTANCE_OPTIMIZED_UNDER_PRESSURE = "Under pressure"
    STORAGE_RIGHTSIZING = "Storage rightsizing"
    OPTIMIZED = "Optimized"
    NO_PCP_DATA = "Waiting for data"


class RosSummary(Enum):
    OPTIMIZED = "System is OPTIMIZED"
    MEMORY_OVERSIZED = "Memory utilization is very low"
    MEMORY_UNDERSIZED = "Memory utilization is too high"
    MEMORY_UNDERSIZED_BY_PRESSURE = "System is suffering from memory pressure"
    CPU_OVERSIZED = "CPU utilization is very low"
    CPU_UNDERSIZED = "CPU utilization is too high"
    CPU_UNDERSIZED_BY_PRESSURE = "System is suffering from CPU pressure"
    IO_OVERSIZED = "I/O utilization is very low"
    IO_UNDERSIZED = "I/O utilization is too high"
    IO_UNDERSIZED_BY_PRESSURE = "System is suffering from IO pressure"
    IDLE = "System is IDLE"


class SystemsTableColumn(Enum):
    """Common column names for System table"""
    SYSTEM_COLUMNS = [
        "inventory_id",
        "display_name",
        "instance_type",
        "cloud_provider",
        "state",
        "fqdn",
        "operating_system",
        "groups"
    ]


class Suggestions(Enum):
    NEWLINE_SEPARATOR = "\n"
    RULES_COLUMNS = ["rule_id", "description", "reason", "resolution", "condition"]
    INSTANCE_PRICE_UNIT = "USD/hour"


class Notification(Enum):
    BUNDLE = "rhel"
    APPLICATION = "resource-optimization"
    EVENT_TYPE = "new-suggestion"
