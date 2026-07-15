# Guia do Usuário — Biomec SAS

Este manual descreve os principais procedimentos operacionais para a condução de análises de sinais biomecânicos utilizando o  **Biomec SAS**. 

---

## 1. Formatos de Arquivo Suportados e Importação

O Biomec SAS suporta a importação de dois formatos principais de arquivos de dados:

*   **Arquivos `.EMT`:** Arquivos de texto tabelado contendo dados cinemáticos ou eletromiográficos. O software realiza o parsing automático de delimitadores, colunas e metadados.
*   **Arquivos `.TDF`:** Formato binário proprietário da *BTS Bioengineering*. A plataforma realiza a leitura da estrutura interna do arquivo, extraindo automaticamente as informações do cabeçalho, canais analógicos e tridimensionais, frequências de amostragem e unidades originais de coleta.

### Como Importar Arquivos:
1. Acesse o menu superior: `Arquivo` &rarr; `Abrir Arquivo`.
2. Selecione a opção correspondente ao formato do arquivo desejado (`Arquivo EMT` ou `Arquivo TDF`).
3. Na janela de seleção do sistema, navegue até o diretório correspondente, selecione os arquivos (é permitido selecionar múltiplos arquivos simultaneamente) e clique em `Abrir`.
4. Os arquivos carregados serão listados na seção superior da árvore lateral esquerda (**"Arquivos carregados"**).

---

## 2. Visualização e Criação de Gráficos

Uma vez importados, os sinais ficam disponíveis para exploração gráfica bidimensional.

### Como Criar um Gráfico:
1. Na árvore lateral esquerda, clique com o **botão direito do mouse** sobre o nome do arquivo importado.
2. Selecione a opção **"Adicionar novo gráfico"**.
3. Na janela de configuração que se abre:
    *   **Tipo de Gráfico:** Selecione entre `Linha` (para traçados contínuos) ou `Dispersão` (para nuvens de pontos).
    *   **Eixo X:** Defina a variável de referência temporal ou espacial (normalmente `tempo` ou `frame`).
    *   **Eixo Y:** Selecione a variável dependente a ser analisada.
    *   **Título e Unidades:** O software sugere automaticamente as unidades baseadas no arquivo original, mas permite a customização de títulos e legendas.
4. Clique em `Confirmar`. O gráfico criado será aninhado abaixo do respectivo arquivo na árvore lateral.
5. Clique sobre o gráfico criado na árvore lateral para exibi-lo na área de visualização central.

> **Múltiplas Curvas:** Para criar gráficos de diversas variáveis Y em lote compartilhando o mesmo eixo X, clique com o botão direito sobre o arquivo e selecione **"Visualizar múltiplas curvas"**. Uma composição será criada automaticamente na seção inferior esquerda.

### Recursos de Visualização:
*   **Zoom:** Clique com o botão direito sobre o gráfico ou a composição na árvore lateral correspondente e selecione **"Ativar Zoom"**. Com o zoom ativo, selecione a área do gráfico que deseja ampliar. Para restabelecer a escala original, clique no botão **"Desativar Zoom"** exibido no topo direito do grafico.
*   **Ajustes Visuais:** Clique com o botão direito sobre o gráfico na árvore lateral e selecione **"Editar Gráfico"** para alterar título, cor da curva ou nomes dos eixos.

---

## 3. Tratamento de Sinais e Limpeza de Dados

### 3.1. Preenchimento de Lacunas (Interpolação)
Durante aquisições cinemáticas, podem haver momentos de perdas de sinal (valores `NaN`). O módulo de interpolação reconstrói estes intervalos de forma matemática.

*   **Como Acessar:** Menu superior `Processamento` &rarr; `Métodos de Interpolação`.
*   **Operação:** Selecione as variáveis que deseja interpolar e escolha o algoritmo de preenchimento: linear, spline ou média.
   O modo "preview" permite que o usuário visualize o resultado da aplicação do método antes de salvar os dados, além de permitir que ele adicione um ponto manualmente (funcionalidade chamada de "wywiwyg", que significa "what you want is what you get").


### 3.2. Filtragem Digital de Sinais (Filtro Butterworth)
Filtros digitais recursivos do tipo Butterworth são implementados sem atraso de fase.

*   **Como Acessar:** Menu superior `Processamento` &rarr; `Filtrar sinal` &rarr; `Passa-Baixa` ou `Passa-Alta`.
*   **Janela de Visualização Interativa:** A janela de filtragem exibe simultaneamente o sinal original (cinza) e o resultado filtrado (azul) em tempo real conforme os parâmetros são alterados.
*   **Parâmetros Configuráveis:**
    *   **Frequência de Corte ($f_c$):** Limite de atenuação do sinal (em Hz).
    *   **Ordem do Filtro:** Define a declividade da banda de transição.
    *   **Retificação:** Disponível em filtros passa-baixa, permite calcular o valor absoluto do sinal ($|y|$) antes da filtragem, essencial para a obtenção do envelope linear de sinais de Eletromiografia (EMG).
    *   **Algoritmo de Winter:** Exclusivo para filtros passa-baixa, executa uma rotina de análise residual para estimar de forma ótima a frequência de corte do ruído de alta frequência.

### 3.3. Recorte Temporal (Trim)
Permite a limitação da janela temporal de análise.

*   **Como Acessar:** Menu superior `Processamento` &rarr; `Recorte Temporal`.
*   **Operação:** O usuário visualiza os sinais agrupados por categorias físicas (cinemática, força, EMG) e ajusta barras deslizantes verticais (verde para início, vermelha para fim) para definir a nova janela de análise. O recorte afeta de forma síncrona todas as variáveis do arquivo selecionado para garantir a integridade temporal do ensaio.
*   **Translação Temporal:** O software oferece a opção de transladar o eixo de tempo para iniciar exatamente em zero no novo ponto de corte.

### 3.4. Definição de Offset (Deslocamento de Nível)


*   **Como Acessar:** Menu superior `Processamento` &rarr; `Definir Offset`.
*   **Operação:** Permite selecionar múltiplas colunas e indicar o valor numérico a ser subtraído de cada ponto. É recomendado não selecionar muitas colunas de uma vez, para não poluir a preview.
 É possível escolher entre sobrescrever os dados originais no arquivo ativo ou salvar os resultados como novas variáveis independentes.

---

## 4. Informações e Análise Estatística da Curva

Estatísticas descritivas são calculadas de forma dinâmica para qualquer gráfico selecionado.

### Como Acessar as Informações:
1. Na árvore lateral esquerda, expanda o arquivo correspondente.
2. Clique com o **botão direito do mouse** sobre o gráfico desejado e selecione **"Informações da Curva"**.

### Métricas Computadas:
*   **Valores Extremos:** Valores máximos e mínimos dos eixos X e Y, além de picos máximos e mínimos globais.
*   **Métricas Descritivas de Y:** Root Mean Square (RMS) e amplitude pico a pico.
*   **Pontos de Amostragem:** Frequência de amostragem estimada (Hz) e quantidade total de pontos válidos (excluindo-se lacunas).

---

## 5. Operações Matemáticas entre Variáveis

O menu superior `Operações` permite derivar novos canais de dados a partir de relações matemáticas:

*   **Aritmética Básica (`Operações` &rarr; `Aritmética Básica`):** Efetua operações algébricas ($+, -, \times, \div$) entre duas colunas de dados ou entre uma coluna e uma constante numérica.
*   **Trigonometria (`Operações` &rarr; `Trigonometria`):** Calcula funções trigonométricas ($seno$, $cosseno$, $tangente$) de variáveis angulares. O software detecta a unidade de entrada (graus ou radianos) para a correta aplicação das relações.
*   **Cálculo e Funções Escalares (`Operações` &rarr; `Cálculo e Funções Escalares`):**
    *   *Derivadas:* Primeira e segunda derivadas temporais (velocidade e aceleração) calculadas via diferenças finitas centrais.
    *   *Integral:* Área sob a curva calculada pelo método trapezoidal cumulativo.
    *   *Escalares:* Módulo ($|y|$), inverso ($1/y$) e raiz quadrada ($\sqrt{y}$).
*   **Definir Ângulos (`Operações` &rarr; `Definir Ângulos`):** Permite calcular ângulos articulares ou de inclinação espacial a partir de coordenadas espaciais 3D (marcadores cinemáticos).

---

## 6. Automatização por Scripts

Os scripts otimizam fluxos de processamento repetitivos sobre múltiplos conjuntos de dados, automatizando essas ações. 

### Diferenças entre Tipos de Scripts:
*   **Scripts de Arquivo:** Operam sobre a estrutura bruta do DataFrame. Servem para criar gráficos em lote, recortar trechos temporais e gerar novas variáveis calculadas de forma automatizada no arquivo selecionado.
*   **Scripts de Gráfico:** Otimizam a etapa de tratamento dos dados. Servem para aplicar configurações pre-estabelecidas de filtros, interpolações, offsets e polinômios de referência em um gráfico.

### Como Criar e Executar Scripts:
1. Acesse o menu superior `Scripts` &rarr; `Criar Novo Script de Arquivo` ou `Criar Novo Script de Gráfico`.
2. Configure a sequência de etapas na interface de criação e salve o roteiro.
3. Para aplicar, clique com o botão direito sobre o arquivo ou gráfico na árvore lateral, clique em `Aplicar Script` e selecione o roteiro correspondente.

---

## 7. Exportação de Resultados e Projetos

O menu superior `Exportar` possui as seguintes opções:

*   **Salvar Projeto (`.sas`):** Salva o estado completo da análise (arquivos importados, configurações de plotagem, composições visuais e histórico do pipeline) em um arquivo compactado `.sas`. Para retomar o trabalho, acesse `Arquivo` &rarr; `Abrir Projeto (.sas)`.
*   **Exportar Histórico de Processamento (`.txt`):** Gera um relatório contendo todas as operações realizadas (pipeline de processamento).
*   **Exportar Gráficos e Relatórios:** Acessível em `Exportar` &rarr; `Exportar Gráficos`. Permite selecionar múltiplos gráficos na lista e exportá-los em três formatos:
    *   *PDF:* Documento contendo as imagens vetorizadas dos gráficos selecionados.
    *   *TXT:* Arquivo com as estatísticas descritivas/ informações das curvas associadas.
    *   *ZIP:* Arquivo compactado contendo o documento em PDF e o relatório estatístico correspondente.