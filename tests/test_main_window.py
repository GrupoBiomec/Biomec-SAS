import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialog
import pandas as pd
from ui.main_window import MainWindow


@pytest.fixture
def mock_main_window():
    """Fixture para fornecer um objeto mockado da MainWindow com estado e árvore estruturados."""
    # 1. ARRANGE
    mw = MagicMock()

    # Mock do estado
    estado = MagicMock()
    estado.get_arquivos.return_value = {}
    estado.get_graficos.return_value = {}
    estado.get_sobreposicoes.return_value = {}
    estado.get_exibicoes_simultaneas.return_value = {}
    mw.estado = estado

    # Mock da árvore
    arvore = MagicMock()
    mw.arvore = arvore

    # Mock do exibidor de gráficos
    exibidor = MagicMock()
    mw.exibidor_graficos = exibidor

    return mw


def test_abrir_multiplas_curvas_sucesso_adiciona_sobreposicoes_e_evita_colisoes(
    mock_main_window,
):
    # 1. ARRANGE
    mw = mock_main_window
    nome_arquivo = "C1T1M-600KM-01.tdf"

    # Configurar arquivos no estado
    df_mock = pd.DataFrame({"sinal1": [1, 2], "sinal2": [3, 4]})
    arquivos = {
        nome_arquivo: {
            "dataframe": df_mock,
            "unidades_colunas": {"sinal1": "V", "sinal2": "N"},
        }
    }
    mw.estado.get_arquivos.return_value = arquivos

    # Simula que o arquivo ainda NÃO possui gráficos registrados (o que causaria KeyError anteriormente)
    mw.estado.get_graficos.side_effect = lambda name=None: (
        {} if name == nome_arquivo else {nome_arquivo: {}}
    )

    # Configura sobreposições existentes para forçar a renomeação da composição se houver conflito
    sobreposicoes = {"Curvas_Multiplas": {}}
    mw.estado.get_sobreposicoes.return_value = sobreposicoes
    mw.estado.get_exibicoes_simultaneas.return_value = {}

    with patch("ui.main_window.JanelaMultiplasCurvas") as MockJanela:
        janela_instance = MagicMock()
        janela_instance.exec.return_value = QDialog.DialogCode.Accepted
        # Seleção de variáveis de destino
        janela_instance.get_selecoes.return_value = {
            "eixo_x": "tempo",
            "eixo_y_lista": ["sinal1", "sinal2"],
            "nome": "Curvas_Multiplas",
        }
        MockJanela.return_value = janela_instance

        # 2. ACT
        # Chamamos o método da classe MainWindow passando nosso mock como self
        MainWindow._abrir_multiplas_curvas(mw, nome_arquivo)

        # 3. ASSERT
        # Deve ter adicionado duas configs de gráficos
        assert mw.estado.adicionar_config_grafico.call_count == 2

        # Como "Curvas_Multiplas" já existia no get_sobreposicoes, deve salvar como "Curvas_Multiplas_1"
        assert "Curvas_Multiplas_1" in sobreposicoes
        assert sobreposicoes["Curvas_Multiplas_1"]["titulo"] == "Curvas_Multiplas_1"

        # Verifica se atualizou a árvore e selecionou o novo item
        mw.arvore._atualizar_arvore_composicoes.assert_called_once()
        mw.arvore._selecionar_item_composicao.assert_called_once_with(
            "Curvas_Multiplas_1"
        )
        mw.exibidor_graficos._exibir_grafico_selecionado.assert_called_once()


def test_salvar_nova_variavel_com_plotar_auto_cria_e_seleciona_grafico(
    mock_main_window,
):
    # 1. ARRANGE
    mw = mock_main_window
    nome_arquivo = "arquivo_teste"
    resultado = {
        "nome": "sinal_novo",
        "valores": pd.Series([1.0, 2.0]),
        "unidade": "V",
        "nome_arquivo": nome_arquivo,
        "plotar_auto": True,
        "pipeline_step": {},
    }

    # Configure mock dataframe for the time column check
    df_mock = pd.DataFrame({"tempo": [0.0, 1.0]})
    mw.estado.get_dataframe.return_value = df_mock
    mw.estado.get_unidades_colunas.return_value = {"tempo": "s"}
    mw.estado.nome_existe.return_value = False
    mw.estado._salvar_nova_variavel.return_value = "sinal_novo"

    # Mock QMessageBox
    with patch("ui.main_window.QMessageBox") as mock_box:
        # 2. ACT
        MainWindow._salvar_nova_variavel(mw, resultado)

        # 3. ASSERT
        mw.estado._salvar_nova_variavel.assert_called_once_with(resultado)
        # Should add graph config
        mw.estado.adicionar_config_grafico.assert_called_once()
        mw.arvore._adicionar_grafico_na_arvore_de_arquivo.assert_called_once_with(
            nome_arquivo, "sinal_novo"
        )
        mw.arvore._selecionar_item_na_arvore.assert_called_once_with(
            nome_arquivo, "sinal_novo"
        )
        mw.exibidor_graficos._exibir_grafico_selecionado.assert_called_once()


def test_desfazer_ultima_operacao_com_graficos_associados_confirmacao_exclui_ambos(
    mock_main_window,
):
    # 1. ARRANGE
    mw = mock_main_window
    nome_arquivo = "arquivo_teste"
    nome_var = "sinal_para_excluir"

    # Configure mock combo selection
    mw._selecionar_arquivo_via_combo.return_value = nome_arquivo

    # Mock get_arquivo / pipeline to return the target variable
    pipeline = [{"is_operation_var": True, "variavel_gerada": nome_var}]
    mw.estado.get_arquivo.return_value = {"pipeline": pipeline}

    # Configure mock get_graficos to return a graph using that variable
    mw.estado.get_graficos.return_value = {
        "grafico_dependente": {
            "eixo_y": nome_var,
            "eixo_x": "tempo",
            "arvore": MagicMock(),
        }
    }

    # Mock QMessagebox to accept the deletion
    from PyQt6.QtWidgets import QMessageBox

    with patch("ui.main_window.QMessageBox") as mock_box:
        mock_box.question.return_value = QMessageBox.StandardButton.Yes
        mock_box.StandardButton = QMessageBox.StandardButton

        # 2. ACT
        MainWindow.desfazer_ultima_operacao(mw)

        # 3. ASSERT
        # Check confirmation prompt
        mock_box.question.assert_called_once()

        # Should remove the dependent graph
        mw.estado.remover_grafico.assert_called_once_with(
            nome_arquivo, "grafico_dependente"
        )

        # Should call desfazer_ultima_operacao on state
        mw.estado.desfazer_ultima_operacao.assert_called_once_with(nome_arquivo)


def test_desfazer_ultima_operacao_com_graficos_associados_cancelamento_mantem_ambos(
    mock_main_window,
):
    # 1. ARRANGE
    mw = mock_main_window
    nome_arquivo = "arquivo_teste"
    nome_var = "sinal_para_excluir"

    # Configure mock combo selection
    mw._selecionar_arquivo_via_combo.return_value = nome_arquivo

    # Mock get_arquivo / pipeline to return the target variable
    pipeline = [{"is_operation_var": True, "variavel_gerada": nome_var}]
    mw.estado.get_arquivo.return_value = {"pipeline": pipeline}

    # Configure mock get_graficos to return a graph using that variable
    mw.estado.get_graficos.return_value = {
        "grafico_dependente": {
            "eixo_y": nome_var,
            "eixo_x": "tempo",
            "arvore": MagicMock(),
        }
    }

    # Mock QMessageBox to reject the deletion
    from PyQt6.QtWidgets import QMessageBox

    with patch("ui.main_window.QMessageBox") as mock_box:
        mock_box.question.return_value = QMessageBox.StandardButton.No
        mock_box.StandardButton = QMessageBox.StandardButton

        # 2. ACT
        MainWindow.desfazer_ultima_operacao(mw)

        # 3. ASSERT
        # Check confirmation prompt
        mock_box.question.assert_called_once()

        # Should NOT remove the dependent graph
        mw.estado.remover_grafico.assert_not_called()

        # Should NOT call desfazer_ultima_operacao on state
        mw.estado.desfazer_ultima_operacao.assert_not_called()
