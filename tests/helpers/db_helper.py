from ros.lib.models import System, PerformanceProfile
from ros.lib.app import db


def db_get_host(host_id):
    return db.session.query(System).filter_by(inventory_id=host_id).first()


def db_get_perf_profile(system_id):
    return db.session.query(PerformanceProfile).filter_by(system_id=system_id).first()
