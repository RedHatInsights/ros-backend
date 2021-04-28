from ros.lib.models import System
from ros.lib.app import db


def db_get_host(host_id):
    return db.session.query(System).filter_by(inventory_id=host_id).first()
