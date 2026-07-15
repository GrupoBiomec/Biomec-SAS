import pytest
import json
from arquivos.exportadores.historico import salvar_historico_processamento


@pytest.fixture
def pipelines_teste():
    """Fixture para fornecer um dicionário de pipelines de teste."""
    # 1. ARRANGE
    return {
        "arquivo1": [
            {
                "categoria": "Tratamento de Dados",
                "acao": "Recorte Temporal",
                "inicio": 0.0,
                "fim": 10.0,
                "deslocar_0": True,
                "batch_id": 1,
            },
            {
                "categoria": "Operações",
                "acao": "Offset",
                "valor": 5.0,
                "is_operation_var": False,
            },
        ]
    }


def test_salvar_historico_json_sucesso_grava_arquivo_valido(pipelines_teste, tmp_path):
    # 1. ARRANGE
    caminho_json = tmp_path / "historico.json"

    # 2. ACT
    sucesso, erro = salvar_historico_processamento(str(caminho_json), pipelines_teste)

    # 3. ASSERT
    assert sucesso is True
    assert erro == ""
    assert caminho_json.exists()

    # Lê de volta e valida os dados
    with open(caminho_json, "r", encoding="utf-8") as f:
        dados_carregados = json.load(f)
    assert dados_carregados == pipelines_teste


def test_salvar_historico_txt_sucesso_escreve_formato_estruturado(
    pipelines_teste, tmp_path
):
    # 1. ARRANGE
    caminho_txt = tmp_path / "historico.txt"

    # 2. ACT
    sucesso, erro = salvar_historico_processamento(str(caminho_txt), pipelines_teste)

    # 3. ASSERT
    assert sucesso is True
    assert erro == ""
    assert caminho_txt.exists()

    # Valida conteúdo textual escrito
    conteudo = caminho_txt.read_text(encoding="utf-8")
    assert "Histórico de Processamento" in conteudo
    assert "Arquivo: arquivo1" in conteudo
    assert "--- TRATAMENTO DE DADOS ---" in conteudo
    assert "[1] Recorte Temporal" in conteudo
    assert "Inicio: 0.0" in conteudo
    assert "Fim: 10.0" in conteudo
    assert "--- OPERAÇÕES ---" in conteudo
    assert "[1] Offset" in conteudo
    assert "Valor: 5.0" in conteudo


def test_salvar_historico_falha_caminho_invalido_retorna_erro_io(pipelines_teste):
    # 1. ARRANGE
    # Diretório que não existe de forma alguma
    caminho_invalido = "/diretorio_inexistente_com_certeza/historico.json"

    # 2. ACT
    sucesso, erro = salvar_historico_processamento(caminho_invalido, pipelines_teste)

    # 3. ASSERT
    assert sucesso is False
    assert "Erro ao exportar histórico" in erro
