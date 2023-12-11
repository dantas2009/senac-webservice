from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.models import Base
from app.main import app
from app.database import get_db
from tests.log import log

SQLALCHEMY_DATABASE_URL = 'sqlite:///testedb.sqlite'

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)

client = TestClient(app)

faker = Faker()

usuario = {
    "nome": faker.name(),
    "email": faker.email(),
    "senha": faker.password(),
}

def test_cadastro():
    response = client.post(
        "/auth/cadastro",
        json = {
            "nome": usuario["nome"],
            "email": usuario["email"],
            "senha": usuario["senha"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    access_token = data["access_token"]

    client.headers.update({"Authorization": f"Bearer {access_token}"})
    response = client.get("/conta/")

    log.info(response)

    assert response.status_code == 200, response.text

    data = response.json()
    
    assert data["nome"] == usuario["nome"]
    assert data["email"] == usuario["email"]

def test_cadastro_invalido():
    response = client.post(
        "/auth/cadastro",
        json = {
            "nome": usuario["nome"],
            "email": usuario["email"],
            "senha": usuario["senha"],
        },
    )
    assert response.status_code == 500, response.text


def test_login():
    response = client.post(
        "/auth/login",
        json = {
            "email": usuario["email"],
            "senha": usuario["senha"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    access_token = data["access_token"]

    client.headers.update({"Authorization": f"Bearer {access_token}"})
    response = client.get("/conta/")

    log.info(response)

    assert response.status_code == 200, response.text

    data = response.json()
    
    assert data["nome"] == usuario["nome"]
    assert data["email"] == usuario["email"]

def test_login_invalido():
    response = client.post(
        "/auth/login",
        json = {
            "email": 'email_invalido',
            "senha": 'senha_invalida',
        },
    )
    assert response.status_code == 401, response.text