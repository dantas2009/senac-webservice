from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.params import Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session

from app.routers import chatgpt, dashboard
from .routers import auth, conta, icone, categoria, despesa
from .models import Base
from .database import engine, get_db
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
app.include_router(dashboard.router)
app.include_router(conta.router)
app.include_router(despesa.router)
app.include_router(categoria.router)
app.include_router(icone.router)
app.include_router(chatgpt.router)

Base.metadata.create_all(bind=engine)

#db_dependency = Annotated[Session, Depends(get_db)]

@app.get("/", tags=["Default"])
def root():
    return {
        "senac": "Pós Full-Stack - Projeto Final",
        "alunos": [
            {"nome": "Daniel Bernado"},
            {"nome": "Gabriel Dantas"}
        ],
        "professor": "Marcelo Batalha"
    }
