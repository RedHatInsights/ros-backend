from ros.lib.models import System
from ros.lib.app import db


def db_get_host(host_id):
    return db.session.query(System).filter_by(inventory_id=host_id).first()


def db_get_record(model, **filters):
    return db.session.query(model).filter_by(**filters).first()


def db_get_records(model, **filters):
    return db.session.query(model).filter_by(**filters)
