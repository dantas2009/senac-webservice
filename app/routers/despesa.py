from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from passlib.context import CryptContext
from starlette import status
from app.database import SessionLocal
from app.models import Categorias, Despesas, Icones
from app.routers import auth
from dateutil.relativedelta import relativedelta


bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/despesas',
    tags=['Despesas']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Despesa(BaseModel):
    id_categoria: int
    despesa: str
    valor: float
    vencimento: str
    pagamento: str

class DespesaParcelada(BaseModel):
    id_categoria: int
    despesa: str
    valor: float
    parcelas: int
    data_primeiro_vencimento: str
    dia_vencimento: int

class DespesaPagamento(BaseModel):
    pagamento: str


db_dependency = Annotated[Session, Depends(get_db)]
auth_dependency = Annotated[dict, Depends(auth.buscar_usuario_auth)]

def calcular_proximo_mes(data_referencia, dia_vencimento):
    proximo_mes = data_referencia + relativedelta(months=1)
    ultimo_dia_mes = ((datetime(proximo_mes.year, proximo_mes.month, 1) + relativedelta(months=1)) - relativedelta(days=1)).day
    proxima_data_vencimento = datetime(proximo_mes.year, proximo_mes.month, min(dia_vencimento,  ultimo_dia_mes))
    return proxima_data_vencimento

@router.post("/")
async def add(despesa: Despesa, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    despesa_db = Despesas(
        id_usuario = id_usuario,
        id_categoria = despesa.id_categoria,
        despesa = despesa.despesa,
        valor = despesa.valor,
        vencimento = despesa.vencimento,
        pagamento = despesa.pagamento
    )

    db.add(despesa_db)
    db.commit()

    return {}

@router.post("/parceladas")
async def add_parcelado(despesa_parcelada: DespesaParcelada, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    id_categoria = despesa_parcelada.id_categoria
    despesa = despesa_parcelada.despesa
    valor = despesa_parcelada.valor / despesa_parcelada.parcelas
    parcelas = despesa_parcelada.parcelas
    dia_vencimento = despesa_parcelada.dia_vencimento

    #Começa o vencimento com um mês anterior para que o próximo mês seja o mês desejado, como primeiro.
    vencimento = datetime.strptime(despesa_parcelada.data_primeiro_vencimento, "%m-%Y") - relativedelta(months=1)

    for i in range(1, (parcelas + 1)):
        vencimento = calcular_proximo_mes(vencimento, dia_vencimento)
        despesa_db = Despesas(
            id_usuario = id_usuario,
            id_categoria = id_categoria,
            despesa = f'{despesa} - {i} de {parcelas}',
            valor = valor,
            vencimento = vencimento,
            pagamento = ''
        )

        db.add(despesa_db)

    db.commit()

    return {}

@router.patch("/pagamento/{id_despesa}")
async def editar(id_despesa: int, despesa: DespesaPagamento, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    despesa_db = db.query(Despesas).filter(and_(Despesas.id_usuario == id_usuario, Despesas.id_despesa == id_despesa)).first()

    despesa_db.pagamento = despesa.pagamento
    
    db.commit()

    return {}


@router.put("/{id_despesa}")
async def editar(id_despesa: int, despesa: Despesa, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    despesa_db = db.query(Despesas).filter((Despesas.id_usuario == id_usuario) and (Despesas.id_despesa == id_despesa) ).first()

    despesa_db.id_categoria = despesa.id_categoria
    despesa_db.despesa = despesa.despesa
    despesa_db.valor = despesa.valor
    despesa_db.vencimento = despesa.vencimento
    despesa_db.pagamento = despesa.pagamento
    
    db.commit()

    return {}

@router.delete("/{id_despesa}")
async def remover(id_despesa: int, usuario: auth_dependency, db: db_dependency ):
    id_usuario = usuario['id_usuario']

    despesa_db = db.query(Despesas).filter(and_(Despesas.id_usuario == id_usuario, Despesas.id_despesa == id_despesa) ).first()

    db.delete(despesa_db)
    db.commit()

    return {}

@router.get("/despesa/{id_despesa}", status_code=status.HTTP_200_OK)
async def buscar(id_despesa: int, usuario: auth_dependency, db: db_dependency):
    
    id_usuario = usuario['id_usuario']
    despesa = db.query(Despesas).filter((Despesas.id_usuario == id_usuario) & (Despesas.id_despesa == id_despesa)).options(joinedload(Despesas.categorias).joinedload(Categorias.icones)).first()
    return despesa

@router.get("/", status_code=status.HTTP_200_OK)
async def buscar_todos(
    usuario: auth_dependency, 
    db: db_dependency, 
    skip: int = Query(0, ge=0), 
    limit: int = Query(10, le=100), 
    categoria: int = 0, 
    pesquisa: str = '',
    inicio: str = '',
    fim: str = ''):
    
    id_usuario = usuario['id_usuario']
    despesas_query = (db.query(Despesas).filter(Despesas.id_usuario == id_usuario).options(joinedload(Despesas.categorias).joinedload(Categorias.icones)))
    
    #Filtro por categoria
    if categoria != 0:
        despesas_query = despesas_query.filter(Despesas.id_categoria == categoria)

    #Filtro pela data de vencimento
    if inicio and fim:
        data_inicio = datetime.strptime(inicio, "%d/%m/%Y")
        data_fim = datetime.strptime(fim, "%d/%m/%Y") + timedelta(days=1)

        despesas_query = despesas_query.filter(
            and_(
                Despesas.vencimento >= data_inicio,
                Despesas.vencimento <= data_fim
            )
        )

    
    #Filtro por Despesa ou Valor
    if pesquisa:
        valor = pesquisa.replace(".", "").replace(",", ".").replace(" ", "").replace("R", "").replace("$", "").rstrip('0').rstrip('.')
        despesas_query = despesas_query.filter(
            or_(
                Despesas.despesa.ilike(f"%{pesquisa}%"),
                Despesas.valor.ilike(f"%{valor}%")
            )
        )

    despesas = despesas_query.order_by(desc(Despesas.id_despesa)).offset(skip).limit(limit).all()
    total = despesas_query.count()

    despesa_serialized = [despesa.serialize() for despesa in despesas]


    return {  'despesas': despesa_serialized , "total": total }

