# Arquitetura e Estrutura do Código

O projeto adota uma arquitetura modular baseada na separação de responsabilidades.

---

## Estrutura do Código

```
Biomec-SAS/
├── .github/workflows/      # Rotinas automáticas do GitHub para testes, publicação de versões e atualização do site de documentação.
├── src/                            
│   ├── main.py             # Ponto de entrada da aplicação
│   ├── controller/         # Controle central e gerenciamento do estado do programa
│   ├── processamento/      # Cálculos matemáticos, tratamento de dados e automação de rotinas
│   ├── arquivos/          
│   │   ├── parsers/        # Leitores que convertem os arquivos específicos do laboratório em tabelas Pandas
│   │   ├── exportadores/   # Ferramentas para gerar relatórios, gráficos (PDF/TXT) e logs de histórico
│   │   └── projeto/        # Gerenciamento da abertura e salvamento das sessões de trabalho (.sas)
│   └── ui/                 # Interface gráfica do usuário (janelas secundárias, painéis laterais e menus)
├── tests/                          # Testes automatizados de unidade e integração
├── pyproject.toml   
├── assets/                         # Ícone logo do app
├── docs/                           # Documentação oficial do projeto (.md)
├── requirements.txt              
└── LICENSE.txt                     
```

---

## Detalhamento dos Módulos Principais

### Controladora de Estado (`src/controller/`)
O módulo `gerenciador_estado.py` atua como o núcleo de coordenação do aplicativo.
*   **Gerenciamento Centralizado:** Mantém o dicionário global de arquivos importados, os dataframes originais e filtrados, configurações de gráficos ativos e roteiros de scripts.
*   **Pipeline de Rastreabilidade:** Registra todas as operações aplicadas a cada canal do sinal, de modo a viabilizar a reprodutibilidade científica e o salvamento do progresso realizado.

### Camada de Processamento de Dados (`src/processamento/`)
Este pacote encapsula toda a lógica matemática e estatística, mantendo-se independente da interface gráfica:
*   `operacoes.py`: Funções para transformações matemáticas clássicas.
*   `limpeza.py`: Algoritmos para correção de ruídos e dados inconsistentes, interpolação linear, média móvel e spline.
*   `informacoes_curvas.py`: Cálculos estatísticos das curvas analisadas.
*   `gera_graficos.py`: Prepara e formata os dados matemáticos para que sejam exibidos corretamente nos gráficos da tela (pelo PyQtGraph).
*   `executadores_scripts`: Responsável por executar os scripts de automação.

### Entrada, Saída e Salvamento (`src/arquivos/`)
Responsável pela entrada e saída de dados do sistema:
*   `parsers/`: Módulos de decodificação para extração estruturada dos dados.
*   `exportadores/`: Responsável por salvar o histórico de operações feitas nas curvas (em .txt) e exportar os gráficos gerados (em .pdf).
*   `projeto/`: Gerencia o salvamento das sessões de trabalho no formato .sas. Esse arquivo é um pacote compactado (ZIP) que reúne as configurações da análise em JSON e os dados das tabelas no formato padrão Apache Parquet.

### Interface Gráfica (`src/ui/`)
Desenvolvida utilizando a biblioteca **PyQt6**:
*   `main_window.py`: Janela principal do programa, organiza o layout que centraliza menus e atalhos globais.
*   `arvore.py`: Coordena as árvores laterais que exibem os arquivos abertos e os gráficos criados.
*   `exibe_graficos.py`: Utiliza o *PlotWidget* do *PyQtGraph* para renderização e gerencia a exibição dos gráficos na tela.
*   `dialogs/`: Diálogos/Janelas secundárias utilizadas quando o usuário precisa digitar parâmetros específicos