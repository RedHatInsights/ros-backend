import unittest
import logging
from unittest.mock import Mock
from ros.processor.suggestions_engine import SuggestionsEngine, is_pcp_collected


class TestSuggestionsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()
        self.mock_consumer = Mock()

    def test_handle_create_update_missing_data(self):
        payload_create = {'type': 'create'}
        payload_update = {'type': 'updated', 'platform_metadata': {}}

        with self.assertLogs(logging.getLogger(), level='INFO') as log:
            self.engine.handle_create_update(payload_create)
            expected_log_message = (
                "INFO:ros.processor.suggestions_engine:SUGGESTIONS_ENGINE - Create event - "
                "Missing host or/and platform_metadata field(s)."
            )
            self.assertIn(expected_log_message, log.output)

            self.engine.handle_create_update(payload_update)
            expected_log_message = (
                "INFO:ros.processor.suggestions_engine:SUGGESTIONS_ENGINE - Update event - "
                "Missing host or/and platform_metadata field(s)."
            )
            self.assertIn(expected_log_message, log.output)

    def test_is_pcp_collected(self):
        valid_metadata = {'is_ros_v2': True, 'is_pcp_raw_data_collected': True}
        self.assertTrue(is_pcp_collected(valid_metadata))

        invalid_metadata = {'is_ros_v2': True, 'is_pcp_raw_data_collected': False}
        self.assertFalse(is_pcp_collected(invalid_metadata))

        invalid_metadata = {'is_ros_v2': False, 'is_pcp_raw_data_collected': True}
        self.assertFalse(is_pcp_collected(invalid_metadata))

        invalid_metadata = {'is_ros_v2': False, 'is_pcp_raw_data_collected': False}
        self.assertFalse(is_pcp_collected(invalid_metadata))


if __name__ == '__main__':
    unittest.main()
