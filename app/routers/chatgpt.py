from datetime import date
import json
import os
import openai 
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
import httpx
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext
from starlette import status
from app.database import SessionLocal
from app.models import Icones, Categorias
from app.routers import auth

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/chatgpt',
    tags=['ChatGPT']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
auth_dependency = Annotated[dict, Depends(auth.buscar_usuario_auth)]

class Input(BaseModel):
    input: str

@router.post("/")
async def chat_input(input: Input, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    categorias = db.query(Categorias).filter(
                and_(
                    or_(Categorias.id_usuario == id_usuario, Categorias.id_usuario == None), 
                    Categorias.status
                )).options(joinedload(Categorias.icones)).all()
    
    string_categorias = ''
    for categoria in categorias:
        string_categorias += f"ID: {categoria.id_categoria}, Categoria: {categoria.categoria}\n"

    despesa = await chatgpt(input.input, string_categorias)

    return despesa 

async def chatgpt(input: str, categorias: str):

    openai.api_key = os.getenv('CHATGPT_SECRET')

    functions = [
        {
            "name": "criar_despesa",
            "description": "Gostaria de criar uma despesa atraves de um input, se não for uma despesa, retorne um json vazio",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_categoria": {
                        "type": "integer",
                        "description": f"Categorias disponivies: {categorias}"
                    },
                    "despesa": {
                        "type": "string",
                        "description": "Nome da despesa."
                    },
                    "valor": {
                        "type": "string",
                        "description": "Valor da despesa em decimal"
                    },
                    "vencimento": {
                        "type": "string",
                        "description": f"Data de vencimento da despesa em formato datetime hoje o dia é: {date.today()}"
                    },
                    "pagamento": {
                        "type": "string",
                        "description": f"Data de pagamento da despesa é em formato datetime hoje o dia é: {date.today()} caso o pagamento não tenha sido efetuado, retorne null"
                    },
                }
            }
        }
    ]
 
    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo-16k-0613",
        messages = [
            {
                "role": "system",
                "content": "You are a useful assistant."
            },
            {
                "role": "user",
                "content": f"Aqui o input: {input}. Retorne a despesa em json."
            }
        ],
        functions = functions,
        function_call = {
            "name": functions[0]["name"]
        }
    )
    
    arguments = response.choices[0]["message"]["function_call"]["arguments"]

    despesa = json.loads(arguments)

    if despesa['despesa'] == None or 'valor' not in  despesa or 'id_categoria' not in despesa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    return json.loads(arguments)
