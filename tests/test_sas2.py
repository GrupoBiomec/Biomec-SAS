import pytest
import pandas as pd
import json
import zipfile
from controller.gerenciador_estado import GerenciadorEstado


@pytest.fixture
def dataframe_teste():
    """Fixture para fornecer um DataFrame simples para serialização."""
    # 1. ARRANGE
    return pd.DataFrame({"a": [1, 2, 3]})


@pytest.fixture
def estado_populado(dataframe_teste):
    """Fixture que retorna um GerenciadorEstado com dados de projeto complexos."""
    # 1. ARRANGE
    estado = GerenciadorEstado()
    estado.guarda_arquivos["teste"] = {
        "dataframe": dataframe_teste,
        "dataframe_original": dataframe_teste.copy(),
        "pipeline": [{"acao": "Recorte Temporal", "inicio": 1, "fim": 2}],
        "pipeline_colunas": {"a": [{"acao": "offset", "valor": 5}]},
        "colunas_modificadas": {"a"},
    }
    estado.guarda_graficos["teste"] = {
        "graf1": {
            "tipo": "Linha",
            "titulo": "graf1",
            "eixo_x": "a",
            "eixo_y": "a",
            "unidade_x": "s",
            "unidade_y": "V",
        }
    }
    return estado


def test_salvar_e_abrir_projeto_sas_preserva_estrutura_completa(
    estado_populado, tmp_path
):
    # 1. ARRANGE
    estado = estado_populado
    caminho_projeto = tmp_path / "teste_projeto.sas"

    # 2. ACT
    estado.salvar_projeto(str(caminho_projeto))

    # 3. ASSERT
    # Verifica integridade do arquivo ZIP e a existência de config.json
    assert caminho_projeto.exists()
    with zipfile.ZipFile(caminho_projeto, "r") as zipf:
        assert "config.json" in zipf.namelist()
        with zipf.open("config.json") as f:
            config = json.load(f)

    # Inspeciona campos específicos no arquivo JSON bruto para garantir exportação correta
    assert "teste" in config["guarda_arquivos"]
    assert (
        config["guarda_arquivos"]["teste"]["pipeline"][0]["acao"] == "Recorte Temporal"
    )
    assert "colunas_modificadas" in config["guarda_arquivos"]["teste"]

    # Restaura o projeto em uma nova instância do gerenciador de estado
    novo_estado = GerenciadorEstado()
    novo_estado.abrir_projeto(str(caminho_projeto))

    # Garante correspondência idêntica com o estado original e retorno dos conjuntos (set) do Python
    assert "teste" in novo_estado.guarda_arquivos
    assert isinstance(novo_estado.guarda_arquivos["teste"]["colunas_modificadas"], set)
    assert "a" in novo_estado.guarda_arquivos["teste"]["colunas_modificadas"]
    assert (
        novo_estado.guarda_arquivos["teste"]["pipeline"][0]["acao"]
        == "Recorte Temporal"
    )
    pd.testing.assert_frame_equal(
        novo_estado.guarda_arquivos["teste"]["dataframe"],
        estado.guarda_arquivos["teste"]["dataframe"],
    )


def test_abrir_projeto_sem_config_json_lanca_file_not_found_error(tmp_path):
    # 1. ARRANGE
    # Cria um zip vazio (sem o config.json)
    caminho_projeto_invalido = tmp_path / "projeto_invalido.sas"
    with zipfile.ZipFile(caminho_projeto_invalido, "w") as zipf:
        zipf.writestr("outros_dados.txt", "conteudo")

    estado = GerenciadorEstado()

    # 2. ACT & 3. ASSERT
    with pytest.raises(FileNotFoundError, match="config.json não encontrado"):
        estado.abrir_projeto(str(caminho_projeto_invalido))


def test_abrir_projeto_corrompido_lanca_bad_zip_file(tmp_path):
    # 1. ARRANGE
    # Escreve um arquivo de texto qualquer disfarçado de .sas
    caminho_corrompido = tmp_path / "corrompido.sas"
    caminho_corrompido.write_text("não sou um arquivo zip")

    estado = GerenciadorEstado()

    # 2. ACT & 3. ASSERT
    with pytest.raises(zipfile.BadZipFile):
        estado.abrir_projeto(str(caminho_corrompido))
