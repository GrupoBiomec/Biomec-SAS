import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from arquivos.parsers.open_tdf import TratamentoTDF


@pytest.fixture
def mock_tdf_cinematica_e_emg():
    """Fixture para fornecer um mock do Tdf contendo dados 3D e EMG."""
    # 1. ARRANGE
    mock_tdf = MagicMock()

    # 1.1 Configura dados 3D
    mock_tdf.has_data3D = True
    mock_track = MagicMock()
    mock_track.label = "marcador"
    mock_track.X = np.array([1.0, 1.1, 1.2])
    mock_track.Y = np.array([2.0, 2.1, 2.2])
    mock_track.Z = np.array([3.0, 3.1, 3.2])

    mock_data3d = MagicMock()
    mock_data3d.nFrames = 3
    mock_data3d.frequency = 10.0
    mock_data3d.startTime = 0.0
    mock_data3d.tracks = [mock_track]
    mock_tdf.data3D = mock_data3d

    # 1.2 Configura dados EMG
    mock_tdf.has_emg = True
    mock_signal = MagicMock()
    mock_signal.label = "EMG1"
    mock_signal.data = np.array([0.05, 0.06, 0.07])

    mock_emg = MagicMock()
    mock_emg.nSamples = 3
    mock_emg.frequency = 10.0
    mock_emg.startTime = 0.0
    mock_emg.__iter__.return_value = [mock_signal]
    mock_tdf.emg = mock_emg

    # Sem forças
    mock_tdf.has_force_and_torque = False

    return mock_tdf


@pytest.fixture
def mock_tdf_plataforma():
    """Fixture para fornecer um mock do Tdf contendo dados da Plataforma de Força."""
    # 1. ARRANGE
    mock_tdf = MagicMock()
    mock_tdf.has_data3D = False
    mock_tdf.has_emg = False

    # Configura Força e Torque
    mock_tdf.has_force_and_torque = True
    mock_force_track = MagicMock()
    # plat.force: Nx3
    mock_force_track.force = np.array(
        [[10.0, 20.0, 30.0], [11.0, 21.0, 31.0], [12.0, 22.0, 32.0]]
    )
    # plat.application_point: Nx3
    mock_force_track.application_point = np.array(
        [[0.1, 0.2, 0.0], [0.11, 0.21, 0.0], [0.12, 0.22, 0.0]]
    )
    # plat.torque: Nx3
    mock_force_track.torque = np.array(
        [[0.0, 0.0, 5.0], [0.0, 0.0, 5.1], [0.0, 0.0, 5.2]]
    )

    mock_force = MagicMock()
    mock_force.nFrames = 3
    mock_force.frequency = 10.0
    mock_force.startTime = 0.0
    mock_force.tracks = [mock_force_track]
    mock_tdf.force_and_torque = mock_force

    return mock_tdf


def test_load_tdf_file_sucesso_carrega_e_mescla_cinematica_com_emg(
    mock_tdf_cinematica_e_emg, tmp_path
):
    # 1. ARRANGE
    # Cria arquivo fictício
    fake_file = tmp_path / "teste.tdf"
    fake_file.write_text("fake binary data")

    leitor = TratamentoTDF()

    # 2. ACT
    with patch("arquivos.parsers.open_tdf.Tdf", return_value=mock_tdf_cinematica_e_emg):
        sucesso = leitor.load_tdf_file(str(fake_file))

    # 3. ASSERT
    assert sucesso is True
    assert leitor.is_loaded() is True
    df = leitor.get_dataframe()
    assert isinstance(df, pd.DataFrame)

    # Colunas: frame, time, marcador_x, marcador_y, marcador_z, EMG1
    assert "frame" in df.columns
    assert "time" in df.columns
    assert "marcador_x" in df.columns
    assert "EMG1" in df.columns
    assert df["marcador_x"].iloc[0] == 1.0
    assert df["EMG1"].iloc[2] == 0.07

    # Unidades
    unidades = leitor.unidades_colunas
    assert unidades["marcador_x"] == "m"
    assert unidades["EMG1"] == "V"
    assert unidades["time"] == "s"

    # Testa get_file_info e get_header_info com dados carregados
    info = leitor.get_file_info()
    assert info is not None
    assert info["nome_arqv"] == "teste.tdf"
    assert info["linhas"] == 3
    assert info["colunas"] == 6

    header = leitor.get_header_info()
    assert header is not None
    assert "3D" in header["type"]
    assert "EMG" in header["type"]


def test_load_tdf_file_sucesso_carrega_plataforma_de_forca(
    mock_tdf_plataforma, tmp_path
):
    # 1. ARRANGE
    fake_file = tmp_path / "teste_plat.tdf"
    fake_file.write_text("fake binary data")

    leitor = TratamentoTDF()

    # 2. ACT
    with patch("arquivos.parsers.open_tdf.Tdf", return_value=mock_tdf_plataforma):
        sucesso = leitor.load_tdf_file(str(fake_file))

    # 3. ASSERT
    assert sucesso is True
    df = leitor.get_dataframe()
    # Colunas esperadas da plataforma: Plat0_Fx, Plat0_Fy, Plat0_Fz, Plat0_CoPx, Plat0_CoPy, Plat0_Tz
    assert "Plat0_Fx" in df.columns
    assert "Plat0_CoPx" in df.columns
    assert "Plat0_Tz" in df.columns
    assert df["Plat0_Fx"].iloc[0] == 10.0
    assert df["Plat0_Tz"].iloc[1] == 5.1


def test_load_tdf_file_inexistente_retorna_false():
    # 1. ARRANGE
    leitor = TratamentoTDF()

    # 2. ACT
    sucesso = leitor.load_tdf_file("caminho_inexistente.tdf")

    # 3. ASSERT
    assert sucesso is False


def test_parse_tdf_file_sem_dados_reconhecidos_lanca_value_error(tmp_path):
    # 1. ARRANGE
    fake_file = tmp_path / "vazio.tdf"
    fake_file.write_text("fake binary data")

    # Mock do Tdf que não tem nenhum bloco de dados ativo
    mock_tdf_vazio = MagicMock()
    mock_tdf_vazio.has_data3D = False
    mock_tdf_vazio.has_emg = False
    mock_tdf_vazio.has_force_and_torque = False
    mock_tdf_vazio.blocks = []

    leitor = TratamentoTDF()

    # 2. ACT & 3. ASSERT
    with patch("arquivos.parsers.open_tdf.Tdf", return_value=mock_tdf_vazio):
        with pytest.raises(
            ValueError,
            match="O arquivo TDF não contém dados 3D, EMG ou de Plataforma de Força",
        ):
            leitor.load_tdf_file(str(fake_file))


def test_open_tdf_file_cancelado_pelo_usuario_retorna_false():
    # 1. ARRANGE
    leitor = TratamentoTDF()

    # 2. ACT
    with patch(
        "arquivos.parsers.open_tdf.QFileDialog.getOpenFileName", return_value=("", "")
    ):
        sucesso = leitor.open_tdf_file()

    # 3. ASSERT
    assert sucesso is False


def test_open_tdf_file_sucesso():
    # 1. ARRANGE
    leitor = TratamentoTDF()

    # 2. ACT & 3. ASSERT
    with (
        patch(
            "arquivos.parsers.open_tdf.QFileDialog.getOpenFileName",
            return_value=("caminho/arquivo.tdf", "filter"),
        ),
        patch.object(leitor, "load_tdf_file", return_value=True) as mock_load,
        patch("arquivos.parsers.open_tdf.QMessageBox.information") as mock_msg,
    ):

        leitor.nome_arqv = "arquivo.tdf"
        sucesso = leitor.open_tdf_file()

        assert sucesso is True
        mock_load.assert_called_once_with("caminho/arquivo.tdf")
        mock_msg.assert_called_once()


def test_open_tdf_file_exception():
    # 1. ARRANGE
    leitor = TratamentoTDF()

    # 2. ACT & 3. ASSERT
    with (
        patch(
            "arquivos.parsers.open_tdf.QFileDialog.getOpenFileName",
            side_effect=Exception("Erro inesperado"),
        ),
        patch("arquivos.parsers.open_tdf.QMessageBox.critical") as mock_critical,
    ):

        sucesso = leitor.open_tdf_file()

        assert sucesso is False
        mock_critical.assert_called_once()


def test_get_file_info_and_header_info_not_loaded():
    # 1. ARRANGE
    leitor = TratamentoTDF()

    # 2. ACT & 3. ASSERT
    assert leitor.get_file_info() is None
    assert leitor.get_header_info() is None


def test_get_header_info_different_data_types(tmp_path):
    # 1. ARRANGE
    leitor = TratamentoTDF()
    leitor.file_path = "dummy.tdf"
    leitor.dataframe = pd.DataFrame()

    # Caso 1: 3D
    leitor.unidades_colunas = {"marcador_x": "m"}
    info = leitor.get_header_info()
    assert "3D" in info["type"]
    assert "EMG" not in info["type"]
    assert "Force" not in info["type"]

    # Caso 2: 3D + EMG + Force
    leitor.unidades_colunas = {"marcador_x": "m", "EMG1": "V", "Plat0_Fx": "N"}
    info = leitor.get_header_info()
    assert "3D" in info["type"]
    assert "EMG" in info["type"]
    assert "Force" in info["type"]

    # Caso 3: Desconhecido
    leitor.unidades_colunas = {"marcador_x": "kg"}
    info = leitor.get_header_info()
    assert info["type"] == "Unknown Data"


def test_extrai_infos_sucesso_e_falha():
    # 1. ARRANGE
    leitor = TratamentoTDF()

    # 2. ACT & 3. ASSERT (Falha)
    with patch.object(leitor, "open_tdf_file", return_value=False):
        df, info, header, unidades = leitor.extrai_infos()
        assert df is None
        assert info is None
        assert header is None
        assert unidades is None

    # (Sucesso)
    mock_df = pd.DataFrame()
    mock_info = {"linhas": 10}
    mock_header = {"format": "TDF"}
    mock_unidades = {"col": "m"}
    with (
        patch.object(leitor, "open_tdf_file", return_value=True),
        patch.object(leitor, "get_dataframe", return_value=mock_df),
        patch.object(leitor, "get_file_info", return_value=mock_info),
        patch.object(leitor, "get_header_info", return_value=mock_header),
    ):

        leitor.unidades_colunas = mock_unidades
        df, info, header, unidades = leitor.extrai_infos()
        assert df is mock_df
        assert info is mock_info
        assert header is mock_header
        assert unidades is mock_unidades


def test_obter_unidades_tdf():
    # 1. ARRANGE & 2. ACT
    unidades = TratamentoTDF._obter_unidades_tdf()

    # 3. ASSERT
    assert isinstance(unidades, dict)
    assert unidades["emg"] == "V"
    # Modificar o retorno não deve alterar a constante global/classe
    unidades["emg"] = "mV"
    assert TratamentoTDF._obter_unidades_tdf()["emg"] == "V"


def test_parse_tdf_file_fallback_plataforma_bruta(tmp_path):
    # 1. ARRANGE
    fake_file = tmp_path / "fallback.tdf"
    fake_file.write_text("fake binary data")

    from basictdf.tdfForcePlatformsData import ForcePlatformsDataBlock

    mock_tdf = MagicMock()
    mock_tdf.has_data3D = False
    mock_tdf.has_emg = False
    mock_tdf.has_force_and_torque = False

    # Configura o bloco bruto de plataforma
    mock_raw_block = MagicMock(spec=ForcePlatformsDataBlock)
    mock_raw_block.nBytes = 250
    mock_raw_block.n_frames = 3
    mock_raw_block.frequency = 1000.0
    mock_raw_block.start_time = 0.0

    mock_plat = MagicMock()
    mock_plat.force = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    mock_plat.application_point = np.array(
        [[0.1, 0.2, 0.0], [0.11, 0.21, 0.0], [0.12, 0.22, 0.0]]
    )
    mock_plat.torque = np.array([0.5, 0.6, 0.7])

    mock_raw_block._platforms = [mock_plat]
    mock_tdf.blocks = [mock_raw_block]

    leitor = TratamentoTDF()

    # 2. ACT
    with patch("arquivos.parsers.open_tdf.Tdf", return_value=mock_tdf):
        df, unidades = leitor._parse_tdf_file(str(fake_file))

    # 3. ASSERT
    assert "Plat0_Fx" in df.columns
    assert "Plat0_CoPx" in df.columns
    assert "Plat0_Tz" in df.columns
    assert df["Plat0_Fx"].iloc[1] == 4.0
    assert df["Plat0_Tz"].iloc[2] == 0.7
    assert unidades["Plat0_Fx"] == "N"
    assert unidades["Plat0_Tz"] == "N.m"
