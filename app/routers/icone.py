from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from starlette import status
from app.database import get_db
from app.models import Categorias, Usuarios, Icones
from app.routers import auth

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/icones',
    tags=['Icones']
)

db_dependency = Annotated[Session, Depends(get_db)]
auth_dependency = Annotated[dict, Depends(auth.buscar_usuario_auth)]

@router.get("/disponiveis", status_code=status.HTTP_200_OK)
async def buscar_icones(usuario: auth_dependency, db: db_dependency):
    id_usuario = usuario['id_usuario']
    icones = db.query(Icones).filter(
        ~Icones.id_icone.in_(db.query(Categorias.id_icone).filter((Categorias.id_usuario == id_usuario) | (Categorias.id_usuario == None)))
    ).all()
    
    return icones
