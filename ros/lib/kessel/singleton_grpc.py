import grpc
from ros.lib.config import get_logger
from kessel.inventory.v1beta2 import inventory_service_pb2_grpc

LOG = get_logger(__name__)

# Singleton storage
_GRPC_CHANNEL = None
_GRPC_STUB = None


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
            from ros.lib.config import (
                KESSEL_AUTH_CLIENT_ID,
                KESSEL_AUTH_CLIENT_SECRET,
                KESSEL_AUTH_OIDC_ISSUER,
                KESSEL_INSECURE,
                create_kessel_oauth2_credentials
            )

            if KESSEL_AUTH_CLIENT_ID and KESSEL_AUTH_CLIENT_SECRET and KESSEL_AUTH_OIDC_ISSUER:
                try:
                    from kessel.inventory.v1beta2 import ClientBuilder

                    LOG.debug("Creating OAuth2 authenticated Kessel connection")

                    # Create OAuth2 client credentials using shared function
                    auth_credentials = create_kessel_oauth2_credentials()
                    if not auth_credentials:
                        raise Exception("Failed to create OAuth2 credentials")

                    # Create authenticated stub and channel using ClientBuilder
                    LOG.debug(f"Creating authenticated Kessel client for {host}")

                    if KESSEL_INSECURE:
                        # Use local channel credentials for insecure connections
                        LOG.info("Using insecure channel credentials with OAuth2 authentication")
                        _GRPC_STUB, _GRPC_CHANNEL = (
                            ClientBuilder(host)
                            .oauth2_client_authenticated(auth_credentials, grpc.local_channel_credentials())
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

                except ImportError:
                    LOG.warning("kessel_sdk OAuth2 authentication not available, falling back to insecure connection")
                    _GRPC_CHANNEL = grpc.insecure_channel(host)
                    _GRPC_STUB = inventory_service_pb2_grpc.KesselInventoryServiceStub(_GRPC_CHANNEL)
                except Exception as err:
                    LOG.warning(f"OAuth2 authentication failed: {err}, falling back to insecure connection")
                    _GRPC_CHANNEL = grpc.insecure_channel(host)
                    _GRPC_STUB = inventory_service_pb2_grpc.KesselInventoryServiceStub(_GRPC_CHANNEL)
            else:
                LOG.error("OAuth2 credentials are required but not provided")
                raise ValueError(
                    "KESSEL_AUTH_CLIENT_ID, KESSEL_AUTH_CLIENT_SECRET, and KESSEL_AUTH_OIDC_ISSUER must be set"
                )

        except grpc.RpcError as err:
            LOG.error(f"Failed to establish grpc connection to {host}: {err}")
            raise

    return _GRPC_STUB
