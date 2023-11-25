from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.params import Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session
from .routers import auth, conta, icone, categoria, despesa
from .models import Base
from .database import engine, SessionLocal
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conta.router)
app.include_router(despesa.router)
app.include_router(categoria.router)
app.include_router(icone.router)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]


@app.get("/", tags=["Default"])
def root():
    return {
        "senac": "Pós Full-Stack - Projeto Final",
        "alunos": [
            {"nome": "Daniel Bernado"},
            {"nome": "Gabriel Dantas"}
        ]
    }
