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
_AUTH_FAILED_AT = None
AUTH_FAILURE_BACKOFF_SECS = 30


def get_cached_kessel_auth_credentials():
    """
    Get or create cached OAuth2 credentials to avoid expensive OIDC discovery calls.
    This is a shared cache used by both the gRPC singleton and KesselClient instances.
    A failed creation is not retried for AUTH_FAILURE_BACKOFF_SECS, so an identity
    provider outage doesn't trigger discovery on every request.
    Returns:
        OAuth2ClientCredentials object or None if creation fails
    """
    global _AUTH_CREDENTIALS, _AUTH_FAILED_AT
    if _AUTH_CREDENTIALS is None:
        if _AUTH_FAILED_AT is not None and time.monotonic() - _AUTH_FAILED_AT < AUTH_FAILURE_BACKOFF_SECS:
            return None
        from ros.lib.config import create_kessel_oauth2_credentials
        LOG.debug("Creating shared OAuth2 credentials cache")
        _AUTH_CREDENTIALS = create_kessel_oauth2_credentials()
        _AUTH_FAILED_AT = time.monotonic() if _AUTH_CREDENTIALS is None else None
    return _AUTH_CREDENTIALS


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
