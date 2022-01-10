import datetime
import json
from base64 import b64encode
import pytest

from ros.api.main import app


@pytest.fixture(scope="session")
def auth_token():
    identity = {
        "identity": {
            "account_number": "12345",
            "type": "User",
            "user": {
                "username": "tuser@redhat.com",
                "email": "tuser@redhat.com",
                "first_name": "test",
                "last_name": "user",
                "is_active": True,
                "is_org_admin": False,
                "is_internal": True,
                "locale": "en_US"
            },
            "internal": {
                "org_id": "000001"
            }
        }
    }
    auth_token = b64encode(json.dumps(identity).encode('utf-8'))
    return auth_token


def test_status():
    with app.test_client() as client:
        response = client.get('/api/ros/v1/status')
        assert response.status_code == 200
        assert response.json["status"] == "Application is running!"


def test_is_configured(auth_token, db_setup, db_create_account, db_create_system, db_create_performance_profile):
    with app.test_client() as client:
        response = client.get('/api/ros/v1/is_configured', headers={"x-rh-identity": auth_token})
        sys_response = client.get('/api/ros/v1/systems', headers={"x-rh-identity": auth_token})
        assert response.status_code == 200
        assert response.json["count"] == 1
        assert response.json["systems_stats"]["with_suggestions"] == 1
        assert response.json["systems_stats"]["waiting_for_data"] == 0
        assert response.json["count"] == sys_response.json["meta"]["count"]


def test_systems(auth_token, db_setup, db_create_account, db_create_system, db_create_performance_profile):
    with app.test_client() as client:
        response = client.get('/api/ros/v1/systems', headers={"x-rh-identity": auth_token})
        assert response.status_code == 200
        assert response.json["meta"]["count"] == 1


def test_system_detail(auth_token, db_setup, db_create_account, db_create_system, db_create_performance_profile):
    with app.test_client() as client:
        response = client.get(
            '/api/ros/v1/systems/ee0b9978-fe1b-4191-8408-cbadbd47f7a3',  # inventory_id from db_create_system
            headers={"x-rh-identity": auth_token}
        )
        print(response.json)
        assert response.status_code == 200
        assert response.json["inventory_id"] == 'ee0b9978-fe1b-4191-8408-cbadbd47f7a3'


def test_system_history(auth_token, db_setup, db_create_account, db_create_system, db_create_performance_profile):
    with app.test_client() as client:
        response = client.get(
            '/api/ros/v1/systems/ee0b9978-fe1b-4191-8408-cbadbd47f7a3/history',
            headers={"x-rh-identity": auth_token}
        )
        assert response.status_code == 200
        assert response.json["meta"]["count"] == 1
        assert response.json["data"][0]["report_date"] == str(datetime.datetime.utcnow().date())
        assert response.json["inventory_id"] == 'ee0b9978-fe1b-4191-8408-cbadbd47f7a3'


def test_system_suggestions(
        auth_token,
        db_setup,
        db_create_account,
        db_create_system,
        db_create_performance_profile,
        db_instantiate_rules
):
    with app.test_client() as client:
        response = client.get(
            '/api/ros/v1/systems/ee0b9978-fe1b-4191-8408-cbadbd47f7a3/suggestions',
            headers={"x-rh-identity": auth_token}
        )
        assert response.status_code == 200
        assert response.json["inventory_id"] == 'ee0b9978-fe1b-4191-8408-cbadbd47f7a3'
        assert response.json["meta"]["count"] == 1
        assert response.json["data"][0]["rule_id"] == "ros_instance_evaluation|INSTANCE_IDLE"


def test_system_rating(
        auth_token,
        db_setup,
        db_create_account,
        db_create_system,
        db_create_performance_profile
):
    with app.test_client() as client:
        data_dict = {
                "inventory_id": "ee0b9978-fe1b-4191-8408-cbadbd47f7a3",
                "rating": -1
        }
        response = client.post(
            '/api/ros/v1/rating',
            headers={"x-rh-identity": auth_token},
            data=json.dumps(data_dict)
        )
        assert response.status_code == 201
        assert response.json["inventory_id"] == data_dict['inventory_id']
        assert response.json["rating"] == data_dict['rating']

        # Checking if the set rating shows up on system detail
        test_host_detail = client.get(
            '/api/ros/v1/systems/ee0b9978-fe1b-4191-8408-cbadbd47f7a3',
            headers={"x-rh-identity": auth_token}
        )
        assert test_host_detail.json["rating"] == data_dict['rating']


def test_openapi_endpoint():
    with open("ros/openapi/openapi.json") as f:
        content_from_file = json.loads(f.read())
        f.close()
    with app.test_client() as client:
        response = client.get(
            '/api/ros/v1/openapi.json',
            headers={"x-rh-identity": auth_token}
        )
        assert response.json == content_from_file
