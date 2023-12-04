from pydantic import BaseModel
from .database import Base
from sqlalchemy import Column, Integer, String, Boolean, Float, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from babel.numbers import format_currency
from babel import Locale


class Usuarios(Base):
    __tablename__ = 'usuarios'

    id_usuario = Column(Integer, primary_key=True, index=True)
    nome = Column(String(256), nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    senha = Column(String(2048), nullable=False)
    limite_gastos = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Boolean, default=True)
    criado = Column(DateTime, nullable=False)

    categorias = relationship("Categorias", back_populates="usuario")

    def serialize(self):
        return {
            'id_usuario': self.id_usuario,
            'nome': self.nome,
            'email': self.email,
            'limite_gastos': self.limite_gastos,
        }

class Despesas(Base):
    __tablename__ = 'despesas'

    id_despesa = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=True)
    id_categoria = Column(Integer, ForeignKey('categorias.id_categoria'))
    despesa = Column(String(256), nullable=False)
    valor = Column(DECIMAL(10, 2), nullable=False)
    vencimento = Column(DateTime, nullable=False)
    pagamento = Column(DateTime)

    categorias = relationship("Categorias", back_populates="despesas")

    def serialize(self):
        pagamento = ''
        if self.pagamento and self.pagamento != '0000-00-00 00:00:00':
            pagamento = self.pagamento.strftime('%d/%m/%Y %H:%M:%S')
        return {
            'id_despesa': self.id_despesa,
            'id_usuario': self.id_usuario,
            'id_categoria': self.id_categoria,
            'despesa': self.despesa,
            'valor': format_currency(self.valor, 'BRL', locale='pt_BR'),
            'vencimento': self.vencimento.strftime('%d/%m/%Y %H:%M:%S'),
            'pagamento':  pagamento,
            'categorias': self.categorias,
        }

class Categorias(Base):
    __tablename__ = 'categorias'

    id_categoria = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'))
    id_icone = Column(Integer, ForeignKey('icones.id_icone'))
    categoria = Column(String(256), nullable=False)
    status = Column(Boolean, default=True)

    usuario = relationship("Usuarios", back_populates="categorias")
    despesas = relationship("Despesas", back_populates="categorias")
    icones = relationship("Icones", back_populates="categorias")

class Icones(Base):
    __tablename__ = 'icones'

    id_icone = Column(Integer, primary_key=True, index=True)
    icone = Column(String(256), nullable=False)

    categorias = relationship("Categorias", back_populates="icones")





