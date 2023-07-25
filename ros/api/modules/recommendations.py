"""
Custom readonly class for Recommendation
"""
from ros.lib.config import INSTANCE_PRICE_UNIT


NEWLINE_SEPARATOR = '\n'
RULES_COLUMNS = ['rule_id', 'description', 'reason', 'resolution', 'condition']

ROSSUMMARY = dict(
    OPTIMIZED='System is OPTIMIZED',
    MEMORY_OVERSIZED='Memory utilization is very low',
    MEMORY_UNDERSIZED='Memory utilization is too high',
    MEMORY_UNDERSIZED_BY_PRESSURE='System is suffering from memory pressure',
    CPU_OVERSIZED='CPU utilization is very low',
    CPU_UNDERSIZED='CPU utilization is too high',
    CPU_UNDERSIZED_BY_PRESSURE='System is suffering from CPU pressure',
    IO_OVERSIZED='I/O utilization is very low',
    IO_UNDERSIZED='I/O utilization is too high',
    IO_UNDERSIZED_BY_PRESSURE='System is suffering from IO pressure',
    IDLE='System is IDLE',
)


class Recommendation:
    """Custom readonly recommendation class to generate list."""
    def __init__(self, rule_data, rule_hit, system, psi_enabled):
        rule_hit_key = rule_hit.get("key")

        rule_dict = rule_data.__dict__
        self.rule_hit_details = rule_hit.get('details')
        self.detected_issues = self.detected_issues_by_states(rule_hit_key)
        self.suggested_instances = self.candidates_str()
        self.current_instance = self.instance_info_str()
        self.psi_enabled = psi_enabled
        for rkey in RULES_COLUMNS:
            setattr(self, rkey, eval("f'{}'".format(rule_dict[rkey])))

    def instance_info_str(self):
        """Return current instance type with price info."""
        return f'{self.rule_hit_details.get("instance_type")} ' + \
            f'({self.rule_hit_details.get("price")} {INSTANCE_PRICE_UNIT})'

    def candidates_str(self):
        """Get string of instance types separated by newline."""
        candidates = self.rule_hit_details.get('candidates')
        formatted_candidates = []

        for candidate in candidates[0:3]:
            formatted_candidates.append(
                f'{candidate[0]} ({candidate[1]} {INSTANCE_PRICE_UNIT})')

        return NEWLINE_SEPARATOR.join(formatted_candidates)

    def detected_issues_by_states(self, rule_hit_key):
        """Get string of issues descriptions per state."""
        if rule_hit_key == 'INSTANCE_IDLE':
            return None

        states = self.rule_hit_details.get('states')
        summaries = [
            ROSSUMMARY[state] for substates in states.values()
            for state in substates
            if ROSSUMMARY.get(state) is not None
        ]
        return NEWLINE_SEPARATOR.join(summaries)
