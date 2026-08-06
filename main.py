import sys
from datetime import datetime
from modelos import Categoria, Transacao, TipoTransacao, Orcamento
from servicos import GerenciadorFin
from repositorio import RepoSQLite

def ler_float(mensagem: str) -> float:
    #   Lê valor decimal vindo do terminal garantindo validação de tipo e de valor positivo 
    while True:
        try:
            entrada = input(mensagem).replace(",", ".").strip()
            valor = float(entrada)
            if valor <= 0:
                print("O valor deve ser maior que zero. Tente novamente.")
                continue
            return valor
        except ValueError:
            print("Entrada inválida. Informe um valor válido (Ex: 10.50 ou 10,50)")

def ler_int(mensagem: str) -> int:
    #   Lê um numero inteiro vindo do terminal
    while True:
        try:
            return int(input(mensagem).strip())
        except ValueError:
            print("Por favor, informe um número inteiro válido.")

def ler_data(mensagem: str) -> datetime:
    #   Lê uma data no formato DD/MM/AAAA ou assume a data atual se deixado em branco
    while True:
        entrada = input(mensagem).strip()
        if not entrada:
            return datetime.now()
        try:
            return datetime.strptime(entrada, "%d/%m/%Y")        
        except ValueError:
            print("Formato inválido. Informe uma data no formato DD/MM/AAAA ou deixe em branco para usar a data atual.")

class AppCLI:
    def __init__(self):
        self.repositorio = RepoSQLite("financas.db")
        self.gerenciador = GerenciadorFin()

        #   Carrega os dados persistidos ao iniciar

        self.categorias = self.repositorio.listar_categorias()
        self.gerenciador.transacoes = self.repositorio.carregar_transacoes()
        self.gerenciador.orcamentos = self.repositorio.carregar_orcamentos()

    def exibir_menu(self):
        print("\n" + "-" * 30)
        print("GERENCIADOR DE FINANÇAS PESSOAIS")
        print("-" * 30 + "\n")
        print("[1] - Cadastrar Transação (Receita/Despesa)")
        print("[2] - Ver Saldo Geral")
        print("[3] - Listar Extrato por Mês/Ano")
        print("[4] - Definir/Checar Orçamento por Categoria")
        print("[5] - Exportar para .CSV")
        print("[0] - Salvar e Sair")
        print("-" * 30)

    def menu_cad_transacao(self):
        
        print("--- Nova Transação ---")
        descricao = input("Descrição (Ex: Aluguel, Mercado): ").strip()
        if not descricao:
            print("A descrição não pode estar vazia.")
            return

        valor = ler_float("Valor (R$): ")

        print("\nEscolha a Categoria: ")
        for cat in self.categorias:
            print(f"[{cat.id}] {cat.nome} ({cat.tipo.value})")

        cat_id = ler_int("ID da Categoria: ")
        cat_selecionada = None
        for cat in self.categorias:
            if cat.id == cat_id:
                cat_selecionada = cat
                break
        
        if not cat_selecionada:
            print("Categoria não selecionada.")
            return

        data_transacao = ler_data("Data (DD/MM/AAAA ou deixar em branco para hoje): ")

        nova_transacao = Transacao(
            id=0,
            descricao=descricao,
            valor=valor,
            categoria=cat_selecionada,
            data=data_transacao
        )

        try:
            id_gerado = self.repositorio.salvar_transacao(nova_transacao)
            nova_transacao.id = id_gerado

            self.gerenciador.add_transacao(nova_transacao)
            print(f"A transação '{descricao}' foi cadastrada com sucesso.")

            if cat_selecionada.tipo == TipoTransacao.DESPESA:
                alerta = self.gerenciador.check_alerta_orc(
                    categoria_id=cat_selecionada.id,
                    mes=data_transacao.month,
                    ano=data_transacao.year
                )
                print(f"\nStatus do Orçamento: {alerta}")

        except ValueError as e:
            print(f"Erro na operação: {e}")

        print(f"Transação #{id_gerado} salva no banco de dados com sucesso.")

    def menu_exibir_saldo(self):
        saldo = self.gerenciador.calc_saldo_total()
        status = "POSITIVO" if saldo >= 0 else "NEGATIVO/EM DÉBITO"
        print(f"\nSaldo Geral Atual: R${saldo:.2f} ({status})")

    def menu_listar_extrato(self):
        print("\n--- Extrato Mensal ---")
        mes = ler_int("Informe o mês (1-12): ")
        ano = ler_int("Informe o ano (Ex: 2026): ")

        transacoes_mes = [
            t for t in self.gerenciador.transacoes
            if t.data.month == mes and t.data.year == ano
        ]

        if not transacoes_mes:
            print(f"\nNenhuma transação foi registrada para {mes:02d}/{ano}.")
            return

        print(f"\n{'ID':<4} | {'Data':<10} | {'Tipo':<8} | {'Categoria':<15} | {'Descrição':<20} | {'Valor (R$)':<10}")
        print("-" * 75)
        for t in transacoes_mes:
            sinal = "+" if t.categoria.tipo == TipoTransacao.RECEITA else "-"
            print(
                f"{t.id:<4} | "
                f"{t.data.strftime('%d/%m/%Y'):<10} | "
                f"{t.categoria.tipo.value:<8} | "
                f"{t.categoria.nome:<15} | "
                f"{t.descricao:<20} | "
                f"{sinal} R${t.valor:<8.2f}"
                )

        opc_del = input("Deseja deletar alguma transação? (Y/N): ").upper()

        match opc_del:
            case "Y":
                termo = input("Informe a descrição para buscar: ").strip()

                if not termo:
                    print("Busca cancelada. Nenhum termo informado.")

                encontradas = self.gerenciador.buscar_por_descricao(termo)

                if not encontradas:
                    print(f"Nenhuma transação com o termo '{termo}' foi encontrada.")
                    return

                print(f"\nResultados encontrados para '{termo}'")
                print(f"\n{'ID':<4} | {'Data':<10} | {'Tipo':<8} | {'Categoria':<15} | {'Descrição':<20} | {'Valor (R$)':<10}")
                print("-" * 75)
                for t in encontradas:
                    print(f"{t.id:<4} | {t.data.strftime('%d/%m/%Y'):<10} | {t.descricao:<20} | R${t.valor:<8.2f}")

                id_del = ler_int("\nInforme o ID da transação que deseja deletar (Digite 0 para cancelar): ")
                if id_del == 0:
                    print("Operação cancelada.")
                    return

                #   Garante que o ID digitado pertence ao resultados filtrados
                if not any(t.id == id_del for t in encontradas):
                    print("O ID informado não pertence à lista exibida.")
                    return

                if self.repositorio.remover_transacao(id_del):
                    print(f"Transação #{id_del} removida do banco de dados com sucesso.")
                else:
                    print("Não foi possível remover a transação.")
            case "N":
                print("\nVoltando para o menu principal...\n")
            case _:
                print("\nOpção inválida")
                
    def menu_definir_orc(self):
        print("\n--- Definir Teto de Orçamento ---")
        despesas_cat = [c for c in self.categorias if c.tipo == TipoTransacao.DESPESA]

        if not despesas_cat:
            print("Nenhuma categoria de despesa cadastrada.")
            return

        for cat in despesas_cat:
            print(f"[{cat.id}] {cat.nome}")

        cat_id = ler_int("Escolha a Categoria de Despesa: ")

        if not any(c.id == cat.id for c in despesas_cat):
            print("Categoria inválida ou não é do tipo Despesa.")
            return

        limite = ler_float("Informe o Limite Máximo Mensal: ")
        mes = ler_int("Mês (1-12): ")
        ano = ler_int("Ano (Ex: 2026): ")

        mes_ano_str = f"{mes:02d}/{ano}"

        novo_orc = Orcamento(
            categoria_id=cat_id,
            limite_mensal=limite,
            mes_ano=mes_ano_str
        )

        try:
            self.repositorio.salvar_atualizar_orc(novo_orc)

            #   Atualiza se já existir ou cria um novo
            orcamento_existente = next(
                (o for o in self.gerenciador.orcamentos if o.categoria_id == cat_id and o.mes_ano == mes_ano_str),
                None
            )

            if orcamento_existente:
                orcamento_existente.limite_mensal = limite
            else:
                self.gerenciador.orcamentos.append(novo_orc)

            print(f"Orçamento de R${limite:.2f} definido com sucesso para {mes_ano_str}.")

        except Exception as e:
            print(f"ERR: problema ao salvar orçamento no banco de dados - > {e}")

    def menu_export_csv(self):
        try:
            self.gerenciador.export_csv(self.gerenciador.transacoes)
            print("\nExportação realizada com sucesso.")
        except ValueError as e:
            print(f"ERR: {e}")
        except PermissionError:
            print(f"ERR: Erro de permissão. Fecha o arquivo .csv no excel e tente novamente.")
        except Exception as e:
            print(f"ERR: Erro ao exportar o arquivo -> {e}")

    def executar(self):
        while True:
            self.exibir_menu()
            opcao = input("Informe o que deseja fazer: ")

            match opcao:
                case "1":
                    self.menu_cad_transacao()
                case "2":
                    self.menu_exibir_saldo()
                case "3":
                    self.menu_listar_extrato()
                case "4":
                    self.menu_definir_orc()
                case "5":
                    self.menu_export_csv()
                case "0":
                    print("Saindo...")
                    sys.exit(0)
                case _:
                    print("Opção Inválida.")

if __name__ == "__main__":
    app = AppCLI()
    app.executar()