def test_root_returns_running_message(client):
    """The simplest possible test: does the app boot and respond at all."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API is running"}
