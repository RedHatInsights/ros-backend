import unittest
import logging
from unittest.mock import patch
from ros.processor.suggestions_engine import (
    SuggestionsEngine,
    is_pcp_collected,
    download_and_extract
)


class TestSuggestionsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()

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


class TestDownloadAndExtract(unittest.TestCase):

    @patch("ros.processor.suggestions_engine.extract")
    @patch("ros.processor.suggestions_engine.NamedTemporaryFile")
    @patch("ros.processor.suggestions_engine.requests.get")
    def test_download_and_extract_successful(self, mock_get, mock_tempfile, mock_extract):
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"dummy data"

        mock_tempfile.return_value.__enter__.return_value.name = "tempfile.tar.gz"

        mock_extract.return_value.__enter__.return_value.tmp_dir = "extracted_dir"

        extract_dir = download_and_extract(
            service="TestService",
            event="TestEvent",
            archive_URL="http://example.com/archive.tar.gz",
            host={"id": "test_host"},
            org_id="123"
        )

        mock_get.assert_called_once_with("http://example.com/archive.tar.gz", timeout=10)
        mock_tempfile.return_value.__enter__.assert_called_once()
        mock_extract.assert_called_once()
        self.assertEqual(extract_dir, "extracted_dir")

    @patch('ros.processor.suggestions_engine.extract')
    @patch('ros.processor.suggestions_engine.requests.get')
    def test_download_and_extract_failure(self, mock_get, mock_extract):
        mock_get.return_value.status_code = 404
        mock_get.return_value.reason = "Not Found"

        mock_extract.return_value.__enter__.return_value.tmp_dir = "extracted_dir"

        extract_dir = download_and_extract(
            service="TestService",
            event="TestEvent",
            archive_URL="http://example.com/archive.tar.gz",
            host={"id": "test_host"},
            org_id="123"
        )

        mock_get.assert_called_once_with("http://example.com/archive.tar.gz", timeout=10)
        self.assertIsNone(extract_dir)


if __name__ == '__main__':
    unittest.main()
