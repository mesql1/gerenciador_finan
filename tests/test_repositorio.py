import pytest
from datetime import datetime
from modelos import Transacao, Categoria, TipoTransacao, Orcamento
from repositorio import RepoSQLite

@pytest.fixture
def repo_memoria(tmp_path):
    #   Cria um banco SQLite temporário na memória RAM para os testes
    caminho_db_temp = tmp_path / "test_financas.db"
    repo = RepoSQLite(str(caminho_db_temp))
    return repo

def test_salvar_carregar_transacao(repo_memoria):
    #   Testa a inserção de uma nova transação e a leitura do SQLite
    categorias = repo_memoria.listar_categorias()
    cat_alimentacao = next(c for c in categorias if c.nome == "Alimentação")

    t = Transacao(
        id=0,
        descricao="Almoço Restaurante",
        valor=45.50,
        categoria=cat_alimentacao,
        data=datetime(2026, 8, 10, 12, 0)
    )

    id_gerado = repo_memoria.salvar_transacao(t)
    assert id_gerado > 0

    transacoes_salvas = repo_memoria.carregar_transacoes()
    assert len(transacoes_salvas) == 1
    assert transacoes_salvas[0].descricao == "Almoço Restaurante"
    assert transacoes_salvas[0].valor == 45.50

def test_remover_transacao(repo_memoria):
    #   Testa a exclusão física de um registro no SQLite
    categorias = repo_memoria.listar_categorias()
    cat = categorias[0]

    t = Transacao(id=0, descricao="Teste Delete", valor=100.0, categoria=cat, data=datetime.now())
    id_gerado = repo_memoria.salvar_transacao(t)

    removido = repo_memoria.remover_transacao(id_gerado)
    assert removido is True

    assert len(repo_memoria.carregar_transacoes()) == 0

def test_salvar_atualizar_orc(repo_memoria):
    #   Testa inserção e atualização (ON CONFLICT) de orçamento no SQLite
    categorias = repo_memoria.listar_categorias()
    cat_despesa = next(c for c in categorias if c.tipo == TipoTransacao.DESPESA)

    orc = Orcamento(categoria_id=cat_despesa.id, limite_mensal=300.0, mes_ano="08/2026")
    repo_memoria.salvar_atualizar_orc(orc)

    orc_atualizado = Orcamento(categoria_id=cat_despesa.id, limite_mensal=500.0, mes_ano="08/2026")
    repo_memoria.salvar_atualizar_orc(orc_atualizado)

    orcamentos = repo_memoria.carregar_orcamentos()
    assert len(orcamentos) == 1
    assert orcamentos[0].limite_mensal == 500.0