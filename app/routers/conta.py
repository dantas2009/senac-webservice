from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import outerjoin
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from starlette import status
from app.database import SessionLocal
from app.models import Usuarios
from app.routers import auth
from datetime import datetime


bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')


router = APIRouter(
    prefix='/conta',
    tags=['Conta']
)

class Usuario(BaseModel):
    nome: str
    email: str
    senha: str
    senha_antiga: str
    limite_gastos: float


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
auth_dependency = Annotated[dict, Depends(auth.buscar_usuario_auth)]

@router.get("/", status_code=status.HTTP_200_OK)
async def buscar_usuario(usuario: auth_dependency, db: db_dependency):
    usuario_db = db.query(Usuarios).filter(Usuarios.id_usuario == usuario['id_usuario']).first()
    if(usuario_db is None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    
    return usuario_db.serialize()

@router.put("/", status_code=status.HTTP_200_OK)
async def editar(usuario_update: Usuario, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    usuario_db = db.query(Usuarios).filter(Usuarios.id_usuario == id_usuario).first()

    usuario_db.nome = usuario_update.nome
    usuario_db.email = usuario_update.email
    usuario_db.limite_gastos = usuario_update.limite_gastos
    
    if usuario_update.senha and bcrypt_context.verify(usuario_update.senha_antiga, usuario_db.senha):
        usuario_db.senha = bcrypt_context.hash(usuario_update.senha)
    else: 
        if usuario_update.senha:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Senha antiga inválida")
    
    db.commit()

    return {}
