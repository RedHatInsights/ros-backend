"""
Custom readonly class for Recommendation
"""
from ros.lib.constants import (
        RosSummary, Suggestions
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
        for rkey in Suggestions.RULES_COLUMNS.value:
            setattr(self, rkey, eval("f'{}'".format(rule_dict[rkey])))

    def instance_info_str(self):
        """Return current instance type with price info."""
        return f'{self.rule_hit_details.get("instance_type")} ' + \
            f'({self.rule_hit_details.get("price")} {Suggestions.INSTANCE_PRICE_UNIT.value})'

    def candidates_str(self):
        """Get string of instance types separated by newline."""
        candidates = self.rule_hit_details.get('candidates')
        formatted_candidates = []

        for candidate in candidates[0:3]:
            formatted_candidates.append(
                f'{candidate[0]} ({candidate[1]} {Suggestions.INSTANCE_PRICE_UNIT.value})')

        return Suggestions.NEWLINE_SEPARATOR.value.join(formatted_candidates)

    def detected_issues_by_states(self, rule_hit_key):
        """Get string of issues descriptions per state."""
        if rule_hit_key == 'INSTANCE_IDLE':
            return None

        states = self.rule_hit_details.get('states')
        summaries = [
            RosSummary[state].value for substates in states.values()
            for state in substates
            if RosSummary[state].value is not None
        ]
        return Suggestions.NEWLINE_SEPARATOR.value.join(summaries)
