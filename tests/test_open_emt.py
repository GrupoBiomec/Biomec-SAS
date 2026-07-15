import pytest
import pandas as pd
from unittest.mock import patch
from arquivos.parsers.open_emt import TratamentoEMT


@pytest.fixture
def conteudo_emt_valido():
    """Fixture para fornecer o conteúdo textual de um arquivo EMT válido."""
    # 1. ARRANGE
    return (
        "BTS ASCII format\n"
        "Type: EMG\n"
        "Measure unit: V\n"
        "Sequences: 3\n"
        "Outro cabecalho: valor\n"
        "\n"
        "Item\tSinalA\tSinalB\n"
        "1\t0.123\t0.456\n"
        "2\t0.789\t1.011\n"
        "3\t1.213\t1.415\n"
    )


@pytest.fixture
def arquivo_emt_valido(conteudo_emt_valido, tmp_path):
    """Fixture que grava o conteúdo EMT válido em um arquivo temporário."""
    # 1. ARRANGE
    caminho_arquivo = tmp_path / "teste.emt"
    caminho_arquivo.write_text(conteudo_emt_valido, encoding="latin-1")
    return caminho_arquivo


def test_load_emt_file_sucesso_carrega_dataframe_e_limpa_dados(arquivo_emt_valido):
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT
    sucesso = leitor.load_emt_file(str(arquivo_emt_valido))

    # 3. ASSERT
    assert sucesso is True
    assert leitor.is_loaded() is True
    df = leitor.get_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert list(df.columns) == ["Item", "SinalA", "SinalB"]
    assert df["SinalA"].iloc[0] == 0.123


def test_load_emt_file_inexistente_retorna_false():
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT
    sucesso = leitor.load_emt_file("caminho_inexistente.emt")

    # 3. ASSERT
    assert sucesso is False
    assert leitor.is_loaded() is False


def test_get_header_info_extrai_metadados_corretamente(arquivo_emt_valido):
    # 1. ARRANGE
    leitor = TratamentoEMT()
    leitor.load_emt_file(str(arquivo_emt_valido))

    # 2. ACT
    header = leitor.get_header_info()

    # 3. ASSERT
    assert header is not None
    assert header["format"] == "BTS ASCII format"
    assert header["type"] == "EMG"
    assert header["measure_unit"] == "V"
    assert header["sequences"] == "3"


def test_get_file_info_retorna_dicionario_completo(arquivo_emt_valido):
    # 1. ARRANGE
    leitor = TratamentoEMT()
    leitor.load_emt_file(str(arquivo_emt_valido))

    # 2. ACT
    info = leitor.get_file_info()

    # 3. ASSERT
    assert info is not None
    assert info["nome_arqv"] == "teste.emt"
    assert info["linhas"] == 3
    assert info["colunas"] == 3
    assert info["type"] == "EMG"
    assert info["measure_unit"] == "V"


def test_open_emt_file_cancelado_pelo_usuario_retorna_false():
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT
    with patch(
        "arquivos.parsers.open_emt.QFileDialog.getOpenFileName", return_value=("", "")
    ):
        sucesso = leitor.open_emt_file()

    # 3. ASSERT
    assert sucesso is False


def test_open_emt_file_sucesso_abre_e_avisa_usuario(arquivo_emt_valido):
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT & 3. ASSERT
    with patch(
        "arquivos.parsers.open_emt.QFileDialog.getOpenFileName",
        return_value=(str(arquivo_emt_valido), "filter"),
    ):
        with patch("arquivos.parsers.open_emt.QMessageBox.information") as mock_msg:
            sucesso = leitor.open_emt_file()
            assert sucesso is True
            mock_msg.assert_called_once()


def test_open_emt_file_exception():
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT & 3. ASSERT
    with (
        patch(
            "arquivos.parsers.open_emt.QFileDialog.getOpenFileName",
            side_effect=Exception("Erro inesperado"),
        ),
        patch("arquivos.parsers.open_emt.QMessageBox.critical") as mock_critical,
    ):

        sucesso = leitor.open_emt_file()
        assert sucesso is False
        mock_critical.assert_called_once()


def test_get_file_info_not_loaded():
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT & 3. ASSERT
    assert leitor.get_file_info() is None


def test_get_header_info_caminho_vazio_ou_erro(tmp_path):
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT & 3. ASSERT
    # Caso 1: file_path vazio
    assert leitor.get_header_info() is None

    # Caso 2: arquivo inexistente que lança IOError ao abrir
    leitor.file_path = str(tmp_path / "nao_existe.emt")
    assert leitor.get_header_info() is None


def test_extrai_infos_sucesso_e_falha(arquivo_emt_valido):
    # 1. ARRANGE
    leitor = TratamentoEMT()

    # 2. ACT & 3. ASSERT (Falha)
    with patch.object(leitor, "open_emt_file", return_value=False):
        df, conteudo, cabecalho = leitor.extrai_infos()
        assert df is None
        assert conteudo is None
        assert cabecalho is None

    # (Sucesso)
    with (
        patch(
            "arquivos.parsers.open_emt.QFileDialog.getOpenFileName",
            return_value=(str(arquivo_emt_valido), "filter"),
        ),
        patch("arquivos.parsers.open_emt.QMessageBox.information"),
    ):
        df, conteudo, cabecalho = leitor.extrai_infos()
        assert isinstance(df, pd.DataFrame)
        assert conteudo["nome_arqv"] == "teste.emt"
        assert cabecalho["type"] == "EMG"
