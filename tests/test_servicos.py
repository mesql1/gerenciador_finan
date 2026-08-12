import pytest
from datetime import datetime
from modelos import Transacao, Categoria, TipoTransacao, Orcamento
from servicos import GerenciadorFin

@pytest.fixture
def gerenciador_dados():
    gerenciador = GerenciadorFin()

    cat_receita = Categoria(id=1, nome="Salário", tipo=TipoTransacao.RECEITA)
    cat_despesa = Categoria(id=2, nome="Mercado", tipo=TipoTransacao.DESPESA)

    t1 = Transacao(id=1, descricao="Salário Mensal", valor=3000.0, categoria=cat_receita, data=datetime(2026, 8, 1))
    t2 = Transacao(id=2, descricao="Compras", valor=500.0, categoria=cat_despesa, data=datetime(2026, 8, 5))

    gerenciador.add_transacao(t1)
    gerenciador.add_transacao(t2)

    return gerenciador

def test_calculo_saldo_total(gerenciador_dados):
    saldo = gerenciador_dados.calc_saldo_total()
    assert saldo == 2500.0

def test_add_transacao_invalido():
    gerenciador = GerenciadorFin()
    cat = Categoria(id=1, nome="Lazer", tipo=TipoTransacao.DESPESA)

    with pytest.raises(ValueError):
        gerenciador.add_transacao(
            Transacao(id=1, descricao="Invalida", valor=-50.0, categoria=cat, data=datetime.now())
        )

def teste_alerta_orc_estourado(gerenciador_dados):
    gerenciador_dados.orcamentos.append(
        Orcamento(categoria_id=2, limite_mensal=400.0, mes_ano="08/2026")
    )

    alerta = gerenciador_dados.check_alerta_orc(categoria_id=2, mes=8, ano=2026)

    assert "PERIGO" in alerta or "ATENÇÃO" in alerta