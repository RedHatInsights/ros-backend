import unittest
import logging
from unittest.mock import patch

from ros.processor.suggestions_engine import (
    SuggestionsEngine,
    is_pcp_collected,
    download_and_extract,
    get_index_file_path,
    create_output_dir,
    find_root_directory,
    PCP_METRICS
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

        with download_and_extract(
                service="TestService",
                event="TestEvent",
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

        with download_and_extract(
                service="TestService",
                event="TestEvent",
                archive_URL="http://example.com/archive.tar.gz",
                host={"id": "test_host"},
                org_id="123"
        ) as extract_dir:
            self.assertIsNone(extract_dir)

        mock_get.assert_called_once_with("http://example.com/archive.tar.gz", timeout=10)


class TestFindRootDirectory(unittest.TestCase):

    @patch('ros.processor.suggestions_engine.os.walk')
    def test_file_found_in_root_directory(self, mock_walk):
        mock_walk.return_value = [
            ("/root", ["subdir1", "subdir2"], ["other_file.txt"]),
            ("/root/subdir1", [], ["insights_archive.txt"]),
            ("/root/subdir2", [], ["file2.txt"]),
        ]

        result = find_root_directory("/root", "insights_archive.txt")
        self.assertEqual(result, "/root/subdir1")

    @patch('ros.processor.suggestions_engine.os.walk')
    def test_file_not_found(self, mock_walk):
        mock_walk.return_value = [
            ("/root", ["subdir1", "subdir2"], ["other_file.txt"]),
            ("/root/subdir1", [], ["file1.txt"]),
            ("/root/subdir2", [], ["file2.txt"]),
        ]

        result = find_root_directory("/root", "insights_archive.txt")
        self.assertIsNone(result)


class TestGetIndexFilePath(unittest.TestCase):

    @patch("ros.processor.suggestions_engine.os.listdir")
    @patch("ros.processor.suggestions_engine.os.path.join")
    @patch("ros.processor.suggestions_engine.find_root_directory")
    def test_get_index_file_path(self, mock_find_root_directory, mock_join, mock_listdir):
        mock_find_root_directory.return_value = "/tmp/extracted/"

        mock_listdir.return_value = ["YYYYMMDD.index"]
        mock_join.return_value = "/tmp/extracted/data/var/log/pcp/pmlogger/YYYYMMDD.index"

        index_file_path = get_index_file_path(
            service="TestService",
            event="TestEvent",
            host={"id": "test_host"},
            extracted_dir="/tmp/extracted"
        )

        mock_listdir.assert_called_once_with("/tmp/extracted/data/var/log/pcp/pmlogger/YYYYMMDD.index")
        self.assertEqual(index_file_path, "/tmp/extracted/data/var/log/pcp/pmlogger/YYYYMMDD.index")


class TestCreateOutputDir(unittest.TestCase):

    @patch("ros.processor.suggestions_engine.os.makedirs")
    @patch("ros.processor.suggestions_engine.os.path.exists")
    def test_create_output_dir(self, mock_path_exists, mock_makedirs):
        request_id = "12345"
        mock_path_exists.return_value = False
        mock_makedirs.return_value = None

        output_dir = create_output_dir(request_id)

        mock_makedirs.assert_called_once_with(output_dir)
        self.assertEqual(output_dir, "/tmp/pmlogextract-output-12345/")


class TestPCPMetrics(unittest.TestCase):
    def test_pcp_metrics_check(self):
        expected_metrics = [
            "disk.dev.total",
            "hinv.ncpu",
            "kernel.all.cpu.idle",
            "kernel.all.pressure.cpu.some.avg",
            "kernel.all.pressure.io.full.avg",
            "kernel.all.pressure.io.some.avg",
            "kernel.all.pressure.memory.full.avg",
            "kernel.all.pressure.memory.some.avg",
            "mem.physmem",
            "mem.util.available",
        ]
        self.assertEqual(PCP_METRICS, expected_metrics)

    def test_pcp_metrics_in_command(self):
        output_dir = "/tmp/pmlogextract-output-12345"
        command = ["pmlogsummary", "-f", output_dir, *PCP_METRICS]

        expected_command = [
            "pmlogsummary",
            "-f",
            output_dir,
            "disk.dev.total",
            "hinv.ncpu",
            "kernel.all.cpu.idle",
            "kernel.all.pressure.cpu.some.avg",
            "kernel.all.pressure.io.full.avg",
            "kernel.all.pressure.io.some.avg",
            "kernel.all.pressure.memory.full.avg",
            "kernel.all.pressure.memory.some.avg",
            "mem.physmem",
            "mem.util.available",
        ]

        self.assertEqual(command, expected_command)


if __name__ == '__main__':
    unittest.main()
