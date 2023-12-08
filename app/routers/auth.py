from datetime import timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel
import requests
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from starlette import status
from app.database import SessionLocal
from app.models import LoginSocial, Usuarios
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from app.send_email import recuperar_senha_mail

router = APIRouter(
    prefix='/auth',
    tags=['Autenticação']
)

SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_ALGORITHM = os.getenv("SECRET_ALGORITHM")

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

class Token(BaseModel):
    access_token: str
    token_type: str

class Login(BaseModel):
    email: str
    senha: str

class Usuario(BaseModel):
    nome: str
    email: str
    senha: str

class Recupear(BaseModel):
    email: str

class NovaSenha(BaseModel):
    token: str
    senha: str

class LoginSocialRequest(BaseModel):
    token: str
    provedor: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def auth_usuario(email: str, senha: str, db):
    usuario = db.query(Usuarios).filter(Usuarios.email == email).first()
    if not usuario:
        return False
    if not bcrypt_context.verify(senha, usuario.senha):
        return False
    return usuario

def criar_access_token(email: str, id_usuario: int):
    encode = {'sub': email, 'id': id_usuario, 'datetime': datetime.now().isoformat() }
    return jwt.encode(encode, SECRET_KEY, algorithm=SECRET_ALGORITHM)

async def buscar_usuario_auth(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[SECRET_ALGORITHM])
        email: str = payload.get('sub')
        id_usuario: int = payload.get('id')
        if email is None or id_usuario is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        
        return {'email': email, 'id_usuario': id_usuario}
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

async def buscar_usuario_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[SECRET_ALGORITHM])
        email: str = payload.get('sub')
        id_usuario: int = payload.get('id')
        if email is None or id_usuario is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user .'
            )
        
        return {'email': email, 'id_usuario': id_usuario}
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

async def auth_usuario_token(login: LoginSocialRequest, db):
    
    login_social = db.query(LoginSocial).filter(LoginSocial.token == login.token).first()

    if login_social:
        usuario = db.query(Usuarios).filter(Usuarios.id_usuario == login_social.id_usuario).first()
        if usuario:
            return usuario

    provedor_usuario = { 'email' : '' }
    if login.provedor.lower() == 'google':
        provedor_usuario = await google_login(login.token)
    
    if login.provedor.lower() == 'facebook':
        provedor_usuario = await facebook_login(login.token)
    
    usuario = db.query(Usuarios).filter(Usuarios.email == provedor_usuario['email']).first()
    if not usuario:
        usuario = Usuarios(nome=provedor_usuario['name'], email=provedor_usuario['email'], senha='', limite_gastos=0, status=True, criado=datetime.now())
        db.add(usuario)

    login_social = db.query(LoginSocial).filter(and_(LoginSocial.id_usuario == usuario.id_usuario, LoginSocial.provedor == login.provedor)).first()
    if login_social:
        login_social.token = login.token
    else:
        login_social = LoginSocial(id_usuario=usuario.id_usuario, token=login.token, provedor=login.provedor.lower())
        db.add(login_social)

    db.commit()

    return usuario

async def google_login(token: str):
    try:
        response = httpx.get(f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}")
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="Error retrieving Google user data")
    except httpx.HTTPError:
        raise HTTPException(status_code=500, detail="Internal server error")

async def facebook_login(token: str):
    try:
        response = httpx.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}")
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="Error retrieving Facebook user data")
    except httpx.HTTPError:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/token", response_model=Token)
async def token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    
    usuario = auth_usuario(form_data.username, form_data.password, db)
    
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    token = criar_access_token(usuario.email, usuario.id_usuario)

    return {'access_token': token, 'token_type': 'bearer'}

@router.post("/login", response_model=Token)
async def login(login: Login, db: db_dependency ):
    
    usuario = auth_usuario(login.email, login.senha, db)
    
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    
    token = criar_access_token(usuario.email, usuario.id_usuario)

    return {'access_token': token, 'token_type': 'bearer'}

@router.post("/cadastro", response_model=Token)
async def cadastro(usuario: Usuario, db: db_dependency ):
    try:
        usuario_db = Usuarios(
            nome=usuario.nome,
            email=usuario.email,
            senha=bcrypt_context.hash(usuario.senha),
            limite_gastos=0,
            status=True,
            criado=datetime.now(),
        )
        
        db.add(usuario_db)
        db.commit()

        token = criar_access_token(usuario_db.email, usuario_db.id_usuario)

        return {'access_token': token, 'token_type': 'bearer'}
    except SQLAlchemyError:
        db.rollback() 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro ao cadastrar usuário.')

@router.post("/recuperar/mail", response_description="recuperar senha")
async def recuperar_senha(recuperar: Recupear, db: db_dependency ):
    usuario_db = db.query(Usuarios).filter(Usuarios.email == recuperar.email).first()

    if usuario_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    
    expires = datetime.now() + timedelta(hours=20)
    encode = { 'sub': usuario_db.email, 'id': usuario_db.id_usuario, 'exp': expires }
    
    token = jwt.encode(encode, SECRET_KEY, algorithm=SECRET_ALGORITHM)

    URL_RESET_PASSWORD = os.getenv("URL_RESET_PASSWORD")

    reset_link = f'{URL_RESET_PASSWORD}?token={token}'

    await recuperar_senha_mail(
        "Recuperar Senha", 
        usuario_db.email, 
        {
            "nome": usuario_db.nome,
            "reset_link": reset_link
        }
    )

    return {}

@router.post("/recuperar/senha", response_description="recuperar senha")
async def recuperar_senha(nova_senha: NovaSenha, db: db_dependency ):

    usuario = await buscar_usuario_token(nova_senha.token)
    usuario_db = db.query(Usuarios).filter(Usuarios.id_usuario == usuario['id_usuario']).first()

    if usuario_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    
    usuario_db.senha=bcrypt_context.hash(nova_senha.senha),
    db.commit()

    token = criar_access_token(usuario_db.email, usuario_db.id_usuario)

    return {'access_token': token, 'token_type': 'bearer'}

@router.post("/social")
async def login_social(login: LoginSocialRequest, db: db_dependency ):

    usuario = await auth_usuario_token(login, db)
    
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    
    token = criar_access_token(usuario.email, usuario.id_usuario)

    return {'access_token': token, 'token_type': 'bearer'}
