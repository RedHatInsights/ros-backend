import grpc
from ros.lib.config import get_logger
from kessel.inventory.v1beta2 import inventory_service_pb2_grpc

LOG = get_logger(__name__)

# Singleton storage
_GRPC_CHANNEL = None
_GRPC_STUB = None


def get_kessel_stub(host, use_auth=True):
    """
    Get or create a Kessel gRPC stub with optional OAuth2 authentication.

    Args:
        host: Kessel service host and port
        use_auth: Whether to attempt OAuth2 authentication

    Returns:
        KesselInventoryServiceStub instance
    """
    global _GRPC_CHANNEL, _GRPC_STUB

    if _GRPC_STUB is None:
        try:
            from ros.lib.config import (
                KESSEL_OAUTH_CLIENT_ID,
                KESSEL_OAUTH_CLIENT_SECRET,
                KESSEL_OAUTH_OIDC_ISSUER,
                KESSEL_USE_TLS
            )

            # Try OAuth2 authentication if credentials are configured
            if use_auth and KESSEL_OAUTH_CLIENT_ID and KESSEL_OAUTH_CLIENT_SECRET and KESSEL_OAUTH_OIDC_ISSUER:
                try:
                    from kessel.authn import OAuth2ClientCredentials, fetch_oidc_discovery

                    LOG.info("Attempting OAuth2 authentication for Kessel connection")

                    # Fetch OIDC discovery to get token endpoint
                    try:
                        LOG.info(f"Fetching OIDC discovery from: {KESSEL_OAUTH_OIDC_ISSUER}")
                        discovery = fetch_oidc_discovery(KESSEL_OAUTH_OIDC_ISSUER)
                        token_endpoint = discovery.token_endpoint

                        if not token_endpoint:
                            raise ValueError("No token_endpoint found in OIDC discovery response")

                        LOG.info(f"Discovered token endpoint: {token_endpoint}")

                    except Exception as discovery_err:
                        LOG.error(f"Failed to fetch OIDC discovery: {discovery_err}")
                        raise discovery_err

                    # Create OAuth2 client credentials with discovered token endpoint
                    auth = OAuth2ClientCredentials(
                        client_id=KESSEL_OAUTH_CLIENT_ID,
                        client_secret=KESSEL_OAUTH_CLIENT_SECRET,
                        token_endpoint=token_endpoint
                    )

                    # Create authenticated channel
                    if KESSEL_USE_TLS:
                        _GRPC_CHANNEL = auth.create_channel(host, secure=True)
                        LOG.info(f"Established authenticated TLS gRPC connection to {host}")
                    else:
                        _GRPC_CHANNEL = auth.create_channel(host, secure=False)
                        LOG.info(f"Established authenticated insecure gRPC connection to {host}")

                except ImportError:
                    LOG.warning("kessel_sdk OAuth2 authentication not available, falling back to insecure connection")
                    _GRPC_CHANNEL = grpc.insecure_channel(host)
                except Exception as err:
                    LOG.warning(f"OAuth2 authentication failed: {err}, falling back to insecure connection")
                    _GRPC_CHANNEL = grpc.insecure_channel(host)
            else:
                # Use insecure connection
                LOG.info("Using insecure gRPC connection to Kessel")
                _GRPC_CHANNEL = grpc.insecure_channel(host)

        except grpc.RpcError as err:
            LOG.error(f"Failed to establish grpc connection to {host}: {err}")
            raise

        _GRPC_STUB = inventory_service_pb2_grpc.KesselInventoryServiceStub(_GRPC_CHANNEL)

    return _GRPC_STUB
