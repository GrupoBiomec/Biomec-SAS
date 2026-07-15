import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from arquivos.projeto.salvar_projeto import (
    carregar_emt,
    carregar_tdf,
    salvar_projeto_sas,
    abrir_projeto_sas,
)


@pytest.fixture
def mock_main_window():
    """Fixture para fornecer um objeto MainWindow mockado com dependências estruturadas."""
    # 1. ARRANGE
    mw = MagicMock()

    # Mock do estado
    estado = MagicMock()
    estado.guarda_arquivos = {}
    estado.guarda_graficos = {}
    estado.guarda_sobreposicoes = {}
    estado.guarda_exibicoes_simultaneas = {}
    mw.estado = estado

    # Mocks dos leitores
    mw.leitorEMT = MagicMock()
    mw.leitorTDF = MagicMock()

    # Mocks da árvore com assinaturas simplificadas
    arvore = MagicMock()

    def mock_adicionar_arquivo(nome):
        return MagicMock()

    def mock_adicionar_grafico_na_arvore_de_arquivo(nome_arquivo, nome_grafico):
        return MagicMock()

    def mock_atualizar_arvore_composicoes():
        return MagicMock()

    arvore._adicionar_arquivo = mock_adicionar_arquivo
    arvore._adicionar_grafico_na_arvore_de_arquivo = (
        mock_adicionar_grafico_na_arvore_de_arquivo
    )
    arvore._atualizar_arvore_composicoes = mock_atualizar_arvore_composicoes
    mw.arvore = arvore

    return mw


def test_carregar_emt_sucesso_adiciona_arquivo_e_atualiza_arvore(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window
    df_mock = pd.DataFrame({"sinal": [1, 2, 3]})
    conteudo_mock = {"nome_arqv": "arquivo.emt"}
    cabecalho_mock = {"measure_unit": "V"}

    mw.leitorEMT.extrai_infos.return_value = (df_mock, conteudo_mock, cabecalho_mock)

    # 2. ACT
    carregar_emt(mw)

    # 3. ASSERT
    assert "arquivo.emt" in mw.estado.guarda_arquivos
    assert mw.arquivo_ativo == "arquivo.emt"
    # Verifica se os dados salvos estão corretos
    dados = mw.estado.guarda_arquivos["arquivo.emt"]
    assert dados["dataframe"] is df_mock
    assert dados["cabecalho"] == cabecalho_mock
    assert mw.estado.guarda_graficos["arquivo.emt"] == {}


def test_carregar_tdf_sucesso_adiciona_arquivo_e_unidades(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window
    df_mock = pd.DataFrame({"sinal": [1, 2, 3]})
    conteudo_mock = {"nome_arqv": "arquivo.tdf"}
    cabecalho_mock = {}
    unidades_mock = {"sinal": "N"}

    mw.leitorTDF.extrai_infos.return_value = (
        df_mock,
        conteudo_mock,
        cabecalho_mock,
        unidades_mock,
    )

    # 2. ACT
    carregar_tdf(mw)

    # 3. ASSERT
    assert "arquivo.tdf" in mw.estado.guarda_arquivos
    assert mw.arquivo_ativo == "arquivo.tdf"
    assert mw.estado.guarda_arquivos["arquivo.tdf"]["unidades_colunas"] == unidades_mock
    assert mw.estado.guarda_graficos["arquivo.tdf"] == {}


def test_salvar_projeto_sas_sucesso_chama_gerenciador_sas(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window
    caminho = "caminho/projeto.sas"

    # 2. ACT & 3. ASSERT
    with patch(
        "arquivos.projeto.salvar_projeto.QFileDialog.getSaveFileName",
        return_value=(caminho, "filter"),
    ):
        with patch(
            "arquivos.projeto.salvar_projeto.GerenciadorSAS.salvar_projeto"
        ) as mock_salvar:
            with patch(
                "arquivos.projeto.salvar_projeto.QMessageBox.information"
            ) as mock_msg:
                salvar_projeto_sas(mw)
                mock_salvar.assert_called_once_with(
                    caminho,
                    mw.estado.guarda_arquivos,
                    mw.estado.guarda_graficos,
                    mw.estado.guarda_sobreposicoes,
                    mw.estado.guarda_exibicoes_simultaneas,
                )
                mock_msg.assert_called_once()


def test_abrir_projeto_sas_sucesso_mescla_arquivos_e_graficos(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window
    caminho = "caminho/projeto.sas"

    # Mock do retorno de abrir_projeto contendo arquivos, gráficos e sobreposições
    ga_mock = {"arq1": {"dataframe": pd.DataFrame({"col": [1]}), "pipeline": []}}
    gg_mock = {"arq1": {"graf1": {"hidden": False}}}
    gs_mock = {}
    ges_mock = {}

    # 2. ACT & 3. ASSERT
    with patch(
        "arquivos.projeto.salvar_projeto.QFileDialog.getOpenFileName",
        return_value=(caminho, "filter"),
    ):
        with patch(
            "arquivos.projeto.salvar_projeto.GerenciadorSAS.abrir_projeto",
            return_value=(ga_mock, gg_mock, gs_mock, ges_mock),
        ):
            with patch(
                "arquivos.projeto.salvar_projeto.QMessageBox.information"
            ) as mock_msg:
                abrir_projeto_sas(mw)
                assert "arq1" in mw.estado.guarda_arquivos
                assert "arq1" in mw.estado.guarda_graficos
                mock_msg.assert_called_once()


def test_carregar_emt_limite_e_duplicado(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window

    # Caso 1: Limite de 50 arquivos
    mw.estado.guarda_arquivos = {f"arq{i}.emt": {} for i in range(50)}
    with patch("arquivos.projeto.salvar_projeto.QMessageBox.warning") as mock_warn:
        carregar_emt(mw)
        mock_warn.assert_called_once_with(
            mw,
            "Limite Atingido",
            "Você atingiu o limite de 50 arquivos abertos simultaneamente.",
        )

    # Caso 2: Arquivo duplicado
    mw.estado.guarda_arquivos = {"duplicado.emt": {}}
    mw.leitorEMT.extrai_infos.return_value = (
        pd.DataFrame(),
        {"nome_arqv": "duplicado.emt"},
        {},
    )
    with patch("arquivos.projeto.salvar_projeto.QMessageBox.warning") as mock_warn:
        carregar_emt(mw)
        mock_warn.assert_called_once_with(
            mw, "Arquivo Duplicado", "O arquivo 'duplicado.emt' já está aberto."
        )


def test_carregar_tdf_limite_duplicado_e_value_error(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window

    # Caso 1: Limite de 50 arquivos
    mw.estado.guarda_arquivos = {f"arq{i}.tdf": {} for i in range(50)}
    with patch("arquivos.projeto.salvar_projeto.QMessageBox.warning") as mock_warn:
        carregar_tdf(mw)
        mock_warn.assert_called_once_with(
            mw,
            "Limite Atingido",
            "Você atingiu o limite de 50 arquivos abertos simultaneamente.",
        )

    # Caso 2: ValueError ao extrair infos (sem dados válidos)
    mw.estado.guarda_arquivos = {}
    mw.leitorTDF.extrai_infos.side_effect = ValueError("Format error")
    with patch("arquivos.projeto.salvar_projeto.QMessageBox.warning") as mock_warn:
        carregar_tdf(mw)
        mock_warn.assert_called_once_with(
            mw,
            "Aviso",
            "Não foram identificados dados 3D, EMG ou de Plataforma de Força.",
        )

    # Caso 3: Arquivo duplicado
    mw.leitorTDF.extrai_infos.side_effect = None
    mw.leitorTDF.extrai_infos.return_value = (
        pd.DataFrame(),
        {"nome_arqv": "duplicado.tdf"},
        {},
        {},
    )
    mw.estado.guarda_arquivos = {"duplicado.tdf": {}}
    with patch("arquivos.projeto.salvar_projeto.QMessageBox.warning") as mock_warn:
        carregar_tdf(mw)
        mock_warn.assert_called_once_with(
            mw, "Arquivo Duplicado", "O arquivo 'duplicado.tdf' já está aberto."
        )


def test_salvar_projeto_sas_formatos_e_excecao(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window
    caminho_sem_ext = "caminho/projeto"

    # Caso 1: Salvar com sucesso sem extensão .sas no nome inicial
    with (
        patch(
            "arquivos.projeto.salvar_projeto.QFileDialog.getSaveFileName",
            return_value=(caminho_sem_ext, ""),
        ),
        patch(
            "arquivos.projeto.salvar_projeto.GerenciadorSAS.salvar_projeto"
        ) as mock_salvar,
        patch("arquivos.projeto.salvar_projeto.QMessageBox.information"),
    ):

        salvar_projeto_sas(mw)
        # Deve ter adicionado .sas
        mock_salvar.assert_called_once_with(
            "caminho/projeto.sas",
            mw.estado.guarda_arquivos,
            mw.estado.guarda_graficos,
            mw.estado.guarda_sobreposicoes,
            mw.estado.guarda_exibicoes_simultaneas,
        )

    # Caso 2: Exceção ao salvar
    with (
        patch(
            "arquivos.projeto.salvar_projeto.QFileDialog.getSaveFileName",
            return_value=("caminho/projeto.sas", ""),
        ),
        patch(
            "arquivos.projeto.salvar_projeto.GerenciadorSAS.salvar_projeto",
            side_effect=Exception("Permissão negada"),
        ),
        patch("arquivos.projeto.salvar_projeto.QMessageBox.critical") as mock_crit,
    ):

        salvar_projeto_sas(mw)
        mock_crit.assert_called_once()


def test_abrir_projeto_sas_colisoes_e_excecao(mock_main_window):
    # 1. ARRANGE
    mw = mock_main_window

    # Arquivo já aberto na interface
    mw.estado.guarda_arquivos = {"arq1": {"dados": 1}}
    mw.estado.guarda_sobreposicoes = {"sobre1": {}}
    mw.estado.guarda_exibicoes_simultaneas = {"simul1": {}}

    # Dados vindos do arquivo .sas a ser aberto
    ga_mock = {"arq1": {"dataframe": pd.DataFrame({"col": [1]})}}
    gg_mock = {"arq1": {"graf1": {"hidden": False}}}
    gs_mock = {"sobre1": {"graficos_fonte": [{"arquivo": "arq1"}]}}
    ges_mock = {"simul1": {"layout": [[{"arquivo": "arq1"}]]}}

    caminho = "projeto.sas"

    # 2. ACT
    with (
        patch(
            "arquivos.projeto.salvar_projeto.QFileDialog.getOpenFileName",
            return_value=(caminho, "filter"),
        ),
        patch(
            "arquivos.projeto.salvar_projeto.GerenciadorSAS.abrir_projeto",
            return_value=(ga_mock, gg_mock, gs_mock, ges_mock),
        ),
        patch("arquivos.projeto.salvar_projeto.QMessageBox.information") as mock_info,
    ):

        abrir_projeto_sas(mw)

    # 3. ASSERT
    # arq1 já existia, então deve ter sido renomeado para arq1_1
    assert "arq1" in mw.estado.guarda_arquivos
    assert "arq1_1" in mw.estado.guarda_arquivos

    # O gráfico de arq1 agora deve estar associado a arq1_1
    assert "arq1_1" in mw.estado.guarda_graficos
    assert "graf1" in mw.estado.guarda_graficos["arq1_1"]

    # As referências de arquivo em guarda_sobreposicoes e guarda_exibicoes_simultaneas devem ter sido remapeadas
    assert (
        mw.estado.guarda_sobreposicoes["sobre1_1"]["graficos_fonte"][0]["arquivo"]
        == "arq1_1"
    )
    assert (
        mw.estado.guarda_exibicoes_simultaneas["simul1_1"]["layout"][0][0]["arquivo"]
        == "arq1_1"
    )

    # E os nomes originais e remapeados devem estar presentes
    assert "sobre1" in mw.estado.guarda_sobreposicoes
    assert "sobre1_1" in mw.estado.guarda_sobreposicoes
    assert "simul1" in mw.estado.guarda_exibicoes_simultaneas
    assert "simul1_1" in mw.estado.guarda_exibicoes_simultaneas

    # Caso 2: Exceção ao abrir
    with (
        patch(
            "arquivos.projeto.salvar_projeto.QFileDialog.getOpenFileName",
            return_value=(caminho, ""),
        ),
        patch(
            "arquivos.projeto.salvar_projeto.GerenciadorSAS.abrir_projeto",
            side_effect=Exception("Arquivo corrompido"),
        ),
        patch("arquivos.projeto.salvar_projeto.QMessageBox.critical") as mock_crit,
    ):

        abrir_projeto_sas(mw)
        mock_crit.assert_called_once()
