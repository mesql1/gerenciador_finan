import csv
from typing import List
from datetime import datetime
from modelos import Transacao, Orcamento, TipoTransacao

class GerenciadorFin:
    def __init__(self):
        self.transacoes: List[Transacao] = [] 
        self.orcamentos: List[Orcamento] = []

    def add_transacao(self, transacao: Transacao):
        if transacao.valor <= 0:
            raise ValueError("O valor da transação deve ser maior que zero.")
        self.transacoes.append(transacao)

    def calc_saldo_total(self) -> float:
        receitas = sum(t.valor for t in self.transacoes if t.categoria.tipo == TipoTransacao.RECEITA)
        despesas = sum(t.valor for t in self.transacoes if t.categoria.tipo == TipoTransacao.DESPESA)
        return receitas - despesas

    def desp_mes(self, mes: int, ano: int) -> List[Transacao]:
        return [
            t for t in self.transacoes
            if t.categoria.tipo == TipoTransacao.DESPESA
            and t.data.month == mes
            and t.data.year == ano
        ]

    def check_alerta_orc(self, categoria_id: int, mes: int, ano: int) -> str:
        mes_ano_str = f"{mes:02d}/{ano}"

        #   Busca por orçamento nessa categoria e mes
        orcamento = next(
            (o for o in self.orcamentos if o.categoria_id == categoria_id and o.mes_ano == mes_ano_str),
            None
        )
        if not orcamento:
            return "Sem orçamento definido."

        total_gasto = sum(

            t.valor for t in self.desp_mes(mes, ano)
            if t.categoria.id == categoria_id
        )

        perc = (total_gasto / orcamento.limite_mensal) * 100

        if perc >= 100:
            return f"ATENÇÃO: ORÇAMENTO ESTOURADO! TOTAL GASTO: R${total_gasto:.2f} DE R${orcamento.limite_mensal:.2f} ({perc:.1f}%)"
        elif perc >= 80:
            return f"ATENÇÃO: VOCÊ ATINGIU O {perc:.1f}% DO LIMITE DEFINIDO (R${total_gasto:.2f} / R${orcamento.limite_mensal:.2f})"

        return f"DENTRO DO LIMITE ({perc:.1f}% usado)"

    #TODO: Finalizar essa função

    def buscar_por_descricao(self, termo: str) -> List[Transacao]:
        pass

    def export_csv(transacoes: list[Transacao], caminho_saida="extrato.csv"):
        if not transacoes:
            raise ValueError("Não há transações para exportar.")

        with open(caminho_saida, mode="w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")

            escritor.writerow(["ID", "Data", "Descrição", "Tipo", "Categoria", "Valor (R$)"])

            for t in transacoes:
                sinal = "+" if t.categoria.tipo == TipoTransacao.RECEITA else "-"
                valor_formatado = f"{sinal}{t.valor:.2f}".replace(".", ",")

                escritor.writerow([
                    t.id,
                    t.data.strftime("%d/%m/%Y"),
                    t.descricao,
                    t.categoria.tipo.value,
                    t.categoria.nome,
                    f"{t.valor:.2f}".replace(".", ",")
                ])