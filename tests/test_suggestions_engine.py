import unittest
import logging
from unittest.mock import patch
import json

from ros.processor.suggestions_engine import SuggestionsEngine
from ros.processor.event_producer import no_pcp_raw_payload


class TestSuggestionsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()

    def test_handle_create_update_missing_data(self):
        payload_create = {'type': 'create', 'platform_metadata':
                          {'is_ros_v2': False, 'is_pcp_raw_data_collected': False}}
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


class TestDownloadAndExtract(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()

    @patch("ros.processor.suggestions_engine.extract")
    @patch("ros.processor.suggestions_engine.NamedTemporaryFile")
    @patch("ros.processor.suggestions_engine.requests.get")
    def test_download_and_extract_successful(self, mock_get, mock_tempfile, mock_extract):
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"dummy data"

        mock_tempfile.return_value.__enter__.return_value.name = "tempfile.tar.gz"

        mock_extract.return_value.__enter__.return_value.tmp_dir = "extracted_dir"

        with self.engine.download_and_extract(
                archive_URL="http://example.com/archive.tar.gz",
                host={"id": "test_host"},
                org_id="123"
        ) as extract_dir:
            self.assertEqual(extract_dir.tmp_dir, "extracted_dir")

        mock_get.assert_called_once_with("http://example.com/archive.tar.gz", timeout=10)
        mock_tempfile.return_value.__enter__.assert_called_once()
        mock_extract.assert_called_once()

    @patch('ros.processor.suggestions_engine.extract')
    @patch('ros.processor.suggestions_engine.requests.get')
    def test_download_and_extract_failure(self, mock_get, mock_extract):
        mock_get.return_value.status_code = 404
        mock_get.return_value.reason = "Not Found"

        mock_extract.return_value.__enter__.return_value.tmp_dir = "extracted_dir"

        with self.engine.download_and_extract(
                archive_URL="http://example.com/archive.tar.gz",
                host={"id": "test_host"},
                org_id="123"
        ) as extract_dir:
            self.assertIsNone(extract_dir)

        mock_get.assert_called_once_with("http://example.com/archive.tar.gz", timeout=10)


class TestFindRootDirectory(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()

    @patch('ros.processor.suggestions_engine.os.walk')
    def test_file_found_in_root_directory(self, mock_walk):
        mock_walk.return_value = [
            ("/root", ["subdir1", "subdir2"], ["other_file.txt"]),
            ("/root/subdir1", [], ["insights_archive.txt"]),
            ("/root/subdir2", [], ["file2.txt"]),
        ]

        result = self.engine.find_root_directory("/root", "insights_archive.txt")
        self.assertEqual(result, "/root/subdir1")

    @patch('ros.processor.suggestions_engine.os.walk')
    def test_file_not_found(self, mock_walk):
        mock_walk.return_value = [
            ("/root", ["subdir1", "subdir2"], ["other_file.txt"]),
            ("/root/subdir1", [], ["file1.txt"]),
            ("/root/subdir2", [], ["file2.txt"]),
        ]

        result = self.engine.find_root_directory("/root", "insights_archive.txt")
        self.assertIsNone(result)


class TestGetIndexFilePath(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()

    @patch("ros.processor.suggestions_engine.os.listdir")
    @patch("ros.processor.suggestions_engine.os.path.join")
    @patch("ros.processor.suggestions_engine.SuggestionsEngine.find_root_directory")
    def test_get_index_file_path(self, mock_find_root_directory, mock_join, mock_listdir):

        mock_listdir.return_value = ["YYYYMMDD.index"]
        mock_join.return_value = "/var/tmp/extracted/data/var/log/pcp/pmlogger/YYYYMMDD.index"

        index_file_path = self.engine.get_index_file_path(
            host={"id": "test_host"},
            extracted_dir_root="/tmp/extracted"
        )

        mock_listdir.assert_called_once_with("/var/tmp/extracted/data/var/log/pcp/pmlogger/YYYYMMDD.index")
        self.assertEqual(index_file_path, "/var/tmp/extracted/data/var/log/pcp/pmlogger/YYYYMMDD.index")


class TestCreateOutputDir(unittest.TestCase):
    def setUp(self):
        self.engine = SuggestionsEngine()

    @patch("ros.processor.suggestions_engine.os.makedirs")
    @patch("ros.processor.suggestions_engine.os.path.exists")
    def test_create_output_dir(self, mock_path_exists, mock_makedirs):
        request_id = "12345"
        host = {"id": "test_host"}
        mock_path_exists.return_value = False
        mock_makedirs.return_value = None

        output_dir = self.engine.create_output_dir(request_id, host)

        mock_makedirs.assert_called_once_with(output_dir)
        self.assertEqual(output_dir, "/var/tmp/pmlogextract-output-12345/")


class TestNoPcpRawPayload(unittest.TestCase):
    def test_valid_payload(self):
        with open("sample-files/no_pcp_raw_message.json", "r") as f:
            input_payload = json.load(f)

        expected_output = {
            "type": "created",
            "org_id": "000001",
            "platform_metadata": {
                "request_id": "a1b2c3",
                "is_ros_v2": True,
                "is_pcp_raw_data_collected": False
            },
            "id": "123123",
            "display_name": "test",
            "fqdn": "test.org",
            "stale_timestamp": "2025-04-25T13:58:54.509083+00:00",
            "groups": [],
            "operating_system": {"name": "Fedora", "version": "40"},
            "cloud_provider": "aws"
        }

        self.assertEqual(no_pcp_raw_payload(input_payload), expected_output)

    def test_missing_host(self):
        with self.assertRaises(AttributeError):
            no_pcp_raw_payload({
                "type": "created",
                "platform_metadata": {"request_id": "a1b2c3"},
                "host": None
            })


if __name__ == '__main__':
    unittest.main()
