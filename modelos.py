from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class TipoTransacao(Enum):
    RECEITA = "Receita"
    DESPESA = "Despesa"

@dataclass
class Categoria:
    id: int
    nome: str
    tipo: TipoTransacao

@dataclass
class Transacao:
    id: int
    descricao: str
    valor: float
    categoria: Categoria
    data: datetime

@dataclass
class Orcamento:
    categoria_id: int
    limite_mensal: float
    mes_ano: str #  formato MM/AAAA