import csv
import customtkinter as ctk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from modelos import Transacao, TipoTransacao, Categoria, Orcamento
from servicos import GerenciadorFin
from repositorio import RepoSQLite

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        #   Configurações da janela
        self.title("Gerenciador de Finanças Pessoais")
        self.geometry("950x750")
        self.resizable(True, True)

        #   Camada de Dados e Serviços
        self.repositorio = RepoSQLite("financas.db")
        self.gerenciador = GerenciadorFin()

        self.categorias = self.repositorio.listar_categorias()
        self.gerenciador.transacoes = self.repositorio.carregar_transacoes()
        self.gerenciador.orcamentos = self.repositorio.carregar_orcamentos()

        self.canvas_graficos = None

        #   Componentes visuais
        self._criar_header()

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tab_transacoes = self.tabview.add("Transações e Extrato")
        self.tab_dashboard = self.tabview.add("Dashboard e Gráficos")
        self.tab_orcamentos = self.tabview.add("Orçamentos")
        self.tab_exportar = self.tabview.add("Exportar Dados")

        self._construir_aba_transacoes()
        self._construir_aba_dashboard()
        self._construir_aba_orcamentos()
        self._construir_aba_exportar()
        
        #   Atualização da tela inicial com dados
        self.atualizar_saldo()
        self.atualizar_tabela_ext()
        self.atualizar_lista_orc()
        self.atualizar_dashboard()

    #   ---
    #   LAYOUT
    #   ---

    def _criar_header(self):
        #   Cabeçalho com título e cartão do saldo atual
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=20, pady=(15, 10))

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_header,
            text="Finanças Pessoais",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.lbl_titulo.pack(side="left")

        #   Cartão de Saldo
        self.card_saldo = ctk.CTkFrame(self.frame_header, corner_radius=10)
        self.card_saldo.pack(side="right", padx=10)

        self.lbl_saldo_titulo = ctk.CTkLabel(self.card_saldo, text="Saldo Geral:", font=ctk.CTkFont(size=12))
        self.lbl_saldo_titulo.pack(padx=15, pady=(5, 0))

        self.lbl_saldo_valor = ctk.CTkLabel(
            self.card_saldo, 
            text="R$0,00",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_saldo_valor.pack(padx=15, pady=(0, 5))

    #   ---
    #   ABA 1: TRANSAÇÕES E EXTRATO
    #   ---

    def _construir_aba_transacoes(self):
        #   Form de cadastro
        self.frame_form = ctk.CTkFrame(self.tab_transacoes, corner_radius=10)
        self.frame_form.pack(fill="x", padx=10, pady=10)

        self.entry_descricao = ctk.CTkEntry(self.frame_form, placeholder_text="Descrição (ex: Mercado)")
        self.entry_descricao.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.entry_valor = ctk.CTkEntry(self.frame_form, placeholder_text="Valor (ex: 150.00)")
        self.entry_valor.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        nomes_cat = [f"{c.id} - {c.nome} ({c.tipo.value})" for c in self.categorias]
        self.combo_categoria = ctk.CTkOptionMenu(self.frame_form, values=nomes_cat)
        self.combo_categoria.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.btn_salvar = ctk.CTkButton(
            self.frame_form,
            text="Salvar",
            fg_color="#2ba84a",
            hover_color="#1e7a34",
            command=self.acao_cadastrar
        )
        self.btn_salvar.grid(row=0, column=3, padx=10, pady=10)
        self.frame_form.grid_columnconfigure((0, 1, 2), weight=1)

        #   Extrato com Scroll
        self.frame_ext = ctk.CTkFrame(self.tab_transacoes, corner_radius=10)
        self.frame_ext.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.lbl_ext_titulo = ctk.CTkLabel(
            self.frame_ext,
            text="Extrato de Lançamentos",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_ext_titulo.pack(anchor="w", padx=15, pady=10)

        self.scroll_transacoes = ctk.CTkScrollableFrame(self.frame_ext)
        self.scroll_transacoes.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    #   ---
    #   ABA 2: ORÇAMENTOS
    #   ---

    def _construir_aba_orcamentos(self):
        #   Form pra definir limite
        self.frame_orc_form = ctk.CTkFrame(self.tab_orcamentos, corner_radius=10)
        self.frame_orc_form.pack(fill="x", padx=10, pady=10)

        despesas_cat = [c for c in self.categorias if c.tipo == TipoTransacao.DESPESA]
        nome_despesas = [f"{c.id} - {c.nome}" for c in despesas_cat]

        self.combo_orc_cat = ctk.CTkOptionMenu(self.frame_orc_form, values=nome_despesas)
        self.combo_orc_cat.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.entry_orc_limite = ctk.CTkEntry(self.frame_orc_form, placeholder_text="Limite R$ (ex: 500)")
        self.entry_orc_limite.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.entry_orc_mes = ctk.CTkEntry(self.frame_orc_form, placeholder_text="Mês (1-12)")
        self.entry_orc_mes.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.entry_orc_ano = ctk.CTkEntry(self.frame_orc_form, placeholder_text="Ano (ex: 2026)")
        self.entry_orc_ano.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        self.btn_definir_orc = ctk.CTkButton(
            self.frame_orc_form,
            text="Definir Teto",
            command=self.acao_definir_orcamento
        )
        self.btn_definir_orc.grid(row=0, column=4, padx=10, pady=10)
        self.frame_orc_form.grid_columnconfigure((0, 1, 2, 3), weight=1)

        #   Scroll de cartões de orçamento
        self.scroll_orcamentos = ctk.CTkScrollableFrame(self.tab_orcamentos)
        self.scroll_orcamentos.pack(fill="both", expand=True, padx=10, pady=10)

    #   ---
    #   ABA 3: EXPORTAR PRA CSV
    #   ---

    def _construir_aba_exportar(self):
        self.frame_exp = ctk.CTkFrame(self.tab_exportar, corner_radius=10)
        self.frame_exp.pack(fill="both", expand=True, padx=20, pady=20)

        self.lbl_exp = ctk.CTkLabel(
            self.frame_exp,
            text="Exportação do Extrato Financeiro",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_exp.pack(pady=(40, 10))

        self.lbl_exp_desc = ctk.CTkLabel(
            self.frame_exp,
            text="Gere um arquivo 'extrato.csv' na raiz do projeto com todas as suas transações para abrir no Excel ou Google Planilhas.",
            wraplength=400
        )
        self.lbl_exp_desc.pack(pady=10)

        self.btn_exportar = ctk.CTkButton(
            self.frame_exp,
            text="Gerar Arquivo CSV",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.acao_exportar_csv
        )
        self.btn_exportar.pack(pady=20)

    def _criar_lista_ext(self):
        #   Área com a tabela de lançamentos cadastrados
        self.frame_ext = ctk.CTkFrame(self, corner_radius=10)
        self.frame_ext.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        self.lbl_ext_titulo = ctk.CTkLabel(
            self.frame_ext,
            text="Extrato Recente",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_ext_titulo.pack(anchor="w", padx=15, pady=15)

        #   Scrollable Frame para simular a tabela de transações
        self.scroll_transacoes = ctk.CTkScrollableFrame(self.frame_ext)
        self.scroll_transacoes.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    #   ---
    #   AÇÕES E REGRAS DE NEGÓCIO DA INTERFACE
    #   ---

    def _construir_aba_dashboard(self):
        self.frame_dash_container = ctk.CTkFrame(self.tab_dashboard, corner_radius=10)
        self.frame_dash_container.pack(fill="both", expand=True, padx=10, pady=10)

    #   Formata o texto exibido no gráfico de rosca
    def formatar_rotulo(pct, allvals):
        absolute = sum(allvals) * (pct / 100.0)

        if pct < 3:
            return ""
        return f"{pct:.1f}%\n(R${absolute:.2f})"

    def atualizar_dashboard(self):
        #   Limpas canvas anterior
        if self.canvas_graficos:
            self.canvas_graficos.get_tk_widget().destroy()

        if not self.gerenciador.transacoes:
            for widget in self.frame_dash_container.winfo_children():
                widget.destroy()
            ctk.CTkLabel(self.frame_dash_container, text="Cadastre transações para visualizar o Dashboard.").pack(expand=True)
            return

        for widget in self.frame_dash_container.winfo_children():
            widget.destroy()

        #   Config do estilo do gráfico
        modo_escuro = ctk.get_appearance_mode() == "Dark"
        cor_fundo = "#242424" if modo_escuro else "#F2F2F2"
        cor_texto = "white" if modo_escuro else "black"

        #   Figura: Lado a Lado
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4), facecolor=cor_fundo)
        fig.subplots_adjust(wspace=0.4)

        #   Figura: Rosca (Despesa por Categoria)
        gastos_por_cat = {}
        for t in self.gerenciador.transacoes:
            if t.categoria.tipo == TipoTransacao.DESPESA:
                nome_cat = t.categoria.nome
                gastos_por_cat[nome_cat] = gastos_por_cat.get(nome_cat, 0.0) + t.valor

        #   Formata o texto exibido no gráfico de rosca
        def formatar_rotulo(pct, allvals):
            absolute = sum(allvals) * (pct / 100.0)

            if pct < 3:
                return ""
            return f"{pct:.1f}%\n(R${absolute:.2f})"

        if gastos_por_cat:
            labels = list(gastos_por_cat.keys())
            valores = list(gastos_por_cat.values())
            cores = ["#e63946", "#f1c40f", "#3498db", "#9b59b6", "#e67e22", "#1abc9c"]

            ax1.set_facecolor(cor_fundo)
            wedges, texts, autotexts = ax1.pie(
                valores,
                labels=labels,
                autopct=lambda pct: formatar_rotulo(pct, valores),
                pctdistance=0.75,
                startangle=140,
                colors=cores,
                textprops=dict(color=cor_texto, fontsize=9),
                wedgeprops=dict(width=0.4, edgecolor=cor_fundo)
            )
            ax1.set_title("Despesas por Categoria", color=cor_texto, fontsize=12, fontweight="bold")

            #   Ajusta a cor dos números das porcentagens
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_weight("bold")

        else:
            ax1.set_facecolor(cor_fundo)
            ax1.text(0.5, 0.5, "Sem despesas", ha="center", va="center", color=cor_texto)

        total_receita = sum(t.valor for t in self.gerenciador.transacoes if t.categoria.tipo == TipoTransacao.RECEITA)
        total_despesa = sum(t.valor for t in self.gerenciador.transacoes if t.categoria.tipo == TipoTransacao.DESPESA)

        ax2.set_facecolor(cor_fundo)
        barras = ax2.bar(["Receitas", "Despesas"], [total_receita, total_despesa], color=["#2ba84a", "#e63946"], width=0.5)
        ax2.set_title("Receitas vs Despesas (R$)", color=cor_texto, fontsize=12, fontweight="bold")
        ax2.tick_params(colors=cor_texto)
        ax2.spines["bottom"].set_color(cor_texto)
        ax2.spines["left"].set_color(cor_texto)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        #   Adiciona valores no topo das barras
        for bar in barras:
            yval = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.02), f"R${yval:.2f}", ha="center", va="bottom", color=cor_texto, fontsize=9)

        #   Renderização da figura no Canvas do Tkinter
        self.canvas_graficos = FigureCanvasTkAgg(fig, master=self.frame_dash_container)
        self.canvas_graficos.draw()
        self.canvas_graficos.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)

    def atualizar_saldo(self):
        saldo = self.gerenciador.calc_saldo_total()
        cor = "#2ba84a" if saldo >= 0 else "#e63946"
        self.lbl_saldo_valor.configure(text=f"R${saldo:.2f}", text_color=cor)

    def atualizar_tabela_ext(self):
        #   Limpa e redesenha as linhas de transações no scroll frame

        #   Limpa widgets anteriores
        for widget in self.scroll_transacoes.winfo_children():
            widget.destroy()

        if not self.gerenciador.transacoes:
            lbl_vazio = ctk.CTkLabel(self.scroll_transacoes, text="Nenhuma transação cadastrada.")
            lbl_vazio.pack(pady=20)
            return

        for t in self.gerenciador.transacoes:
            frame_item = ctk.CTkFrame(self.scroll_transacoes, fg_color=("gray85", "gray20"))
            frame_item.pack(fill="x", pady=4, padx=5)

            sinal = "+" if t.categoria.tipo == TipoTransacao.RECEITA else "-"
            cor_valor = "#2ba84a" if t.categoria.tipo == TipoTransacao.RECEITA else "#e63946"

            info_text = f"#{t.id} | {t.data.strftime('%d/%m/%Y')} | {t.descricao} ({t.categoria.nome})"

            lbl_info = ctk.CTkLabel(frame_item, text=info_text, anchor="w")
            lbl_info.pack(side="left", padx=10, pady=8)

            btn_remover = ctk.CTkButton(
                frame_item,
                text="Remover",
                width=30,
                fg_color="#e63946",
                hover_color="#b82532",
                command=lambda id_del=t.id: self.acao_remover_transacao(id_del)
            )
            btn_remover.pack(side="right", padx=10)

            lbl_val = ctk.CTkLabel(
                frame_item,
                text=f"{sinal} R${t.valor:.2f}",
                text_color=cor_valor,
                font=ctk.CTkFont(weight="bold")
            )
            lbl_val.pack(side="right", padx=15)

    def acao_cadastrar(self):
        descricao = self.entry_descricao.get().strip()
        valor_raw = self.entry_valor.get().strip().replace(",", ".")

        #   Validações
        if not descricao or not valor_raw:
            self._mostrar_mensagem_status("Preencha descrição e valor!", erro=True)
            return

        try:
            valor = float(valor_raw)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self._mostrar_mensagem_status("Digite um valor numérico válido!", erro=True)
            return

        cat_str = self.combo_categoria.get()
        cat_id = int(cat_str.split(" - ")[0])
        cat_obj = next((c for c in self.categorias if c.id == cat_id), None)

        nova_transacao = Transacao(
            id=0,
            descricao=descricao,
            valor=valor,
            categoria=cat_obj,
            data=datetime.now()
        )

        try:
            #   Grava no SQLite e atualiza a memória
            id_gerado = self.repositorio.salvar_transacao(nova_transacao)
            nova_transacao.id = id_gerado
            self.gerenciador.add_transacao(nova_transacao)

            #   Limpa campos e atualiza a tela
            self.entry_descricao.delete(0, "end")
            self.entry_valor.delete(0, "end")

            self.atualizar_saldo()
            self.atualizar_tabela_ext()

            #   Checa alerta de orçamento se for despesa
            if cat_obj.tipo == TipoTransacao.DESPESA:
                alerta = self.gerenciador.check_alerta_orc(
                    categoria_id=cat_obj.id,
                    mes=datetime.now().month,
                    ano=datetime.now().year
                )
                if "PERIGO" in alerta or "ATENÇÃO" in alerta:
                    self._mostrar_mensagem_status(alerta, erro=True)
        except Exception as e:
            self._mostrar_mensagem_status(f"Erro ao salvar: {e}")

    def acao_definir_orcamento(self):
        try:
            cat_str = self.combo_orc_cat.get()
            cat_id = int(cat_str.split(" - ")[0])
            limite = float(self.entry_orc_limite.get().replace(",", "."))
            mes = int(self.entry_orc_mes.get())
            ano = int(self.entry_orc_ano.get())

            mes_ano_str = f"{mes:02d}/{ano}"
            novo_orc = Orcamento(categoria_id=cat_id, limite_mensal=limite, mes_ano=mes_ano_str)

            self.repositorio.salvar_atualizar_orc(novo_orc)
            self.gerenciador.orcamentos = self.repositorio.carregar_orcamentos()

            self.atualizar_lista_orcamentos()
            self._mostrar_mensagem_status("Orçamento gravado com sucesso!")

        except ValueError:
            self._mostrar_mensagem_status("Preencha limite, mês e ano valores numéricos válidos.", erro=True)

    def atualizar_lista_orc(self):
        for widget in self.scroll_orcamentos.winfo_children():
            widget.destroy()

        if not self.gerenciador.orcamentos:
            ctk.CTkLabel(self.scroll_orcamentos, text="Nenhum orçamento cadastrado.").pack(pady=20)
            return

        for orc in self.gerenciador.orcamentos:
            cat = next((c for c in self.categorias if c.id == orc.categoria_id), None)
            nome_cat = cat.nome if cat else "Desconhecida"

            #   Parse mês/ano do orçamento
            mes, ano = map(int, orc.mes_ano.split("/"))

            gastos = sum(
                t.valor for t in self.gerenciador.transacoes
                if t.categoria.id == orc.categoria_id
                and t.data.month == mes
                and t.data.year == ano
            )

            percentual = min(gastos / orc.limite_mensal, 1.0)

            if percentual >= 1.0:
                cor_progresso = "#e63946"
            elif percentual >= 0.8:
                cor_progresso = "#f1c40f"
            else:
                cor_progresso = "#2ba84a"

            frame_card = ctk.CTkFrame(self.scroll_orcamentos, corner_radius=10)
            frame_card.pack(fill="x", pady=6, padx=5)

            lbl_orc_info = ctk.CTkLabel(
                frame_card,
                text=f"{nome_cat} ({orc.mes_ano}) - Gasto: R${gastos:.2f} / R${orc.limite_mensal:.2f} ({percentual*100:.1f}%)",
                font=ctk.CTkFont(weight="bold")
            )
            lbl_orc_info.pack(anchor="w", padx=15, pady=(10, 5))

            prog_bar = ctk.CTkProgressBar(frame_card, progress_color=cor_progresso)
            prog_bar.set(percentual)
            prog_bar.pack(fill="x", padx=15, pady=(0, 10))
            
    def acao_remover_transacao(self, transacao_id: int):
        if self.repositorio.remover_transacao(transacao_id):
            self.gerenciador.transacoes = [t for t in self.gerenciador.transacoes if t.id != transacao_id]
            self.atualizar_saldo()
            self.atualizar_tabela_ext()
            self.atualizar_lista_orcamentos()
            self.atualizar_dashboard()
            self._mostrar_mensagem_status(f"Transação #{transacao_id} removida com sucesso!")

    def acao_exportar_csv(self):
        if not self.gerenciador.transacoes:
            self._mostrar_mensagem_status("Não há transações para exportar!", erro=True)
            return

        try:
            with open("extrato.csv", mode="w", newline="", encoding="utf-8-sig") as f:
                escritor = csv.writer(f, delimiter=";")

                for t in self.gerenciador.transacoes:
                    sinal = "-" if t.categoria.tipo == TipoTransacao.DESPESA else "+"
                    escritor.writerow([
                        t.id,
                        t.data.strftime("%d/%m/%Y"),
                        t.categoria.tipo.value,
                        t.categoria.nome,
                        t.descricao,
                        f"{sinal}{t.valor:.2f}".replace(".", ",")
                    ])
            self._mostrar_mensagem_status("Arquivo 'extrato.csv' exportado com sucesso!")
        except PermissionError:
            self._mostrar_mensagem_status("Feche o arquivo 'extrato.csv' no Excel antes de exportar novamente.")
        except Exception as e:
            self._mostrar_mensagem_status(f"Erro ao exportar: {e}")

    def _mostrar_mensagem_status(self, texto: str, erro: bool = False):
        #   Janele popup simples para exibir avisos/alertas de erro
        top = ctk.CTkToplevel(self)
        top.title("Aviso")
        top.geometry("380x150")
        top.attributes("-topmost", True)

        cor = "#e63946" if erro else "#2ba84a"
        lbl = ctk.CTkLabel(top, text=texto, wraplength=320, text_color=cor, font=ctk.CTkFont(size=13, weight="bold"))
        lbl.pack(expand=True, padx=20, pady=20)

if __name__ == "__main__":
    app = AppGUI()
    app.mainloop()