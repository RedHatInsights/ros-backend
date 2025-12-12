import unittest
from unittest.mock import patch

from ros.lib.cache_utils import (
    set_deleted_system_cache,
    is_system_deleted,
    clear_deleted_system_cache
)


class TestSetDeletedSystemCache(unittest.TestCase):

    @patch('ros.lib.cache_utils.cache')
    def test_set_with_timestamp(self, mock_cache):
        org_id = "000001"
        host_id = "abc-123"
        timestamp = "2022-05-11T13:58:54.509083+00:00"

        set_deleted_system_cache(org_id, host_id, timestamp)

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args

        cache_key = call_args[0][0]
        self.assertEqual(cache_key, f"{org_id}_del_{host_id}")

        cached_value = call_args[0][1]
        self.assertEqual(cached_value, timestamp)

    @patch('ros.lib.cache_utils.cache')
    def test_set_without_timestamp(self, mock_cache):
        set_deleted_system_cache("000001", "abc-123")
        mock_cache.set.assert_called_once()


class TestIsSystemDeleted(unittest.TestCase):

    @patch('ros.lib.cache_utils.cache')
    def test_no_cache(self, mock_cache):
        mock_cache.get.return_value = None

        result = is_system_deleted("000001", "abc-123", "2022-05-11T13:58:54.509083+00:00")

        self.assertFalse(result)

    @patch('ros.lib.cache_utils.cache')
    def test_no_event_timestamp(self, mock_cache):
        mock_cache.get.return_value = '2022-05-11T13:58:54.509083+00:00'

        result = is_system_deleted("000001", "abc-123")

        self.assertTrue(result)

    @patch('ros.lib.cache_utils.cache')
    def test_event_older_than_deletion(self, mock_cache):
        deletion_time = "2022-05-11T13:58:54.509083+00:00"
        event_time = "2022-05-11T13:58:50.509083+00:00"

        mock_cache.get.return_value = deletion_time

        result = is_system_deleted("000001", "abc-123", event_time)

        self.assertTrue(result)

    @patch('ros.lib.cache_utils.cache')
    def test_event_newer_than_deletion(self, mock_cache):
        deletion_time = "2022-05-11T13:58:50.509083+00:00"
        event_time = "2022-05-11T13:58:54.509083+00:00"

        mock_cache.get.return_value = deletion_time

        result = is_system_deleted("000001", "abc-123", event_time)

        self.assertFalse(result)
        mock_cache.delete.assert_called_once()

    @patch('ros.lib.cache_utils.cache')
    def test_equal_timestamps(self, mock_cache):
        timestamp = "2022-05-11T13:58:54.509083+00:00"

        mock_cache.get.return_value = timestamp

        result = is_system_deleted("000001", "abc-123", timestamp)

        self.assertTrue(result)

    @patch('ros.lib.cache_utils.cache')
    def test_error_handling(self, mock_cache):
        mock_cache.get.side_effect = Exception("Cache error")

        result = is_system_deleted("000001", "abc-123", "2022-05-11T13:58:54.509083+00:00")

        self.assertFalse(result)


class TestClearDeletedSystemCache(unittest.TestCase):
    @patch('ros.lib.cache_utils.cache')
    def test_clear_cache(self, mock_cache):
        """Test clearing deletion cache."""
        clear_deleted_system_cache("000001", "abc-123")

        expected_key = "000001_del_abc-123"
        mock_cache.delete.assert_called_once_with(expected_key)

    @patch('ros.lib.cache_utils.cache')
    def test_clear_cache_error(self, mock_cache):
        mock_cache.delete.side_effect = Exception("Cache error")

        clear_deleted_system_cache("000001", "abc-123")


if __name__ == '__main__':
    unittest.main()
