import sqlite3
from datetime import datetime
from modelos import Transacao, Categoria, TipoTransacao, Orcamento

class RepoSQLite:
    def __init__(self, db_path="fincancas.db"):
        self.db_path = db_path
        self._criar_tabelas()
        self._inicializar_categorias_padrao()

    def _obter_conexao(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")#  Suporte para chaves estrangeiras
        return conn

    def _criar_tabelas(self):
        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('Receita', 'Despesa'))
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    data TEXT NOT NULL,
                    categoria_id INTEGER NOT NULL,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orcamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    categoria_id INTEGER NOT NULL,
                    limite_mensal REAL NOT NULL,
                    mes_ano TEXT NOT NULL,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                    UNIQUE(categoria_id, mes_ano)
                );
            """)

    #   Popula a tabela com categorias iniciais caso esteja vazia
    def _inicializar_categorias_padrao(self):
        categorias_iniciais = [
            ("Alimentação", "Despesa"),
            ("Transporte", "Despesa"),
            ("Moradia", "Despesa"),
            ("Lazer", "Despesa"),
            ("Salário", "Receita"),
            ("Investimentos/Extra", "Receita")
        ]

        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM categorias")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO categorias (nome, tipo) VALUES (?, ?)",
                    categorias_iniciais
                )

    # ---
    # CONSULTAS E OPERAÇÕES - CATEGORIAS E TRANSAÇÕES
    # ---

    def listar_categorias(self) -> list[Categoria]:
        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, tipo FROM categorias")
            linhas = cursor.fetchall()
            return [
                Categoria(id=row[0], nome=row[1], tipo=TipoTransacao(row[2]))
                for row in linhas
            ]
    def salvar_transacao(self, transacao: Transacao) -> int:
        data_str = transacao.data.strftime("%Y-%m-%d %H:%M:%S")
        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transacoes (descricao, valor, data, categoria_id) 
                VALUES (?, ?, ?, ?)
            """, (transacao.descricao, transacao.valor, data_str, transacao.categoria.id))
            return cursor.lastrowid

    #   Realiza um JOIN entre transacoes e categorias para carregar a lista completa
    def carregar_transacoes(self) -> list[Transacao]:
        sql = """
            SELECT t.id, t.descricao, t.valor, t.data, c.id, c.nome, c.tipo
            FROM transacoes t
            INNER JOIN categorias c ON t.categoria_id = c.id
            ORDER BY t.data DESC
        """

        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            linhas = cursor.fetchall()

            transacoes = []
            for row in linhas:
                cat = Categoria(id=row[4], nome=row[5], tipo=TipoTransacao(row[6]))
                t = Transacao(
                    id=row[0],
                    descricao=row[1],
                    valor=row[2],
                    categoria=cat,
                    data=datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
                )
                transacoes.append(t)
            return transacoes

    def remover_transacao(self, transacao_id: int) -> bool:
        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))
            return cursor.rowcount > 0

    # ---
    #   OPERAÇÕES - ORÇAMENTOS
    # ---

    def salvar_atualizar_orc(self, orcamento: Orcamento):
        sql = """
            INSERT INTO orcamentos (categoria_id, limite_mensal, mes_ano)
            VALUES (?, ?, ?)
            ON CONFLICT(categoria_id, mes_ano)
            DO UPDATE SET limite_mensal = excluded.limite_mensal
        """

        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (orcamento.categoria_id, orcamento.limite_mensal, orcamento.mes_ano))

    def carregar_orcamentos(self) -> list[Orcamento]:
        with self._obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT categoria_id, limite_mensal, mes_ano FROM orcamentos")
            return [
                Orcamento(categoria_id=r[0], limite_mensal=r[1], mes_ano=r[2])
                for r in cursor.fetchall()
            ]