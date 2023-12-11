from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext
from starlette import status
from app.database import get_db
from app.models import Icones, Categorias
from app.routers import auth

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/categorias',
    tags=['Categorias']
)

class Categoria(BaseModel):
    id_icone: int
    categoria: str
    status: bool

db_dependency = Annotated[Session, Depends(get_db)]
auth_dependency = Annotated[dict, Depends(auth.buscar_usuario_auth)]

@router.post("/")
async def add(categoria: Categoria, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    categoria_db = Categorias(
        id_icone = categoria.id_icone,
        id_usuario = id_usuario,
        categoria = categoria.categoria,
        status = categoria.status
    )

    db.add(categoria_db)
    db.commit()

    return {}

@router.put("/{id_categoria}")
async def editar(id_categoria: int, categoria: Categoria, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    categoria_db = db.query(Categorias).filter(Categorias.id_categoria == id_categoria, Categorias.id_usuario == id_usuario).first()
    if not categoria_db:
        raise HTTPException(status_code=404, detail="Categoria não encontrado")

    categoria_db.id_icone = categoria.id_icone,
    categoria_db.categoria = categoria.categoria,
    categoria_db.status = categoria.status
    
    db.commit()

    return {}

@router.get("/categoria/{id_categoria}", status_code=status.HTTP_200_OK)
async def buscar(id_categoria: int, usuario: auth_dependency, db: db_dependency):
    id_usuario = usuario['id_usuario']
    categoria = db.query(Categorias).filter((Categorias.id_usuario == id_usuario) & (Categorias.id_categoria == id_categoria)).options(joinedload(Categorias.icones)).first()

    return categoria

@router.get("/", status_code=status.HTTP_200_OK)
async def buscar_todos(usuario: auth_dependency, db: db_dependency):
    
    id_usuario = usuario['id_usuario']
    categorias = db.query(Categorias).filter((Categorias.id_usuario == id_usuario) | (Categorias.id_usuario == None)).options(joinedload(Categorias.icones)).all()

    return categorias

@router.get("/disponivel", status_code=status.HTTP_200_OK)
async def buscar_disponivel(usuario: auth_dependency, db: db_dependency):
    
    id_usuario = usuario['id_usuario']
    categorias = db.query(Categorias).filter(
                and_(
                    or_(Categorias.id_usuario == id_usuario, Categorias.id_usuario == None), 
                    Categorias.status
                )).options(joinedload(Categorias.icones)).all()

    return categorias

