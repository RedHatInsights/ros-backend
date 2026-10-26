import time

import grpc
from ros.lib.config import get_logger
from ros.lib.config import KESSEL_INSECURE
from kessel.inventory.v1beta2 import ClientBuilder

LOG = get_logger(__name__)

# Singleton storage
_GRPC_CHANNEL = None
_GRPC_STUB = None
_AUTH_CREDENTIALS = None
_AUTH_FAILURE_TIMESTAMP = None
_AUTH_FAILURE_BACKOFF_SECS = 30


def get_cached_kessel_auth_credentials():
    """
    Get or create cached OAuth2 credentials to avoid expensive OIDC discovery calls.
    This is a shared cache used by both the gRPC singleton and KesselClient instances.

    On failure (e.g. OIDC issuer unreachable), the failure is cached for
    _AUTH_FAILURE_BACKOFF_SECS seconds so that each request does not repeat
    the synchronous discovery attempt during an outage.

    Returns:
        OAuth2ClientCredentials object or None if creation fails
    """
    global _AUTH_CREDENTIALS, _AUTH_FAILURE_TIMESTAMP
    if _AUTH_CREDENTIALS is not None:
        return _AUTH_CREDENTIALS

    # Avoid hammering OIDC if a recent attempt failed
    if _AUTH_FAILURE_TIMESTAMP is not None:
        elapsed = time.monotonic() - _AUTH_FAILURE_TIMESTAMP
        if elapsed < _AUTH_FAILURE_BACKOFF_SECS:
            LOG.warning(
                "OAuth2 credential creation failed %.0fs ago, "
                "backing off for %ds",
                elapsed, _AUTH_FAILURE_BACKOFF_SECS,
            )
            return None

    from ros.lib.config import create_kessel_oauth2_credentials
    LOG.debug("Creating shared OAuth2 credentials cache")
    result = create_kessel_oauth2_credentials()
    if result is None:
        _AUTH_FAILURE_TIMESTAMP = time.monotonic()
    else:
        _AUTH_CREDENTIALS = result
        _AUTH_FAILURE_TIMESTAMP = None
    return result


def get_kessel_stub(host):
    """
    Get or create a Kessel gRPC stub with OAuth2 authentication.

    Args:
        host: Kessel service host and port

    Returns:
        KesselInventoryServiceStub instance
    """
    global _GRPC_CHANNEL, _GRPC_STUB

    if _GRPC_STUB is None:
        try:

            LOG.debug("Creating OAuth2 authenticated Kessel connection")

            # Create OAuth2 client credentials using shared cache
            auth_credentials = get_cached_kessel_auth_credentials()
            if not auth_credentials:
                raise Exception("Failed to create OAuth2 credentials")

            # Create authenticated stub and channel using ClientBuilder
            LOG.debug(f"Creating authenticated Kessel client for {host}")

            if KESSEL_INSECURE:
                # Use local channel credentials for insecure connections
                LOG.info("Using insecure channel credentials with OAuth2 authentication")
                _GRPC_STUB, _GRPC_CHANNEL = (
                    ClientBuilder(host)
                    .insecure()
                    .build()
                )
            else:
                # Use default secure credentials for TLS connections
                LOG.info("Using secure TLS channel credentials with OAuth2 authentication")
                _GRPC_STUB, _GRPC_CHANNEL = (
                    ClientBuilder(host)
                    .oauth2_client_authenticated(auth_credentials)
                    .build()
                )
            LOG.info("Successfully created authenticated Kessel client")
        except grpc.RpcError as err:
            LOG.error(f"Failed to establish grpc connection to {host}: {err}")
            raise
        except Exception as err:
            LOG.error(f"OAuth2 authentication failed: {err}")
            raise

    return _GRPC_STUB
