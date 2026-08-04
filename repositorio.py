import json
from datetime import datetime
from modelos import Transacao, Categoria, TipoTransacao

class RepoJSON:
    def __init__(self, caminho_arquivo="dados_financas.json"):
        self.caminho_arquivo = caminho_arquivo

    def salvar(self, transacoes: list[Transacao]):
        dados = []
        for t in transacoes:
            dados.append({
                "id": t.id,
                "descricao": t.descricao,
                "valor": t.valor,
                "data": t.data.strftime("%Y-%m-%d %H:%M:%S"),
                "categoria": {
                    "id": t.categoria.id,
                    "nome": t.categoria.nome,
                    "tipo": t.categoria.tipo.value
                },
            })

        with open(self.caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)

    def carregar(self) -> list[Transacao]:
        try:
            with open(self.caminho_arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)

            transacoes = []
            for item in dados:
                cat_data = item["categoria"]
                categoria = Categoria(
                    id=cat_data["id"],
                    nome=cat_data["nome"],
                    tipo=TipoTransacao(cat_data["tipo"])
                )
                t = Transacao(
                    id=item["id"],
                    descricao=item["descricao"],
                    valor=item["valor"],
                    categoria=categoria,
                    data=datetime.strptime(item["data"], "%Y-%m-%d %H:%M:%S") 
                )
                transacoes.append(t)
            return transacoes
        except FileNotFoundError:
            return []