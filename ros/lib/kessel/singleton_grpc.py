import grpc
from ros.lib.config import get_logger
from kessel.inventory.v1beta2 import inventory_service_pb2_grpc

LOG = get_logger(__name__)

# Singleton storage
_GRPC_CHANNEL = None
_GRPC_STUB = None


def get_kessel_stub(host):
    global _GRPC_CHANNEL, _GRPC_STUB

    if _GRPC_STUB is None:
        try:
            _GRPC_CHANNEL = grpc.insecure_channel(host)
        except grpc.RpcError as err:
            LOG.error(f"Failed to establish grpc connection to {host}: {err}")
            raise

        _GRPC_STUB = inventory_service_pb2_grpc.KesselInventoryServiceStub(_GRPC_CHANNEL)

    return _GRPC_STUB
