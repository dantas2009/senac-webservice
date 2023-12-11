from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, desc
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from passlib.context import CryptContext
from starlette import status
from app.database import get_db
from app.models import Categorias, Despesas, Icones, Usuarios
from app.routers import auth
from dateutil.relativedelta import relativedelta
import calendar



bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/dashboard',
    tags=['Dashboard']
)

class Despesa(BaseModel):
    id_categoria: int
    despesa: str
    valor: float
    vencimento: str
    pagamento: str


db_dependency = Annotated[Session, Depends(get_db)]
auth_dependency = Annotated[dict, Depends(auth.buscar_usuario_auth)]


@router.get("/cards", status_code=status.HTTP_200_OK)
async def dashboard_cards(
    usuario: auth_dependency, 
    db: db_dependency, ):

    id_usuario = usuario['id_usuario']

    data_atual = datetime.now().date()

    despesas_atrasadas = (
        db.query(Despesas)
        .filter(
            Despesas.id_usuario == id_usuario,
            Despesas.vencimento < data_atual,
            Despesas.pagamento == None
        )
    ).count()

    despesas_pendentes = (
        db.query(Despesas)
        .filter(
            Despesas.id_usuario == id_usuario,
            Despesas.vencimento >= data_atual,
            Despesas.pagamento == None
        )
    ).count()

    primeiro_dia_mes_atual = data_atual.replace(day=1)
    ultimo_dia_mes_atual = (data_atual.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    primeiro_dia_mes_anterior = (data_atual.replace(day=1) - timedelta(days=1)).replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)

    despesas_mes_atual = (
        db.query(Despesas)
        .filter(
            Despesas.id_usuario == id_usuario,
            Despesas.vencimento >= primeiro_dia_mes_atual,
            Despesas.vencimento <= ultimo_dia_mes_atual
        )
    ).count()

    despesas_mes_anterior = (
        db.query(Despesas)
        .filter(
            Despesas.id_usuario == id_usuario,
            Despesas.vencimento >= primeiro_dia_mes_anterior,
            Despesas.vencimento <= ultimo_dia_mes_anterior
        )
    ).count()

    return {
        'despesas_atrasadas' : despesas_atrasadas,
        'despesas_pendentes' : despesas_pendentes,
        'despesas_mes_atual' : despesas_mes_atual,
        'despesas_mes_anterior' : despesas_mes_anterior
    }


@router.get("/line_ano", status_code=status.HTTP_200_OK)
async def dashboard_line_ano(
    usuario: auth_dependency, 
    db: db_dependency, ):

    id_usuario = usuario['id_usuario']

    data_atual = datetime.now()

    valores_por_mes = []

    for i in range(12):
        mes = i + 1
        mes_primeiro_dia = datetime(data_atual.year, mes, 1)
        mes_ultimo_dia = datetime(data_atual.year, mes, calendar.monthrange(data_atual.year, mes)[1]) + timedelta(days=1)

        despesas_mes = (
            db.query(Despesas)
            .filter(
                Despesas.id_usuario == id_usuario,
                Despesas.vencimento >= mes_primeiro_dia,
                Despesas.vencimento <= mes_ultimo_dia
            )
            .all()
        )

        total_despesas_mes = sum(despesa.valor for despesa in despesas_mes)
        valores_por_mes.append(total_despesas_mes)

    despesas_qtd_ano = (
        db.query(Despesas)
        .filter(
            Despesas.id_usuario == id_usuario,
            Despesas.vencimento >= datetime(data_atual.year, 1, 1),
            Despesas.vencimento <= datetime((data_atual.year + 1), 1, 1),
        )
        .count()
    )

    usuario = (
            db.query(Usuarios)
            .filter(Usuarios.id_usuario >= id_usuario)
            .first()
        )
    
    limite_gastos = usuario.limite_gastos

    return {
        'valores_por_mes' : valores_por_mes,
        'despesas_qtd_ano': despesas_qtd_ano,
        'limite_gastos' : limite_gastos
    }

@router.get("/pie_mes", status_code=status.HTTP_200_OK)
async def dashboard_pie_mes(
    usuario: auth_dependency, 
    db: db_dependency, ):

    id_usuario = usuario['id_usuario']

    hoje = datetime.now()
    mes_passado_inicio = (hoje.replace(day=1) - timedelta(days=hoje.day)).replace(day=1)
    mes_passado_fim = hoje.replace(day=1) - timedelta(days=hoje.day)

    despesas_mes = (
    db.query(Categorias.categoria, func.sum(Despesas.valor).label("valor"))
        .outerjoin(Despesas, Categorias.id_categoria == Despesas.id_categoria)
        .filter(
            Despesas.vencimento >= mes_passado_inicio,
            Despesas.vencimento <= mes_passado_fim,
            Despesas.id_usuario == id_usuario
        )
        .group_by(Categorias.categoria)
        .all()
    )

    return {
        'despesas_mes' : despesas_mes,
    }

@router.get("/pie_ano", status_code=status.HTTP_200_OK)
async def dashboard_pie_ano(
    usuario: auth_dependency, 
    db: db_dependency, ):

    id_usuario = usuario['id_usuario']

    ano = datetime.now().year
    ano_inicio = datetime(ano, 1, 1)
    ano_fim = datetime((ano + 1), 1, 1)

    despesas_ano = (
    db.query(Categorias.categoria, func.sum(Despesas.valor).label("valor"))
        .outerjoin(Despesas, Categorias.id_categoria == Despesas.id_categoria)
        .filter(
            Despesas.vencimento >= ano_inicio,
            Despesas.vencimento <= ano_fim,
            Despesas.id_usuario == id_usuario
        )
        .group_by(Categorias.categoria)
        .all()
    )

    return {
        'despesas_ano' : despesas_ano,
    }