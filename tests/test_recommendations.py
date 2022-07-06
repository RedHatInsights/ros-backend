from ros.api.main import app
from ros.lib.models import db
from tests.helpers.db_helper import db_get_host


def test_recommendations_no_cp(
        auth_token,
        db_setup,
        db_create_account,
        db_create_system,
        db_create_performance_profile,
        db_instantiate_rules
):

    system_record = db_get_host('ee0b9978-fe1b-4191-8408-cbadbd47f7a3')
    system_record.cloud_provider = None
    db.session.commit()

    with app.test_client() as client:
        response = client.get(
            '/api/ros/v1/systems/ee0b9978-fe1b-4191-8408-cbadbd47f7a3/suggestions',
            headers={"x-rh-identity": auth_token}
        )
        assert response.status_code == 200
        assert response.json["meta"]["count"] == 0
        assert response.json["data"] == []
