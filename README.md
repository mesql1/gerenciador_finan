#  Gerenciador de Finanças Pessoais (CLI)

> Uma aplicação em Python orientada a objetos para controle financeiro pessoal, gerenciamento de orçamentos e exportação de dados, construída com arquitetura em camadas e boas práticas de desenvolvimento.

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

#  Sobre o Projeto

O **Gerenciador de Finanças Pessoais** é uma ferramenta de linha de comando (CLI) desenvolvida para facilitar o registro de receitas e despesas, o controle de tetos orçamentários por categoria e a análise rápida da saúde financeira mensal. 

O foco principal do projeto foi aplicar **conceitos reais de engenharia de software**, tais como a separação clara de responsabilidades (SoC), validação rigorosa de entradas de usuário e manipulação segura de estruturas de dados e persistência.

---

##  Funcionalidades Atuais

-  **CRUD de Transações:** Cadastre, liste, busque e remova receitas e despesas com datas personalizadas ou automáticas.
-  **Categorização de Gastos:** Suporte nativo a categorias mapeadas com enums fortemente tipadas (`TipoTransacao.RECEITA` / `TipoTransacao.DESPESA`).
-  **Alertas de Orçamento:** Defina limites mensais por categoria. O sistema avisa em tempo real se um novo gasto atingiu 80% ou estourou (100%+) o teto estipulado.
-  **Cálculo de Saldo Geral e Mensal:** Algoritmos eficientes para apuração de saldo total e relatórios por mês/ano.
-  **Persistência de Dados (SQL):** Salvamento e carregamento automático do estado da aplicação com serialização/desserialização de objetos complexos e datas.
-  **Exportação para CSV:** Geração de extratos prontos para abertura no Microsoft Excel ou Google Planilhas (com codificação UTF-8-SIG e separadores regionais).
-  **CLI Robusta:** Tratamento de exceções em tempo de execução para evitar quebras por entradas de dados inválidas no terminal.

---

##  Arquitetura do Projeto

O código foi estruturado em camadas independentes para facilitar a manutenção e futuros testes unitários:

```text
financas_app/
│
├── modelos.py       # Classes de domínio (Transacao, Categoria, Orcamento, Enums)
├── repositorio.py   # Camada de persistência (carregamento/salvamento do JSON)
├── servicos.py      # Regras de negócio (cálculos de saldo, alertas e filtros)
├── main.py          # Interface do usuário (Menu CLI e captura de entradas)
└── financas.db (Gerado automaticamente ao salvar)
```
##  Como Executar o Projeto

### Pré-requisitos

Python 3.10 ou superior instalado no sistema.

## Passo a Passo

**Clone o repositório**:

```Bash
git clone [https://github.com/mesql1/gerenciador_finan.git](https://github.com/mesql1/gerenciador_finan.git)
cd SEU_REPOSITORIO
```
**Execute a aplicação**:

```Bash
python main.py
```
---
##  Roadmap de Atualizações Futuras

Este projeto está sob desenvolvimento contínuo. As próximas etapas incluem:

[X] Migração para SQLite: Substituição do arquivo JSON por banco de dados relacional via sqlite3 nativo.

[ ] Testes Automatizados: Implementação de cobertura de testes unitários com pytest para a camada de serviços e cálculos.

[ ] Visualização Gráfica: Integração com a biblioteca matplotlib para gerar gráficos de pizza por categoria e barras para evolução mensal.

[ ] Gerenciamento de Múltiplas Contas: Suporte a separação por carteiras (Ex: Cartão de Crédito, Conta Corrente, Dinheiro).

## Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
