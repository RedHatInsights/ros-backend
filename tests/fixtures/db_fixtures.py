import os
import pytest
from ros.lib.app import app, db
from sqlalchemy_utils import database_exists, create_database, drop_database
from ros.lib.models import RhAccount, System


@pytest.fixture(scope="session")
def database():
    DB_USER = os.getenv("ROS_DB_USER", "postgres")
    DB_PASSWORD = os.getenv("ROS_DB_PASS", "postgres")
    DB_HOST = os.getenv("ROS_DB_HOST", "localhost")
    DB_PORT = os.getenv("ROS_DB_PORT", "15432")
    DB_NAME = os.getenv("DB_NAME", "ros-db-test")
    DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}"\
             f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    if not database_exists(DB_URI):
        create_database(DB_URI)

    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
    app.testing = True
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        drop_database(DB_URI)


@pytest.fixture(scope="function")
def db_setup(database):
    yield
    clean_tables()


@pytest.fixture(scope="function")
def db_create_account(db_setup):
    account = RhAccount(id=1, account='12345')
    db.session.add(account)
    db.session.commit()


@pytest.fixture(scope="function")
def db_create_system(db_create_account):
    system = System(
        id=1,
        account_id=1,
        inventory_id='ee0b9978-fe1b-4191-8408-cbadbd47f7a2',
        display_name='ip-172-31-11-67.ap-south-1.compute.internal',
        fqdn='ip-172-31-11-67.ap-south-1.compute.internal',
        cloud_provider='aws',
        instance_type='t2.micro',
        rule_hit_details='{"rule_id": "cloud_instance_ros_evaluation|CONSUMPTION_MODEL","component":'
                         '"telemetry.rules.plugins.ros.cloud_instance_ros_evaluation.report_consumption_model",'
                         '"type": "rule","key": "CONSUMPTION_MODEL","details": {"rhel": "8.3","cloud_provider": "aws",'
                         '"instance_type": "t2.micro","type": "rule","error_key": "CONSUMPTION_MODEL"},"tags": [],'
                         '"links": {"jira": ["https://issues.redhat.com/browse/CEECBA-5092"],"kcs": ["T.B.D"]},'
                         '"system_id": "677fb960-e164-48a4-929f-59e2d917b444"}')
    db.session.add(system)
    db.session.commit()


def clean_tables():
    db.session.expire_all()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
