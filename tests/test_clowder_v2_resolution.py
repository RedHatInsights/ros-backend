"""Tests for Clowder V2 RBAC endpoint resolution and bearer authentication."""

from unittest.mock import MagicMock, patch
import pytest


class TestV2EndpointResolution:
    """Test config.py V2 RBAC endpoint resolution."""

    @patch.dict("os.environ", {"CLOWDER_ENABLED": "True"})
    @patch("app_common_python.LoadedConfig")
    @patch("app_common_python.KafkaTopics", {})
    @patch("app_common_python.KafkaServers", [])
    def test_v2_endpoint_with_uri_and_ca(self, mock_loaded_config):
        """V2 endpoint with URI and CA → uses V2 URI and per-dep CA path."""
        v2_endpoint = MagicMock()
        v2_endpoint.uri = "https://rbac.example.com:8443"
        v2_endpoint.ca_certificate = "/tmp/ca-rbac.crt"
        v2_endpoint.authenticated = True

        with patch(
            "app_common_python.get_v2_dependency_endpoint",
            return_value=v2_endpoint,
        ) as mock_get_v2:
            # Reload to pick up the mocked Clowder env
            import importlib
            from ros.lib import config

            importlib.reload(config)

            mock_get_v2.assert_called_once_with("rbac", "service")
            assert config.RBAC_SVC_URL == "https://rbac.example.com:8443"
            assert config.RBAC_CA_PATH == "/tmp/ca-rbac.crt"
            assert config.RBAC_AUTHENTICATED is True

    @patch.dict("os.environ", {"CLOWDER_ENABLED": "True"})
    @patch("app_common_python.LoadedConfig")
    @patch("app_common_python.KafkaTopics", {})
    @patch("app_common_python.KafkaServers", [])
    def test_v2_endpoint_with_uri_no_ca(self, mock_loaded_config):
        """V2 endpoint with URI, no CA → uses V2 URI with system trust."""
        v2_endpoint = MagicMock()
        v2_endpoint.uri = "https://rbac.example.com:8443"
        v2_endpoint.ca_certificate = None
        v2_endpoint.authenticated = False

        with patch(
            "app_common_python.get_v2_dependency_endpoint",
            return_value=v2_endpoint,
        ):
            import importlib
            from ros.lib import config

            importlib.reload(config)

            assert config.RBAC_SVC_URL == "https://rbac.example.com:8443"
            assert config.RBAC_CA_PATH is None
            assert config.RBAC_AUTHENTICATED is False

    @patch.dict("os.environ", {"CLOWDER_ENABLED": "True"})
    @patch("app_common_python.LoadedConfig")
    @patch("app_common_python.KafkaTopics", {})
    @patch("app_common_python.KafkaServers", [])
    def test_v2_endpoint_absent(self, mock_loaded_config):
        """V2 lookup returns None → warning logged, RBAC_SVC_URL empty."""
        mock_loaded_config.tlsCAPath = "/global/ca.crt"

        with patch(
            "app_common_python.get_v2_dependency_endpoint",
            return_value=None,
        ):
            import importlib
            from ros.lib import config

            importlib.reload(config)

            assert config.RBAC_SVC_URL == ""
            assert config.RBAC_CA_PATH == "/global/ca.crt"
            assert config.RBAC_AUTHENTICATED is False

    @patch.dict("os.environ", {"CLOWDER_ENABLED": "False"})
    def test_non_clowder_defaults(self):
        """Non-Clowder path → existing env-var defaults, no bearer."""
        import importlib
        from ros.lib import config

        importlib.reload(config)

        assert "localhost" in config.RBAC_SVC_URL or "8114" in config.RBAC_SVC_URL
        assert config.RBAC_CA_PATH is None  # TLS_CA_PATH default is None
        assert config.RBAC_AUTHENTICATED is False


class TestFetchUrlBearerAuth:
    """Test rbac_interface.py fetch_url bearer authentication behavior."""

    def test_authenticated_true_adds_bearer(self):
        """When RBAC_AUTHENTICATED is True, bearer token is added to headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_credentials = MagicMock()
        mock_token_response = MagicMock()
        mock_token_response.access_token = "test-bearer-token-123"
        mock_credentials.get_token.return_value = mock_token_response

        mock_get_creds = patch(
            "ros.lib.kessel.kessel_shared.get_cached_kessel_auth_credentials",
            return_value=mock_credentials,
        )
        with patch("ros.lib.rbac_interface.RBAC_AUTHENTICATED", True), \
             patch("ros.lib.rbac_interface.RBAC_CA_PATH", "/tmp/ca.crt"), \
             mock_get_creds, \
             patch("requests.request", return_value=mock_response) as mock_req:

            from ros.lib.rbac_interface import fetch_url

            fetch_url(
                "https://rbac.example.com/api/rbac/v1/access/",
                {"X-RH-IDENTITY": "some-identity"},
                MagicMock(),
            )

            # Verify bearer was added alongside x-rh-identity
            call_args = mock_req.call_args
            headers = call_args.kwargs.get("headers") or call_args[1].get("headers")
            assert headers["Authorization"] == "Bearer test-bearer-token-123"
            assert headers["X-RH-IDENTITY"] == "some-identity"
            assert call_args.kwargs.get("verify") == "/tmp/ca.crt"

    def test_authenticated_false_no_bearer(self):
        """When RBAC_AUTHENTICATED is False, no bearer token is added."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch("ros.lib.rbac_interface.RBAC_AUTHENTICATED", False), \
             patch("ros.lib.rbac_interface.RBAC_CA_PATH", None), \
             patch("requests.request", return_value=mock_response) as mock_req:

            from ros.lib.rbac_interface import fetch_url

            fetch_url(
                "https://rbac.example.com/api/rbac/v1/access/",
                {"X-RH-IDENTITY": "some-identity"},
                MagicMock(),
            )

            call_args = mock_req.call_args
            headers = call_args.kwargs.get("headers") or call_args[1].get("headers")
            assert "Authorization" not in headers
            assert headers["X-RH-IDENTITY"] == "some-identity"
            # verify=True when RBAC_CA_PATH is None
            assert (call_args.kwargs.get("verify") or call_args[1].get("verify")) is True

    def test_authenticated_true_missing_credentials_raises(self):
        """When authenticated but credentials unavailable, raise RuntimeError."""
        with patch("ros.lib.rbac_interface.RBAC_AUTHENTICATED", True), \
             patch("ros.lib.rbac_interface.RBAC_CA_PATH", None), \
             patch(
                 "ros.lib.kessel.kessel_shared.get_cached_kessel_auth_credentials",
                 return_value=None,
             ):

            from ros.lib.rbac_interface import fetch_url

            with pytest.raises(RuntimeError, match="OAuth2 credentials are not available"):
                fetch_url(
                    "https://rbac.example.com/api/rbac/v1/access/",
                    {"X-RH-IDENTITY": "some-identity"},
                    MagicMock(),
                )

    def test_ca_path_used_for_tls_verification(self):
        """V2 CA path is passed to requests.request verify parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch("ros.lib.rbac_interface.RBAC_AUTHENTICATED", False), \
             patch("ros.lib.rbac_interface.RBAC_CA_PATH", "/custom/ca-bundle.crt"), \
             patch("requests.request", return_value=mock_response) as mock_req:

            from ros.lib.rbac_interface import fetch_url

            fetch_url(
                "https://rbac.example.com/api/rbac/v1/access/",
                {"X-RH-IDENTITY": "id"},
                MagicMock(),
            )

            call_args = mock_req.call_args
            assert call_args.kwargs.get("verify") == "/custom/ca-bundle.crt" or \
                call_args[1].get("verify") == "/custom/ca-bundle.crt"

    def test_no_ca_path_uses_system_trust(self):
        """No CA path → verify=True (system trust)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch("ros.lib.rbac_interface.RBAC_AUTHENTICATED", False), \
             patch("ros.lib.rbac_interface.RBAC_CA_PATH", None), \
             patch("requests.request", return_value=mock_response) as mock_req:

            from ros.lib.rbac_interface import fetch_url

            fetch_url(
                "https://rbac.example.com/api/rbac/v1/access/",
                {"X-RH-IDENTITY": "id"},
                MagicMock(),
            )

            call_args = mock_req.call_args
            verify_val = call_args.kwargs.get("verify", call_args[1].get("verify") if len(call_args) > 1 else None)
            assert verify_val is True

    def test_original_auth_header_not_mutated(self):
        """Bearer auth creates a copy of auth_header, not mutating original."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_credentials = MagicMock()
        mock_token_response = MagicMock()
        mock_token_response.access_token = "token"
        mock_credentials.get_token.return_value = mock_token_response

        original_header = {"X-RH-IDENTITY": "some-identity"}

        mock_get_creds = patch(
            "ros.lib.kessel.kessel_shared.get_cached_kessel_auth_credentials",
            return_value=mock_credentials,
        )
        with patch("ros.lib.rbac_interface.RBAC_AUTHENTICATED", True), \
             patch("ros.lib.rbac_interface.RBAC_CA_PATH", None), \
             mock_get_creds, \
             patch("requests.request", return_value=mock_response):

            from ros.lib.rbac_interface import fetch_url

            fetch_url(
                "https://rbac.example.com/api/rbac/v1/access/",
                original_header,
                MagicMock(),
            )

            # Original header should not have Authorization added
            assert "Authorization" not in original_header
