from datetime import timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import requests
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from starlette import status
from app.database import SessionLocal
from app.models import Usuarios
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user.'
            )
        
        return {'email': email, 'id_usuario': id_usuario}
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')


@router.post("/token", response_model=Token)
async def token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    
    usuario = auth_usuario(form_data.username, form_data.password, db)
    
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    
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


#GOOGLE AUTH


#GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
#GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
#GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

#@router.post("/google/token")
#async def login_google():
#    return {
#        "url": f'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline'
#    }

#@router.post("/google/login")
#async def auth_google(code: str):
#    token_url = "https://accounts.google.com/o/oauth2/token"
#    data = {
#        "code": code,
#        "client_id": GOOGLE_CLIENT_ID,
#        "client_secret": GOOGLE_CLIENT_SECRET,
#        "redirect_uri": GOOGLE_REDIRECT_URI,
#        "grant_type": "authorization_code",
#    }
#    response = requests.post(token_url, data=data)
#    access_token = response.json().get("access_token")
#    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f'Bearer {access_token}'})
#    return user_info.json()
