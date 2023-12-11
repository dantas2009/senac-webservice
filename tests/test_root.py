from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    body = response.json()
    assert response.status_code == 200
    assert body["alunos"] ==  [
        {"nome": "Daniel Bernado"},
        {"nome": "Gabriel Dantas"}
    ]