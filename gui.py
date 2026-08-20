import csv
import sqlite3
import customtkinter as ctk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from modelos import Transacao, TipoTransacao, Categoria, Orcamento, Conta
from servicos import GerenciadorFin
from repositorio import RepoSQLite

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

COLOR_BG_DARK = "#18181B"
COLOR_SIDEBAR = "#18181B"
COLOR_CARD_DARK = "#27272A"
COLOR_BORDER_DARK = "#3F3F46"
COLOR_TEXT_MAIN = "#F4F4F5"
COLOR_TEXT_MUTED = "#A1A1AA"

COLOR_INCOME = "#10B981"
COLOR_EXPENSE = "#EF4444"
COLOR_WARNING = "#F59E0B"
COLOR_PRIMARY = "#2563EB"

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        #   Configurações da janela
        self.title("Gerenciador de Finanças Pessoais")
        self.geometry("1050x760")
        self.resizable(True, True)

        #   Camada de Dados e Serviços
        self.repositorio = RepoSQLite("financas_1.0.db")
        self.gerenciador = GerenciadorFin()

        self.categorias = self.repositorio.listar_categorias()
        self.contas = self.repositorio.listar_contas()
        self.gerenciador.transacoes = self.repositorio.carregar_transacoes()
        self.gerenciador.orcamentos = self.repositorio.carregar_orcamentos()

        self.aba_ativa = "transacoes"
        self.canvas_graficos = None
        self._timer_status = None
        self.contas_exp = set() #   Guarda os IDs das contas "abertas"

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._construir_sidebar()
        self._construir_area_conteudo()

        self.navegar_para("transacoes")
        self.atualizar_saldo()
        
    #   ---
    #   LAYOUT
    #   ---

    #   TODO: Consertar problema da aba de exportação

    def _construir_sidebar(self):
        self.frame_sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=COLOR_SIDEBAR,
            border_width=1,
            border_color=COLOR_BORDER_DARK
        )
        self.frame_sidebar.grid(row=0, column=0, sticky="nsew")

        self.lbl_logo = ctk.CTkLabel(
            self.frame_sidebar,
            text="FINANÇAS",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        self.lbl_logo.pack(anchor="w", padx=20, pady=(24, 4))

        self.lbl_logo_sub = ctk.CTkLabel(
            self.frame_sidebar,
            text="Painel de Controle",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_logo_sub.pack(anchor="w", padx=20, pady=(0, 20))

        self.botoes_nav = {}
        itens_menu = [
            ("transacoes", "Transações"),
            ("dashboard", "Dashboard"),
            ("contas", "Contas"),
            ("orcamentos", "Orçamentos"),
            ("exportar", "Exportação")
        ]

        for idx, (chave, rotulo) in enumerate(itens_menu, start=2):
            btn = ctk.CTkButton(
                self.frame_sidebar,
                text=rotulo,
                height=38,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="transparent",
                text_color=COLOR_TEXT_MUTED,
                hover_color=COLOR_CARD_DARK,
                command=lambda k=chave: self.navegar_para(k)
            )
            btn.pack(side="top", fill="x", padx=12, pady=3)
            self.botoes_nav[chave] = btn

        self.card_saldo_sidebar = ctk.CTkFrame(
            self.frame_sidebar,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.card_saldo_sidebar.pack(side="bottom", fill="x", padx=12, pady=16)

        self.lbl_saldo_titulo = ctk.CTkLabel(
            self.card_saldo_sidebar,
            text="SALDO TOTAL",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_saldo_titulo.pack(anchor="w", padx=12, pady=(10, 0))

        self.lbl_saldo_valor = ctk.CTkLabel(
            self.card_saldo_sidebar,
            text="R$0,00",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_saldo_valor.pack(anchor="w", padx=12, pady=(0, 10))

    def _construir_area_conteudo(self):
        self.frame_main = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_main.grid(row=0, column=1, sticky="nsew", padx=20, pady=16)
        self.frame_main.grid_rowconfigure(0, weight=1)
        self.frame_main.grid_columnconfigure(0, weight=1)

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
        self.lbl_status.grid(row=1, column=0, pady=(6, 0), sticky="ew")

    def navegar_para(self, nome_tela: str):
        self.aba_ativa = nome_tela

        for chave, btn in self.botoes_nav.items():
            if chave == nome_tela:
                btn.configure(fg_color=COLOR_PRIMARY, text_color=COLOR_TEXT_MAIN)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED)

        for chave, tela in self.telas.items():
            if chave == nome_tela:
                tela.grid(row=0, column=0, sticky="nsew")
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
            corner_radius=6,
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
            corner_radius=6,
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
                corner_radius=6,
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
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        self.frame_dash_container.grid(row=0, column=0, sticky="nsew")

        return tela

    def _criar_tela_contas(self):
        tela = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        tela.grid_rowconfigure(1, weight=1)
        tela.grid_columnconfigure(0, weight=1)

        self.frame_conta_form = ctk.CTkFrame(
            tela,
            corner_radius=6,
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
            corner_radius=6,
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
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER_DARK,
            fg_color=COLOR_CARD_DARK
        )
        frame_exp.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        lbl_exp = ctk.CTkLabel(frame_exp, text="EXPORTAÇÃO DE DADOS", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN)
        lbl_exp.pack(pady=(40, 12))

        frame_info_box = ctk.CTkFrame(frame_exp, fg_color=COLOR_BG_DARK, corner_radius=6)
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
            corner_radius=6,
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
            corner_radius=6,
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
            corner_radius=6,
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
            corner_radius=6,
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
            corner_radius=6,
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

        frame_info_box = ctk.CTkFrame(self.frame_exp, fg_color=COLOR_BG_DARK, corner_radius=6)
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

    def _construir_aba_contas(self):
        self.frame_conta_form = ctk.CTkFrame(
            self.tab_contas,
            corner_radius=6,
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
                corner_radius=6,
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
                    corner_radius=6,
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
            corner_radius=6,
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

        if not self.gerenciador.transacoes:
            ctk.CTkLabel(
                self.frame_dash_container,
                text="Sem dados para geração de dashboard.",
                text_color=COLOR_TEXT_MUTED
            ).pack(expand=True)
            return

        cor_fundo = COLOR_CARD_DARK
        cor_texto = COLOR_TEXT_MAIN

        #   Figura: Lado a Lado
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4), facecolor=cor_fundo)
        fig.subplots_adjust(wspace=0.35)

        #   Figura: Rosca (Despesa por Categoria)
        gastos_por_cat = {}
        for t in self.gerenciador.transacoes:
            if t.categoria.tipo == TipoTransacao.DESPESA:
                gastos_por_cat[t.categoria.nome] = gastos_por_cat.get(t.categoria.nome, 0.0) + t.valor

        #   Formata o texto exibido no gráfico de rosca
        def formatar_rotulo(pct, allvals):
            absolute = sum(allvals) * (pct / 100.0)

            return f"{pct:.1f}%\n(R${absolute:.0f})" if pct >= 4 else ""

        if gastos_por_cat:
            labels = list(gastos_por_cat.keys())
            valores = list(gastos_por_cat.values())
            cores = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#64748B"]

            ax1.set_facecolor(cor_fundo)
            wedges, texts, autotexts = ax1.pie(
                valores,
                labels=labels,
                autopct=lambda pct: formatar_rotulo(pct, valores),
                pctdistance=0.75,
                startangle=140,
                colors=cores,
                textprops=dict(color=cor_texto, fontsize=8),
                wedgeprops=dict(width=0.38, edgecolor=cor_fundo)
            )
            #   Ajusta a cor dos números das porcentagens
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_weight("bold")

            ax1.set_title("Despesas por Categoria", color=cor_texto, fontsize=12, fontweight="bold")

        else:
            ax1.set_facecolor(cor_fundo)
            ax1.text(0.5, 0.5, "Sem despesas", ha="center", va="center", color=COLOR_TEXT_MUTED)

        total_receita = sum(t.valor for t in self.gerenciador.transacoes if t.categoria.tipo == TipoTransacao.RECEITA)
        total_despesa = sum(t.valor for t in self.gerenciador.transacoes if t.categoria.tipo == TipoTransacao.DESPESA)

        ax2.set_facecolor(cor_fundo)
        barras = ax2.bar(["Receitas", "Despesas"], [total_receita, total_despesa], color=[COLOR_INCOME, COLOR_EXPENSE], width=0.45)
        ax2.set_title("Receitas vs Despesas (R$)", color=cor_texto, fontsize=11, fontweight="bold")
        ax2.tick_params(colors=cor_texto)

        #   Adiciona valores no topo das barras
        for bar in barras:
            yval = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.02 if yval > 0 else 0), f"R${yval:.2f}", ha="center", va="bottom", color=cor_texto, fontsize=8)

        #   Renderização da figura no Canvas do Tkinter
        self.canvas_graficos = FigureCanvasTkAgg(fig, master=self.frame_dash_container)
        self.canvas_graficos.draw_idle()
        self.canvas_graficos.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)

        self.update_idletasks()

    def atualizar_saldo(self):
        saldo = self.gerenciador.calc_saldo_total()
        cor = COLOR_INCOME if saldo >= 0 else COLOR_EXPENSE
        self.lbl_saldo_valor.configure(text=f"R${saldo:.2f}", text_color=cor)

    def atualizar_tabela_ext(self):
        #   Limpa e redesenha as linhas de transações no scroll frame

        #   Limpa widgets anteriores
        for widget in self.scroll_transacoes.winfo_children():
            widget.destroy()

        if not self.gerenciador.transacoes:
            ctk.CTkLabel(
                self.scroll_transacoes,
                text="Nenhuma transação cadastrada.",
                text_color=COLOR_TEXT_MUTED
            ).pack(pady=24)
            return

        for t in self.gerenciador.transacoes:
            frame_bloco = ctk.CTkFrame(
                self.scroll_transacoes,
                corner_radius=6,
                border_width=1,
                border_color=COLOR_BORDER_DARK,
                fg_color=COLOR_BG_DARK
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

            detalhes_texto = f"{t.categoria.nome} - {t.data.strftime('%d/%m/%Y')}"
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
                text="Remover",
                width=65,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color="#3F3F46",
                hover_color="#991B1B",
                command=lambda id_del=t.id: self.acao_remover_transacao(id_del)
            )
            btn_remover.pack(side="right", padx=12, pady=10)

            lbl_val = ctk.CTkLabel(
                frame_bloco,
                text=f"{sinal} R${t.valor:.2f}",
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
                corner_radius=6,
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

        self._timer_status = self.after(3500, self._timer_status)

    def _limpar_status(self):
        self.lbl_status.configure(text="")
        self._timer_status = None

if __name__ == "__main__":
    app = AppGUI()
    app.mainloop()