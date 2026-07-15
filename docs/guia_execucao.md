# Executando o Projeto

Este guia descreve como configurar o ambiente de desenvolvimento, instalar as dependências, executar a aplicação e rodar os testes automatizados.

---

## Pré-requisitos

| Requisito | Versão mínima |
|-----------|---------------|
| Python    | 3.12          |
| pip       | 21+           |


> A interface gráfica utiliza **PyQt6**, que requer um ambiente com suporte a display gráfico.

---

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/GrupoBiomec/Biomec-SAS.git
cd Biomec-SAS
```

### 2. Crie e ative um ambiente virtual

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

## Executando a aplicação

Após a instalação das dependências, execute:

```bash
python src/main.py
```

---

## Testes e Cobertura

O projeto possui testes automatizados para os principais componentes, incluindo:

- leitura e processamento de arquivos;
- operações matemáticas;
- gerenciamento de estado;
- scripts de processamento;
- serialização de projetos.

### Executar todos os testes

```bash
pytest
```

### Executar os testes com relatório de cobertura

```bash
pytest --cov
```

### Gerar relatório de cobertura em HTML

```bash
pytest --cov --cov-report=html
```

O relatório será gerado na pasta `htmlcov/`.

Para visualizá-lo, abra o arquivo:

```text
htmlcov/index.html
```

em qualquer navegador.