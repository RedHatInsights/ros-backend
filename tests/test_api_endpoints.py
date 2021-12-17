from ros.api.main import app


def test_status_endpoint():
    with app.test_client() as client:
        response = client.get('/api/ros/v1/status')
        assert response.status_code == 200
        assert response.json["status"] == "Application is running!"
