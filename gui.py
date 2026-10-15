import csv
import sqlite3
import customtkinter as ctk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

from modelos import Transacao, TipoTransacao, Categoria, Orcamento, Conta
from servicos import GerenciadorFin
from repositorio import RepoSQLite

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Linguagem visual reta: remove o arredondamento padrão inclusive dos
# componentes internos, como barras de rolagem e menus suspensos.
def _remover_cantos_arredondados(configuracao):
    for chave, valor in configuracao.items():
        if isinstance(valor, dict):
            _remover_cantos_arredondados(valor)
        elif "corner_radius" in chave:
            configuracao[chave] = 0


_remover_cantos_arredondados(ctk.ThemeManager.theme)

COLOR_BG_DARK = "#09090B"
COLOR_SIDEBAR = "#070708"
COLOR_CARD_DARK = "#121214"
COLOR_CARD_ALT = "#18181B"
COLOR_BORDER_DARK = "#27272A"
COLOR_TEXT_MAIN = "#FAFAFA"
COLOR_TEXT_MUTED = "#8B8B95"

COLOR_INCOME = "#38D996"
COLOR_EXPENSE = "#FF646D"
COLOR_WARNING = "#F6B94A"
COLOR_PRIMARY = "#7C5CFC"
COLOR_PRIMARY_HOVER = "#6D4EE8"
FONT_FAMILY = "Inter UI"

# Define a mesma família para widgets com fonte explícita, componentes que
# usam a fonte padrão do CustomTkinter e textos gerados pelo Matplotlib.
ctk.ThemeManager.theme["CTkFont"]["family"] = FONT_FAMILY
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Inter UI", "Inter", "Segoe UI"]

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        #   Configurações da janela
        self.title("Gerenciador de Finanças Pessoais")
        self.geometry("1240x790")
        self.minsize(1050, 700)
        self.resizable(True, True)
        self.configure(fg_color=COLOR_BG_DARK)

        #   Camada de Dados e Serviços
        self.repositorio = RepoSQLite("financas_1.0.db")
        self.gerenciador = GerenciadorFin()

        self.categorias = self.repositorio.listar_categorias()
        self.contas = self.repositorio.listar_contas()
        self.gerenciador.transacoes = self.repositorio.carregar_transacoes()
        self.gerenciador.orcamentos = self.repositorio.carregar_orcamentos()

        self.aba_ativa = "dashboard"
        self.canvas_graficos = None
        self._timer_status = None
        self.contas_exp = set() #   Guarda os IDs das contas "abertas"

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=210)
        self.grid_columnconfigure(1, weight=1)

        self._construir_sidebar()
        self._construir_area_conteudo()

        self.navegar_para("dashboard")
        self.atualizar_saldo()
        
    #   ---
    #   LAYOUT
    #   ---

    #   TODO: Consertar problema da aba de exportação

    def _construir_sidebar(self):
        self.frame_sidebar = ctk.CTkFrame(
            self,
            width=210,
            corner_radius=0,
            fg_color=COLOR_SIDEBAR,
            border_width=0
        )
        self.frame_sidebar.grid(row=0, column=0, sticky="nsew")

        self.lbl_logo = ctk.CTkLabel(
            self.frame_sidebar,
            text="◈  NEXA",
            font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            anchor="w"
        )
        self.lbl_logo.pack(fill="x", padx=20, pady=(24, 2))

        self.lbl_logo_sub = ctk.CTkLabel(
            self.frame_sidebar,
            text="PERSONAL FINANCE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_logo_sub.pack(anchor="w", padx=43, pady=(0, 25))

        ctk.CTkLabel(
            self.frame_sidebar,
            text="MENU",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color="#5D5D66"
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self.botoes_nav = {}
        itens_menu = [
            ("dashboard", "▦   Visão geral"),
            ("transacoes", "⇄   Transações"),
            ("contas", "▣   Contas"),
            ("orcamentos", "◫   Orçamentos"),
            ("exportar", "⇧   Exportar")
        ]

        for idx, (chave, rotulo) in enumerate(itens_menu, start=2):
            btn = ctk.CTkButton(
                self.frame_sidebar,
                text=rotulo,
                height=40,
                anchor="w",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                fg_color="transparent",
                text_color=COLOR_TEXT_MUTED,
                hover_color=COLOR_CARD_ALT,
                corner_radius=0,
                command=lambda k=chave: self.navegar_para(k)
            )
            btn.pack(side="top", fill="x", padx=11, pady=2)
            self.botoes_nav[chave] = btn

        self.card_saldo_sidebar = ctk.CTkFrame(
            self.frame_sidebar,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.card_saldo_sidebar.pack(side="bottom", fill="x", padx=12, pady=14)

        self.lbl_saldo_titulo = ctk.CTkLabel(
            self.card_saldo_sidebar,
            text="SALDO DISPONÍVEL",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_saldo_titulo.pack(anchor="w", padx=12, pady=(10, 0))

        self.lbl_saldo_valor = ctk.CTkLabel(
            self.card_saldo_sidebar,
            text="R$0,00",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")
        )
        self.lbl_saldo_valor.pack(anchor="w", padx=12, pady=(0, 10))

    def _construir_area_conteudo(self):
        self.frame_main = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_main.grid(row=0, column=1, sticky="nsew", padx=22, pady=(16, 10))
        self.frame_main.grid_rowconfigure(1, weight=1)
        self.frame_main.grid_columnconfigure(0, weight=1)

        self.frame_topbar = ctk.CTkFrame(self.frame_main, fg_color="transparent", height=52)
        self.frame_topbar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.frame_topbar.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(self.frame_topbar, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        self.lbl_page_title = ctk.CTkLabel(
            title_box, text="Visão geral", anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=21, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_page_title.pack(anchor="w")
        self.lbl_page_subtitle = ctk.CTkLabel(
            title_box, text="Seu dinheiro, com clareza.", anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED
        )
        self.lbl_page_subtitle.pack(anchor="w", pady=(1, 0))

        self.entry_busca = ctk.CTkEntry(
            self.frame_topbar, width=220, height=34, corner_radius=0,
            fg_color=COLOR_CARD_DARK, border_color=COLOR_BORDER_DARK,
            placeholder_text="⌕  Buscar transação..."
        )
        self.entry_busca.grid(row=0, column=1, padx=(12, 8))
        self.entry_busca.bind("<KeyRelease>", lambda _event: self.atualizar_tabela_ext())
        ctk.CTkButton(
            self.frame_topbar, text="+  Nova transação", width=140, height=34,
            corner_radius=0, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=lambda: self.navegar_para("transacoes")
        ).grid(row=0, column=2)

        self.telas = {}

        self.telas["transacoes"] = self._criar_tela_transacoes()
        self.telas["dashboard"] = self._criar_tela_dashboard()
        self.telas["contas"] = self._criar_tela_contas()
        self.telas["orcamentos"] = self._criar_tela_orc()
        self.telas["exportar"] = self._criar_tela_exportar()

        self.lbl_status = ctk.CTkLabel(
            self.frame_main,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_status.grid(row=2, column=0, pady=(6, 0), sticky="ew")

    def navegar_para(self, nome_tela: str):
        self.aba_ativa = nome_tela

        titulos = {
            "dashboard": ("Visão geral", "Acompanhe a saúde das suas finanças."),
            "transacoes": ("Transações", "Registre e acompanhe suas movimentações."),
            "contas": ("Contas", "Organize seus saldos por carteira."),
            "orcamentos": ("Orçamentos", "Defina limites e controle seus gastos."),
            "exportar": ("Exportar dados", "Leve seu histórico para onde precisar.")
        }
        titulo, subtitulo = titulos[nome_tela]
        self.lbl_page_title.configure(text=titulo)
        self.lbl_page_subtitle.configure(text=subtitulo)
        self.entry_busca.grid() if nome_tela == "transacoes" else self.entry_busca.grid_remove()

        for chave, btn in self.botoes_nav.items():
            if chave == nome_tela:
                btn.configure(fg_color="#232027", text_color=COLOR_TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED)

        for chave, tela in self.telas.items():
            if chave == nome_tela:
                tela.grid(row=1, column=0, sticky="nsew")
            else:
                tela.grid_forget()

        if nome_tela == "transacoes":
            self.atualizar_tabela_ext()
        elif nome_tela == "dashboard":
            self.atualizar_dashboard()
        elif nome_tela == "contas":
            self.atualizar_lista_contas()
        elif nome_tela == "orcamentos":
            self.atualizar_lista_orc()

    def _criar_tela_transacoes(self):
        tela = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        tela.grid_rowconfigure(1, weight=1)
        tela.grid_columnconfigure(0, weight=1)

        self.frame_form = ctk.CTkFrame(
            tela,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_form.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame_form.grid_columnconfigure((0, 1), weight=2)
        self.frame_form.grid_columnconfigure(2, weight=1)

        self.entry_descricao = ctk.CTkEntry(self.frame_form, placeholder_text="Descrição da transação", height=36)
        self.entry_descricao.grid(row=0, column=0, columnspan=2, padx=10, pady=(12, 6), sticky="ew")

        self.entry_valor = ctk.CTkEntry(self.frame_form, placeholder_text="Valor (R$)", height=36)
        self.entry_valor.grid(row=0, column=2, padx=10, pady=(12, 6), sticky="ew")

        nomes_cat = [f"{c.id} - {c.nome} ({c.tipo.value})" for c in self.categorias]
        self.combo_categoria = ctk.CTkOptionMenu(self.frame_form, values=nomes_cat, height=36)
        self.combo_categoria.grid(row=1, column=0, padx=10, pady=(6, 12), sticky="ew")

        nomes_contas = [f"{c.id} - {c.nome}" for c in self.contas]
        self.combo_contas = ctk.CTkOptionMenu(self.frame_form, values=nomes_contas, height=36)
        self.combo_contas.grid(row=1, column=1, padx=10, pady=(6, 12), sticky="ew")

        self.btn_salvar = ctk.CTkButton(
            self.frame_form,
            text="Cadastrar",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            fg_color=COLOR_PRIMARY,
            hover_color="#1D4ED8",
            command=self.acao_cadastrar
        )
        self.btn_salvar.grid(row=1, column=2, padx=10, pady=(6, 12), sticky="ew")

        self.frame_ext = ctk.CTkFrame(
            tela,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_ext.grid(row=1, column=0, sticky="nsew")

        lbl_extrato_titulo = ctk.CTkLabel(
            self.frame_ext,
            text="HISTÓRICO DE TRANSAÇÕES",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_extrato_titulo.pack(anchor="w", padx=16, pady=(12, 6))

        self.scroll_transacoes = ctk.CTkScrollableFrame(self.frame_ext, fg_color="transparent")
        self.scroll_transacoes.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        return tela

    def atualizar_tabela_extrato(self):
        for widget in self.scroll_transacoes.winfo_children():
            widget.destroy()

        if not self.gerenciador.transacoes:
            ctk.CTkLabel(self.scroll_transacoes, text="Nenhuma transação registrada.", text_color=COLOR_TEXT_MUTED).pack(pady=20)
            return

        for t in self.gerenciador.transacoes:
            frame_bloco = ctk.CTkFrame(
                self.scroll_transacoes,
                corner_radius=0,
                border_width=1,
                border_color=COLOR_BORDER_DARK,
                fg_color=COLOR_BG_DARK
            )
            frame_bloco.pack(fill="x", pady=4, padx=4)

            sinal = "+" if t.categoria.tipo == TipoTransacao.RECEITA else "-"
            cor_valor = COLOR_INCOME if t.categoria.tipo == TipoTransacao.RECEITA else COLOR_EXPENSE

            frame_info = ctk.CTkLabel(frame_bloco, fg_color="transparent")
            frame_info.pack(side="left", padx=12, pady=10)

            lbl_descricao = ctk.CTkLabel(frame_info, text=f"#{t.id} - {t.descricao}", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT_MAIN, anchor="w")
            lbl_descricao.pack(anchor="w")

            detalhes_texto = f"Conta: {t.conta.nome} - {t.categoria.nome} - {t.data.strftime('%d/%m/%Y')}"
            lbl_detalhes = ctk.CTkLabel(frame_info, text=detalhes_texto, font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED, anchor="w")
            lbl_detalhes.pack(anchor="w", pady=(2, 0))

            btn_remover = ctk.CTkButton(
                frame_bloco,
                text="Remover",
                width=65,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color="#3F3F46",
                hover_color="#991B1B",
                command=lambda id_del=t.id: self.acao_remover_transacao(id_del)
            )
            btn_remover.pack(side="right", padx=12, pady=10)

            lbl_valor = ctk.CTkLabel(frame_bloco, text=f"{sinal} R${t.valor:.2f}", text_color=cor_valor, font=ctk.CTkFont(size=14, weight="bold"))
            lbl_valor.pack(side="right", padx=12, pady=10)

    def _criar_tela_dashboard(self):
        tela = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        tela.grid_rowconfigure(0, weight=1)
        tela.grid_columnconfigure(0, weight=1)

        self.frame_dash_container = ctk.CTkFrame(
            tela,
            corner_radius=0,
            fg_color="transparent"
        )
        self.frame_dash_container.grid(row=0, column=0, sticky="nsew")

        return tela

    def _criar_tela_contas(self):
        tela = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        tela.grid_rowconfigure(1, weight=1)
        tela.grid_columnconfigure(0, weight=1)

        self.frame_conta_form = ctk.CTkFrame(
            tela,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_conta_form.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.entry_conta_nome = ctk.CTkEntry(self.frame_conta_form, placeholder_text="Nome da Nova Conta (ex: Nubank, Inter)", height=36)
        self.entry_conta_nome.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self.btn_salvar_conta = ctk.CTkButton(
            self.frame_conta_form,
            text="Criar Conta",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            fg_color=COLOR_PRIMARY,
            hover_color="#1D4ED8",
            command=self.acao_cadastrar_conta
        )
        self.btn_salvar_conta.grid(row=0, column=1, padx=12, pady=12)
        self.frame_conta_form.grid_columnconfigure(0, weight=1)

        self.scroll_contas = ctk.CTkScrollableFrame(tela, fg_color="transparent")
        self.scroll_contas.grid(row=1, column=0, sticky="nsew")

        return tela

    def _criar_tela_orc(self):
        tela = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        tela.grid_rowconfigure(1, weight=1)
        tela.grid_columnconfigure(0, weight=1)

        self.frame_orc_form = ctk.CTkFrame(
            tela,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_orc_form.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        despesas_cat = [c for c in self.categorias if c.tipo == TipoTransacao.DESPESA]
        nomes_despesas = [f"{c.id} - {c.nome}" for c in despesas_cat]

        self.combo_orc_cat = ctk.CTkOptionMenu(self.frame_orc_form, values=nomes_despesas, height=36)
        self.combo_orc_cat.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.entry_orc_limite = ctk.CTkEntry(self.frame_orc_form, placeholder_text="Limite (R$)", height=36)
        self.entry_orc_limite.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.entry_orc_mes = ctk.CTkEntry(self.frame_orc_form, placeholder_text="Mês (1-12)", height=36)
        self.entry_orc_mes.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.entry_orc_ano = ctk.CTkEntry(self.frame_orc_form, placeholder_text="Ano (ex: 2026)", height=36)
        self.entry_orc_ano.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        self.btn_definir_orc = ctk.CTkButton(
            self.frame_orc_form,
            text="Definir Limite",
            height=36,
            fg_color=COLOR_PRIMARY,
            hover_color="#1D4ED8",
            command=self.acao_definir_orcamento
        )
        self.btn_definir_orc.grid(row=0, column=4, padx=10, pady=10)
        self.frame_orc_form.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.scroll_orcamentos = ctk.CTkScrollableFrame(tela, fg_color="transparent")
        self.scroll_orcamentos.grid(row=1, column=0, sticky="nsew")

        return tela

    def _criar_tela_exportar(self):
        tela = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        tela.grid_rowconfigure(0, weight=1)
        tela.grid_columnconfigure(0, weight=1)

        frame_exp = ctk.CTkFrame(
            tela, 
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        frame_exp.grid(row=0, column=0, sticky="nsew")

        lbl_exp = ctk.CTkLabel(frame_exp, text="EXPORTAÇÃO DE DADOS", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_exp.pack(pady=(40, 12))

        frame_info_box = ctk.CTkFrame(frame_exp, fg_color=COLOR_BG_DARK, corner_radius=0)
        frame_info_box.pack(padx=30, pady=10, fill="x")

        lbl_exp_desc = ctk.CTkLabel(
            frame_info_box, 
            text="Gera o arquivo 'extrato.csv' unificado com todas as contas cadastradas, pronto para abertura no Excel ou Google Planilhas.",
            wraplength=450,
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_exp_desc.pack(padx=16, pady=16)

        btn_exportar = ctk.CTkButton(
            frame_exp, 
            text="Gerar Relatório CSV", 
            font=ctk.CTkFont(weight="bold"),
            height=40,
            fg_color=COLOR_PRIMARY,
            hover_color="#1D4ED8",
            command=self.acao_exportar_csv
        )
        btn_exportar.pack(pady=(16, 40))

        return tela

    def alternar_expansao_conta(self, conta_id: int):
        if conta_id in self.contas_exp:
            self.contas_exp.remove(conta_id)
        else:
            self.contas_exp.add(conta_id)
        self.atualizar_lista_contas()

    def _criar_header(self):
        #   Cabeçalho com título e cartão do saldo atual
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=24, pady=(20, 10))

        frame_title_box = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        frame_title_box.pack(side="left")

        self.lbl_titulo = ctk.CTkLabel(
            frame_title_box,
            text="Finanças Pessoais",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_titulo.pack(anchor="w")

        self.lbl_subtitulo = ctk.CTkLabel(
            frame_title_box,
            text="Visão geral e controle de fluxo de caixa",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_subtitulo.pack(anchor="w")

        #   Cartão de Saldo
        self.card_saldo = ctk.CTkFrame(
            self.frame_header,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.card_saldo.pack(side="right")

        self.lbl_saldo_titulo = ctk.CTkLabel(
            self.card_saldo,
            text="SALDO ATUAL",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_saldo_titulo.pack(padx=16, pady=(8, 0), anchor="e")

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
        self.frame_form = ctk.CTkFrame(
            self.tab_transacoes,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_form.pack(fill="x", padx=10, pady=10)

        self.frame_form.grid_columnconfigure((0, 1), weight=2)
        self.frame_form.grid_columnconfigure(2, weight=1)

        self.entry_descricao = ctk.CTkEntry(
            self.frame_form,
            placeholder_text="Descrição da transação",
            height=36
        )
        self.entry_descricao.grid(row=0, column=0, columnspan=2, padx=10, pady=(12, 6), sticky="ew")

        self.entry_valor = ctk.CTkEntry(
            self.frame_form,
            placeholder_text="Valor (ex: 150.00)",
            height=36
        )
        self.entry_valor.grid(row=0, column=2, padx=10, pady=(12, 6), sticky="ew")

        nomes_cat = [f"{c.id} - {c.nome} ({c.tipo.value})" for c in self.categorias]
        self.combo_categoria = ctk.CTkOptionMenu(
            self.frame_form,
            values=nomes_cat,
            height=36
        )
        self.combo_categoria.grid(row=1, column=0, padx=10, pady=(6, 12), sticky="ew")

        nomes_contas = [f"{c.id} - {c.nome}" for c in self.contas]
        self.combo_contas = ctk.CTkOptionMenu(self.frame_form, values=nomes_contas, height=36)
        self.combo_contas.grid(row=1, column=1, padx=10, pady=(6, 12), sticky="ew")

        self.btn_salvar = ctk.CTkButton(
            self.frame_form,
            text="Salvar",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self.acao_cadastrar
        )
        self.btn_salvar.grid(row=1, column=2, padx=10, pady=(6, 12), sticky="ew")
        self.frame_form.grid_columnconfigure((0, 1, 2), weight=1)

        #   Extrato com Scroll
        self.frame_ext = ctk.CTkFrame(
            self.tab_transacoes,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_ext.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.lbl_ext_titulo = ctk.CTkLabel(
            self.frame_ext,
            text="HISTÓRICO DE LANÇAMENTOS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_ext_titulo.pack(anchor="w", padx=16, pady=(12, 6))

        self.scroll_transacoes = ctk.CTkScrollableFrame(self.frame_ext, fg_color="transparent")
        self.scroll_transacoes.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    #   ---
    #   ABA 2: ORÇAMENTOS
    #   ---

    def _construir_aba_orcamentos(self):
        #   Form pra definir limite
        self.frame_orc_form = ctk.CTkFrame(
            self.tab_orcamentos,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_orc_form.pack(fill="x", padx=10, pady=10)

        despesas_cat = [c for c in self.categorias if c.tipo == TipoTransacao.DESPESA]
        nome_despesas = [f"{c.id} - {c.nome}" for c in despesas_cat]

        self.combo_orc_cat = ctk.CTkOptionMenu(self.frame_orc_form, values=nome_despesas, height=36)
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
            height=36,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self.acao_definir_orcamento
        )
        self.btn_definir_orc.grid(row=0, column=4, padx=10, pady=10)
        self.frame_orc_form.grid_columnconfigure((0, 1, 2, 3), weight=1)

        #   Scroll de cartões de orçamento
        self.scroll_orcamentos = ctk.CTkScrollableFrame(self.tab_orcamentos, fg_color="transparent")
        self.scroll_orcamentos.pack(fill="both", expand=True, padx=10, pady=10)

    #   ---
    #   ABA 3: EXPORTAR PRA CSV
    #   ---

    def _construir_aba_exportar(self):
        self.frame_exp = ctk.CTkFrame(
            self.tab_exportar,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_exp.pack(fill="both", expand=True, padx=20, pady=20)

        self.lbl_exp = ctk.CTkLabel(
            self.frame_exp,
            text="Exportação do Extrato Financeiro",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_exp.pack(pady=(30, 10))

        frame_info_box = ctk.CTkFrame(self.frame_exp, fg_color=COLOR_BG_DARK, corner_radius=0)
        frame_info_box.pack(padx=30, pady=10, fill="x")

        self.lbl_exp_desc = ctk.CTkLabel(
            frame_info_box,
            text="Gere um arquivo 'extrato.csv' na raiz do projeto com todas as suas transações para abrir no Excel ou Google Planilhas.",
            wraplength=420,
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_exp_desc.pack(padx=16, pady=16)

        self.btn_exportar = ctk.CTkButton(
            self.frame_exp,
            text="Gerar Arquivo CSV",
            font=ctk.CTkFont(weight="bold"),
            height=40,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self.acao_exportar_csv
        )
        self.btn_exportar.pack(pady=(10, 30))

    def _criar_lista_ext(self):
        #   Área com a tabela de lançamentos cadastrados
        self.frame_ext = ctk.CTkFrame(self, corner_radius=0)
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

    def _construir_aba_contas(self):
        self.frame_conta_form = ctk.CTkFrame(
            self.tab_contas,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_conta_form.pack(fill="x", padx=10, pady=10)

        self.entry_conta_nome = ctk.CTkEntry(
            self.frame_conta_form,
            placeholder_text="Nome da Nova Conta (ex: Nubank, Inter, etc...)",
            height=36
        )
        self.entry_conta_nome.grid(row=0, column=0, padx=12, pady=12, sticky="ew")

        self.btn_salvar_conta = ctk.CTkButton(
            self.frame_conta_form,
            text="Criar Conta",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self.acao_cadastrar_conta
        )
        self.btn_salvar_conta.grid(row=0, column=1, padx=12, pady=12)
        self.frame_conta_form.grid_columnconfigure(0, weight=1)

        self.scroll_contas = ctk.CTkScrollableFrame(self.tab_contas, fg_color="transparent")
        self.scroll_contas.pack(fill="both", expand=True, padx=10, pady=10)

    def alt_expansao_conta(self, conta_id: int):
        if conta_id in self.contas_exp:
            self.contas_exp.remove(conta_id)
        else:
            self.contas_exp.add(conta_id)
        self.atualizar_lista_contas()

    def atualizar_lista_contas(self):
        for widget in self.scroll_contas.winfo_children():
            widget.destroy()

        if not self.contas:
            ctk.CTkLabel(
                self.scroll_contas,
                text="Nenhuma conta cadastrada.",
                text_color=COLOR_TEXT_MUTED
            ).pack(pady=20)
            return

        for conta in self.contas:
            exp = conta.id in self.contas_exp
            seta = "🢓" if exp else "🢒"

            saldo_conta = self.gerenciador.calc_saldo_conta(conta.id)
            cor_saldo = COLOR_INCOME if saldo_conta >= 0 else COLOR_EXPENSE

            frame_card = ctk.CTkFrame(
                self.scroll_contas,
                corner_radius=0,
                border_width=1,
                border_color=COLOR_BORDER_DARK,
                fg_color=COLOR_CARD_DARK
            )
            frame_card.pack(fill="x", pady=6, padx=4)

            frame_header = ctk.CTkFrame(frame_card, fg_color="transparent")
            frame_header.pack(side="top", fill="x", padx=16, pady=10)

            frame_header.grid_columnconfigure(0, weight=1)
            frame_header.grid_columnconfigure(1, weight=0)
            frame_header.grid_columnconfigure(2, weight=0)

            btn_toggle = ctk.CTkButton(
                frame_header,
                text=seta,
                width=34,
                height=34,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#3F3F46",
                hover_color="#52525B",
                command=lambda c_id=conta.id: self.alt_expansao_conta(c_id)
            )
            btn_toggle.grid(row=0, column=2, rowspan=2, sticky="e")

            lbl_nome = ctk.CTkLabel(
                frame_header,
                text=f"{conta.nome}",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=COLOR_TEXT_MAIN
            )
            lbl_nome.grid(row=0, column=0, rowspan=2, sticky="w")

            lbl_saldo = ctk.CTkLabel(
                frame_header,
                text=f"R${saldo_conta:.2f}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=cor_saldo
            )
            lbl_saldo.grid(row=0, column=1, padx=(0, 14), pady=(0, 2))

            btn_del_conta = ctk.CTkButton(
                frame_header,
                text="Remover",
                width=72,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color="#3F3F46",
                hover_color="#991B1B",
                command=lambda c_id=conta.id, c_nome=conta.nome: self.acao_remover_conta(c_id, c_nome)
            )
            btn_del_conta.grid(row=1, column=1, padx=(0, 14))

            if exp:
                transacoes_conta = [t for t in self.gerenciador.transacoes if t.conta.id == conta.id]

                frame_drawer = ctk.CTkFrame(
                    frame_card,
                    corner_radius=0,
                    fg_color=COLOR_BG_DARK,
                    border_width=1,
                    border_color=COLOR_BORDER_DARK
                )
                frame_drawer.pack(side="top", fill="x", padx=16, pady=(0, 12))

                if not transacoes_conta:
                    ctk.CTkLabel(
                        frame_drawer,
                        text="Nenhuma transação registrada nesta conta.",
                        font=ctk.CTkFont(size=11),
                        text_color=COLOR_TEXT_MUTED
                    ).pack(pady=10)
                else:
                    for t in transacoes_conta:
                        row_t = ctk.CTkFrame(frame_drawer, fg_color="transparent")
                        row_t.pack(fill="x", padx=12, pady=4)

                        sinal = "+" if t.categoria.tipo == TipoTransacao.RECEITA else "-"
                        cor_v = COLOR_INCOME if t.categoria.tipo == TipoTransacao.RECEITA else COLOR_EXPENSE

                        lbl_item = ctk.CTkLabel(
                            row_t,
                            text=f"#{t.id} - {t.descricao} ({t.categoria.nome}) | {t.data.strftime('%d/%m/%Y')}",
                            font=ctk.CTkFont(size=12),
                            text_color=COLOR_TEXT_MAIN
                        )
                        lbl_item.pack(side="left")

                        lbl_item_valor = ctk.CTkLabel(
                            row_t,
                            text=f"{sinal} R${t.valor:.2f}",
                            font=ctk.CTkFont(size=12, weight="bold"),
                            text_color=cor_v
                        )
                        lbl_item_valor.pack(side="right")

    def acao_cadastrar_conta(self):
        nome = self.entry_conta_nome.get().strip()
        if not nome:
            self._mostrar_mensagem_status("Digite o nome da conta.", erro=True)
            return

        if any(c.nome.lower() == nome.lower() for c in self.contas):
            self._mostrar_mensagem_status(f"A conta '{nome}' já está cadastrada.", erro=True)
            return

        nova_conta = Conta(id=0, nome=nome, saldo_inicial=0.0)
        try:
            id_gerado = self.repositorio.salvar_conta(nova_conta)
            nova_conta.id = id_gerado
            self.contas.append(nova_conta)

            nomes_conta = [f"{c.id} - {c.nome}" for c in self.contas]
            self.combo_contas.configure(values=nomes_conta)

            self.entry_conta_nome.delete(0, "end")
            
            self.atualizar_lista_contas()

            self.scroll_contas.update()
            self.update_idletasks()

            self._mostrar_mensagem_status(f"Conta '{nome}' criada com sucesso.")

        except sqlite3.IntegrityError:
            self._mostrar_mensagem_status(f"A conta '{nome}' já existe no banco de dados.", erro=True)
        except Exception as e:
            self._mostrar_mensagem_status(f"Erro inesperado: {e}", erro=True)

    def _construir_aba_dashboard(self):
        self.frame_dash_container = ctk.CTkFrame(
            self.tab_dashboard,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_dash_container.pack(fill="both", expand=True, padx=10, pady=10)

    #   Formata o texto exibido no gráfico de rosca
    def formatar_rotulo(pct, allvals):
        absolute = sum(allvals) * (pct / 100.0)

        if pct < 3:
            return ""
        return f"{pct:.1f}%\n(R${absolute:.2f})"

    def atualizar_dashboard(self):
        for widget in self.frame_dash_container.winfo_children():
            widget.destroy()

        container = self.frame_dash_container
        for column in range(4):
            container.grid_columnconfigure(column, weight=1, uniform="metricas")
        container.grid_rowconfigure(1, weight=1)
        container.grid_rowconfigure(2, weight=1)

        transacoes = self.gerenciador.transacoes
        receitas = sum(t.valor for t in transacoes if t.categoria.tipo == TipoTransacao.RECEITA)
        despesas = sum(t.valor for t in transacoes if t.categoria.tipo == TipoTransacao.DESPESA)
        saldo = receitas - despesas
        economia = (saldo / receitas * 100) if receitas else 0

        metricas = [
            ("SALDO TOTAL", self._formatar_moeda(saldo), "◈", COLOR_PRIMARY),
            ("RECEITAS", self._formatar_moeda(receitas), "↗", COLOR_INCOME),
            ("DESPESAS", self._formatar_moeda(despesas), "↘", COLOR_EXPENSE),
            ("TAXA DE ECONOMIA", f"{economia:.1f}%", "◎", COLOR_WARNING),
        ]
        for coluna, (titulo, valor, icone, cor) in enumerate(metricas):
            card = ctk.CTkFrame(
                container, height=92, corner_radius=0, fg_color=COLOR_CARD_DARK,
                border_width=1, border_color=COLOR_BORDER_DARK
            )
            card.grid(row=0, column=coluna, sticky="nsew", padx=(0 if coluna == 0 else 5, 0 if coluna == 3 else 5), pady=(0, 10))
            card.grid_propagate(False)
            ctk.CTkLabel(
                card, text=icone, width=28, height=28, corner_radius=0,
                fg_color=COLOR_CARD_ALT, text_color=cor,
                font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")
            ).place(x=14, y=14)
            ctk.CTkLabel(
                card, text=titulo, text_color=COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold")
            ).place(x=52, y=14)
            ctk.CTkLabel(
                card, text=valor, text_color=COLOR_TEXT_MAIN,
                font=ctk.CTkFont(family=FONT_FAMILY, size=19, weight="bold")
            ).place(x=14, y=49)

        chart_card = ctk.CTkFrame(
            container, corner_radius=0, fg_color=COLOR_CARD_DARK,
            border_width=1, border_color=COLOR_BORDER_DARK
        )
        chart_card.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(0, 5), pady=(0, 10))
        ctk.CTkLabel(
            chart_card, text="RECEITAS E DESPESAS", anchor="w", text_color=COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        ).pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(
            chart_card, text="Comparativo mensal dos valores movimentados", anchor="w",
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=9)
        ).pack(fill="x", padx=16, pady=(1, 0))

        movimentos_por_mes = {}
        for transacao in transacoes:
            periodo = (transacao.data.year, transacao.data.month)
            if periodo not in movimentos_por_mes:
                movimentos_por_mes[periodo] = {"receitas": 0.0, "despesas": 0.0}
            campo = "receitas" if transacao.categoria.tipo == TipoTransacao.RECEITA else "despesas"
            movimentos_por_mes[periodo][campo] += transacao.valor

        periodos = sorted(movimentos_por_mes)[-6:]
        if not periodos:
            agora = datetime.now()
            periodos = [(agora.year, agora.month)]
            movimentos_por_mes[periodos[0]] = {"receitas": 0.0, "despesas": 0.0}

        nomes_meses = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
        rotulos = [f"{nomes_meses[mes - 1]}/{str(ano)[-2:]}" for ano, mes in periodos]
        valores_receitas = [movimentos_por_mes[periodo]["receitas"] for periodo in periodos]
        valores_despesas = [movimentos_por_mes[periodo]["despesas"] for periodo in periodos]

        fig, ax = plt.subplots(figsize=(7.2, 2.6), facecolor=COLOR_CARD_DARK)
        ax.set_facecolor(COLOR_CARD_DARK)
        posicoes = list(range(len(periodos)))
        largura = 0.32
        barras_receitas = ax.bar(
            [x - largura / 2 for x in posicoes], valores_receitas,
            width=largura, color=COLOR_INCOME, label="Receitas"
        )
        barras_despesas = ax.bar(
            [x + largura / 2 for x in posicoes], valores_despesas,
            width=largura, color=COLOR_EXPENSE, label="Despesas"
        )
        ax.set_xticks(posicoes, rotulos)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _pos: self._formatar_moeda(valor)))
        ax.tick_params(axis="both", colors=COLOR_TEXT_MUTED, labelsize=8, length=0)
        ax.grid(axis="y", color=COLOR_BORDER_DARK, linewidth=0.7, alpha=0.75)
        ax.set_axisbelow(True)
        maior_valor = max(valores_receitas + valores_despesas + [0])
        ax.set_ylim(0, maior_valor * 1.25 if maior_valor else 1)
        for spine in ax.spines.values():
            spine.set_visible(False)
        legend = ax.legend(frameon=False, loc="upper left", fontsize=8, ncol=2)
        for texto in legend.get_texts():
            texto.set_color(COLOR_TEXT_MUTED)
        deslocamento = maior_valor * 0.025 if maior_valor else 0.02
        for barras in (barras_receitas, barras_despesas):
            for barra in barras:
                altura = barra.get_height()
                ax.text(
                    barra.get_x() + barra.get_width() / 2,
                    altura + deslocamento,
                    self._formatar_moeda(altura),
                    ha="center", va="bottom", color=COLOR_TEXT_MAIN,
                    fontsize=7, fontweight="bold"
                )
        fig.tight_layout(pad=1.2)
        self.canvas_graficos = FigureCanvasTkAgg(fig, master=chart_card)
        self.canvas_graficos.draw_idle()
        widget_grafico = self.canvas_graficos.get_tk_widget()
        widget_grafico.configure(bg=COLOR_CARD_DARK, highlightthickness=0)
        widget_grafico.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        plt.close(fig)

        health_card = ctk.CTkFrame(
            container, corner_radius=0, fg_color=COLOR_CARD_DARK,
            border_width=1, border_color=COLOR_BORDER_DARK
        )
        health_card.grid(row=1, column=3, sticky="nsew", padx=(5, 0), pady=(0, 10))
        ctk.CTkLabel(
            health_card, text="SAÚDE FINANCEIRA", anchor="w", text_color=COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        ).pack(fill="x", padx=16, pady=(12, 4))
        score = max(0, min(100, 50 + int(economia / 2))) if receitas else 0
        ctk.CTkLabel(
            health_card, text=f"{score}%", text_color=COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_FAMILY, size=32, weight="bold")
        ).pack(pady=(8, 0))
        ctk.CTkLabel(
            health_card, text="score calculado", text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9)
        ).pack()
        barra = ctk.CTkProgressBar(health_card, height=9, corner_radius=0, progress_color=COLOR_INCOME)
        barra.set(score / 100)
        barra.pack(fill="x", padx=18, pady=(18, 9))
        mensagem = "Excelente controle" if score >= 75 else "Bom caminho" if score >= 50 else "Atenção aos gastos"
        ctk.CTkLabel(
            health_card, text=mensagem, text_color=COLOR_INCOME if score >= 50 else COLOR_WARNING,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold")
        ).pack()

        recent_card = ctk.CTkFrame(
            container, corner_radius=0, fg_color=COLOR_CARD_DARK,
            border_width=1, border_color=COLOR_BORDER_DARK
        )
        recent_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(
            recent_card, text="TRANSAÇÕES RECENTES", anchor="w", text_color=COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        ).pack(fill="x", padx=16, pady=(12, 7))
        recentes = sorted(transacoes, key=lambda item: item.data, reverse=True)[:4]
        if not recentes:
            ctk.CTkLabel(recent_card, text="Nenhuma movimentação registrada.", text_color=COLOR_TEXT_MUTED).pack(pady=22)
        for transacao in recentes:
            linha = ctk.CTkFrame(recent_card, fg_color="transparent", height=31)
            linha.pack(fill="x", padx=14, pady=1)
            tipo_receita = transacao.categoria.tipo == TipoTransacao.RECEITA
            ctk.CTkLabel(
                linha, text="↗" if tipo_receita else "↘", width=24,
                text_color=COLOR_INCOME if tipo_receita else COLOR_EXPENSE,
                font=ctk.CTkFont(size=13, weight="bold")
            ).pack(side="left")
            ctk.CTkLabel(
                linha, text=transacao.descricao, anchor="w", text_color=COLOR_TEXT_MAIN,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold")
            ).pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(
                linha, text=self._formatar_moeda(transacao.valor),
                text_color=COLOR_INCOME if tipo_receita else COLOR_TEXT_MAIN,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold")
            ).pack(side="right")

        budget_card = ctk.CTkFrame(
            container, corner_radius=0, fg_color=COLOR_CARD_DARK,
            border_width=1, border_color=COLOR_BORDER_DARK
        )
        budget_card.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(
            budget_card, text="ORÇAMENTOS", anchor="w", text_color=COLOR_TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        ).pack(fill="x", padx=16, pady=(12, 7))
        orcamentos = self.gerenciador.orcamentos[:3]
        if not orcamentos:
            ctk.CTkLabel(budget_card, text="Crie limites para acompanhar seus gastos.", text_color=COLOR_TEXT_MUTED).pack(pady=22)
        for orcamento in orcamentos:
            categoria = next((c for c in self.categorias if c.id == orcamento.categoria_id), None)
            mes, ano = map(int, orcamento.mes_ano.split("/"))
            gasto = sum(t.valor for t in transacoes if t.categoria.id == orcamento.categoria_id and t.data.month == mes and t.data.year == ano)
            percentual = min(gasto / orcamento.limite_mensal, 1.0) if orcamento.limite_mensal else 0
            linha = ctk.CTkFrame(budget_card, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(linha, text=categoria.nome if categoria else "Categoria", anchor="w", text_color=COLOR_TEXT_MAIN, font=ctk.CTkFont(size=10, weight="bold")).pack(fill="x")
            progress = ctk.CTkProgressBar(linha, height=6, progress_color=COLOR_EXPENSE if percentual >= .9 else COLOR_PRIMARY)
            progress.set(percentual)
            progress.pack(side="left", fill="x", expand=True, pady=(3, 0))
            ctk.CTkLabel(linha, text=f"{percentual * 100:.0f}%", width=38, text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=9)).pack(side="right", padx=(8, 0))

        self.update_idletasks()

    @staticmethod
    def _formatar_moeda(valor):
        texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {texto}"

    def atualizar_saldo(self):
        saldo = self.gerenciador.calc_saldo_total()
        cor = COLOR_INCOME if saldo >= 0 else COLOR_EXPENSE
        self.lbl_saldo_valor.configure(text=f"R${saldo:.2f}", text_color=cor)

    def atualizar_tabela_ext(self):
        #   Limpa e redesenha as linhas de transações no scroll frame

        #   Limpa widgets anteriores
        for widget in self.scroll_transacoes.winfo_children():
            widget.destroy()

        busca = self.entry_busca.get().strip().lower() if hasattr(self, "entry_busca") else ""
        transacoes = [
            t for t in self.gerenciador.transacoes
            if not busca or busca in t.descricao.lower() or busca in t.categoria.nome.lower() or busca in t.conta.nome.lower()
        ]

        if not transacoes:
            ctk.CTkLabel(
                self.scroll_transacoes,
                text="Nenhuma transação encontrada." if busca else "Nenhuma transação cadastrada.",
                text_color=COLOR_TEXT_MUTED
            ).pack(pady=24)
            return

        for t in sorted(transacoes, key=lambda item: item.data, reverse=True):
            frame_bloco = ctk.CTkFrame(
                self.scroll_transacoes,
                corner_radius=0,
                border_width=1,
                border_color=COLOR_BORDER_DARK,
                fg_color=COLOR_CARD_ALT
            )
            frame_bloco.pack(fill="x", pady=4, padx=4)

            sinal = "+" if t.categoria.tipo == TipoTransacao.RECEITA else "-"
            cor_valor = COLOR_INCOME if t.categoria.tipo == TipoTransacao.RECEITA else COLOR_EXPENSE

            frame_info = ctk.CTkFrame(frame_bloco, fg_color="transparent")
            frame_info.pack(side="left", padx=12, pady=10)

            lbl_descricao = ctk.CTkLabel(
                frame_info,
                text=f"#{t.id} - {t.descricao}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLOR_TEXT_MAIN,
                anchor="w"
            )
            lbl_descricao.pack(anchor="w")

            detalhes_texto = f"{t.conta.nome}  •  {t.categoria.nome}  •  {t.data.strftime('%d/%m/%Y')}"
            lbl_detalhes = ctk.CTkLabel(
                frame_info,
                text=detalhes_texto,
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED,
                anchor="w"
            )
            lbl_detalhes.pack(anchor="w", pady=(2, 0))

            btn_remover = ctk.CTkButton(
                frame_bloco,
                text="×",
                width=30,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color="#991B1B",
                command=lambda id_del=t.id: self.acao_remover_transacao(id_del)
            )
            btn_remover.pack(side="right", padx=12, pady=10)

            lbl_val = ctk.CTkLabel(
                frame_bloco,
                text=f"{sinal} {self._formatar_moeda(t.valor)}",
                text_color=cor_valor,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            lbl_val.pack(side="right", padx=12, pady=10)

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

        conta_str = self.combo_contas.get()
        conta_id = int(conta_str.split(" - ")[0])
        conta_obj = next((c for c in self.contas if c.id == conta_id), None)

        nova_transacao = Transacao(
            id=0,
            descricao=descricao,
            valor=valor,
            categoria=cat_obj,
            conta=conta_obj,
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
            self._mostrar_mensagem_status(f"Transação #{id_gerado} registrada com sucesso.")

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

            self.atualizar_lista_orc()
            self._mostrar_mensagem_status("Orçamento gravado com sucesso!")

        except ValueError:
            self._mostrar_mensagem_status("Preencha limite, mês e ano valores numéricos válidos.", erro=True)

    def atualizar_lista_orc(self):
        for widget in self.scroll_orcamentos.winfo_children():
            widget.destroy()

        if not self.gerenciador.orcamentos:
            ctk.CTkLabel(
                self.scroll_orcamentos, 
                text="Nenhum orçamento cadastrado.",
                text_color=COLOR_TEXT_MUTED
            ).pack(pady=20)
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
            pct_exibicao = (gastos / orc.limite_mensal) * 100
            cor_progresso = COLOR_EXPENSE if percentual >= 1.0 else (COLOR_WARNING if percentual >= 0.8 else COLOR_INCOME)

            frame_card = ctk.CTkFrame(
                self.scroll_orcamentos, 
                corner_radius=0,
                border_width=1,
                border_color=COLOR_BORDER_DARK,
                fg_color=COLOR_CARD_DARK
            )
            frame_card.pack(fill="x", pady=4, padx=4)

            frame_top_card = ctk.CTkFrame(frame_card, fg_color="transparent")
            frame_top_card.pack(fill="x", padx=12, pady=(10, 2))

            lbl_orc_info = ctk.CTkLabel(
                frame_top_card,
                text=f"{nome_cat} ({orc.mes_ano})",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLOR_TEXT_MAIN
            )
            lbl_orc_info.pack(side="left")

            btn_del_orc = ctk.CTkButton(
                frame_top_card,
                text="Remover",
                width=65,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#3F3F46",
                hover_color="#991B1B",
                command=lambda c_id=orc.categoria_id, m_a=orc.mes_ano: self.acao_remover_orc(c_id, m_a)
            )
            btn_del_orc.pack(side="right")

            lbl_val = ctk.CTkLabel(
                frame_card,
                text=f"Gasto: R${gastos:.2f} / R${orc.limite_mensal} ({pct_exibicao:.1f}%)",
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_val.pack(anchor="w", padx=12, pady=(0, 10))

            prog_bar = ctk.CTkProgressBar(frame_card, progress_color=cor_progresso, height=8)
            prog_bar.set(percentual)
            prog_bar.pack(fill="x", padx=12, pady=(0, 10))
            
    def acao_remover_transacao(self, transacao_id: int):
        if self.repositorio.remover_transacao(transacao_id):
            self.gerenciador.transacoes = [t for t in self.gerenciador.transacoes if t.id != transacao_id]
            self.atualizar_saldo()
            self.atualizar_tabela_ext()
            self.atualizar_lista_orc()
            self.atualizar_lista_contas()
            self.atualizar_dashboard()
            self._mostrar_mensagem_status(f"Transação #{transacao_id} removida com sucesso!")

    def acao_remover_conta(self, conta_id: int, conta_nome: str):
        if len(self.contas) <= 1:
            self._mostrar_mensagem_status("O sistema precisa manter ao menos uma conta ativa.", erro=True)
            return

        if self.repositorio.remover_conta(conta_id):
            self.contas = [c for c in self.contas if c.id != conta_id]
            self.gerenciador.transacoes = [t for t in self.gerenciador.transacoes if t.conta.id != conta_id]

            nomes_contas = [f"{c.id} - {c.nome}" for c in self.contas]
            self.combo_contas.configure(values=nomes_contas)
            self.combo_contas.set(nomes_contas[0])

            self.atualizar_saldo()
            self.atualizar_lista_contas()
            self.atualizar_tabela_ext()
            self.atualizar_dashboard()
            self.update_idletasks()

            self._mostrar_mensagem_status(f"Conta '{conta_nome}' e suas transações foram removidas.")
        else:
            self._mostrar_mensagem_status("Erro ao tentar remover conta.", erro=True)

    def acao_remover_orc(self, categoria_id: int, mes_ano: str):
        if self.repositorio.remover_orc(categoria_id, mes_ano):
            self.gerenciador.orcamentos = [
                o for o in self.gerenciador.orcamentos
                if not (o.categoria_id == categoria_id and o.mes_ano == mes_ano)
            ]

            self.atualizar_lista_orc()
            self.update_idletasks()

            self._mostrar_mensagem_status("Orçamento removido com sucesso.")
        else:
            self._mostrar_mensagem_status("Erro ao tentar remover o orçamento.")

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
        cor = COLOR_EXPENSE if erro else COLOR_INCOME

        if getattr(self, "_timer_status", None) is not None:
            self.after_cancel(self._timer_status)
            self._timer_status = None

        self.lbl_status.configure(text=texto, text_color=cor)
        self.update_idletasks()

        self._timer_status = self.after(3500, self._limpar_status)

    def _limpar_status(self):
        self.lbl_status.configure(text="")
        self._timer_status = None

if __name__ == "__main__":
    app = AppGUI()
    app.mainloop()
