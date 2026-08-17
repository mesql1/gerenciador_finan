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
COLOR_CARD_DARK = "#27272A"
COLOR_BORDER_DARK = "#3F3F46"
COLOR_TEXT_MAIN = "#F4F4F5"
COLOR_TEXT_MUTED = "#A1A1AA"

COLOR_INCOME = "#10B981"
COLOR_EXPENSE = "#EF4444"
COLOR_WARNING = "#F59E0B"

#   TODO: Consertar problema da listagem das contas

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

        self.canvas_graficos = None
        self._timer_status = None

        #   Componentes visuais
        self._criar_header()

        self.lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12, weight="normal"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(side="bottom", pady=6)

        self.tabview = ctk.CTkTabview(
            self,
            command=self._trocar_aba,
            fg_color="transparent",
            segmented_button_fg_color=COLOR_CARD_DARK,
            segmented_button_selected_color="#3B82F6",
            segmented_button_selected_hover_color="#2563EB"
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 5))

        self.tab_transacoes = self.tabview.add("Transações e Extrato")
        self.tab_dashboard = self.tabview.add("Dashboard e Gráficos")
        self.tab_contas = self.tabview.add("Contas")
        self.tab_orcamentos = self.tabview.add("Orçamentos")
        self.tab_exportar = self.tabview.add("Exportar Dados")

        self._construir_aba_transacoes()
        self._construir_aba_dashboard()
        self._construir_aba_contas()
        self._construir_aba_orcamentos()
        self._construir_aba_exportar()
        
        #   Atualização da tela inicial com dados
        self.atualizar_saldo()
        self.atualizar_tabela_ext()
        self.atualizar_lista_contas()
        self.atualizar_lista_orc()
        self.atualizar_dashboard()
        self._trocar_aba()

    #   ---
    #   LAYOUT
    #   ---

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
            placeholder_text="Descrição do lançamento",
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
            saldo_conta = self.gerenciador.calc_saldo_conta(conta.id)
            cor_saldo = COLOR_INCOME if saldo_conta >= 0 else COLOR_EXPENSE

            frame_card = ctk.CTkFrame(
                self.scroll_contas,
                corner_radius=6,
                border_width=1,
                border_color=COLOR_BORDER_DARK,
                fg_color=COLOR_CARD_DARK
            )
            frame_card.pack(fill="x", pady=4, padx=4)

            lbl_nome = ctk.CTkLabel(
                frame_card,
                text=f"{conta.nome}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLOR_TEXT_MAIN
            )
            lbl_nome.pack(side="left", padx=16, pady=14)

            lbl_saldo = ctk.CTkLabel(
                frame_card,
                text=f"R${saldo_conta:.2f}",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=cor_saldo
            )
            lbl_saldo.pack(side="right", padx=12, pady=14)

            btn_del_conta = ctk.CTkButton(
                frame_card,
                text="Remover",
                width=65,
                height=28,
                font=ctk.CTkFont(size=11),
                fg_color="#3F3F46",
                hover_color="#991B1B",
                command=lambda c_id=conta.id, c_nome=conta.nome: self.acao_remover_conta(c_id, c_nome)
            )
            btn_del_conta.pack(side="right", padx=12, pady=14)

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

    def _trocar_aba(self):
        #   Executado automaticamente sempre que o usuário clica em qualquer aba
        aba_atual = self.tabview.get()

        if aba_atual == "Transações e Extrato": self.atualizar_tabela_ext()
        elif aba_atual == "Dashboard e Gráficos": self.atualizar_dashboard()
        elif aba_atual == "Contas": self.atualizar_lista_contas()
        elif aba_atual == "Orçamentos": self.atualizar_lista_orc()

        self.update_idletasks()

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
            self._trocar_aba()
            self._mostrar_mensagem_status(f"Lançamento #{id_gerado} registrado com sucesso.")

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
            self.atualizar_dashboard()
            self._trocar_aba()
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