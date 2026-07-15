import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialog
from ui.exibe_graficos import ExibidorGraficos


@pytest.fixture
def mock_main_window():
    """Fixture para fornecer uma instância mockada de MainWindow com dependências de estado e árvore."""
    # 1. ARRANGE
    mw = MagicMock()

    # Mock do estado da aplicação
    estado = MagicMock()
    estado.get_arquivos.return_value = {}
    estado.get_graficos.return_value = {}
    estado.get_sobreposicoes.return_value = {}
    estado.get_exibicoes_simultaneas.return_value = {}
    mw.estado = estado

    # Mock do gerenciador de árvore
    arvore = MagicMock()
    mw.arvore = arvore

    return mw


def test_plotar_separadamente_extrai_graficos_ocultos_e_adiciona_na_arvore(
    mock_main_window,
):
    # 1. ARRANGE
    mw = mock_main_window
    exibidor = ExibidorGraficos(mw)
    nome_composicao = "Composição Teste"

    # Configura um gráfico fonte no estado de sobreposição
    config_sobreposicao = {
        "graficos_fonte": [{"arquivo": "teste.emt", "grafico": "sinal1"}]
    }
    mw.estado.get_sobreposicoes.return_value = {nome_composicao: config_sobreposicao}

    # Configura o gráfico como oculto ('hidden': True)
    graficos = {"teste.emt": {"sinal1": {"hidden": True}}}
    mw.estado.get_graficos.return_value = graficos

    # Mock para a janela de seleção e caixa de mensagens
    with (
        patch("ui.exibe_graficos.JanelaPlotarSeparadamente") as MockJanela,
        patch("ui.exibe_graficos.QMessageBox.information") as mock_info,
    ):

        instancia_janela = MagicMock()
        instancia_janela.exec.return_value = QDialog.DialogCode.Accepted
        instancia_janela.get_selecionados.return_value = ["teste.emt → sinal1"]
        MockJanela.return_value = instancia_janela

        # 2. ACT
        exibidor._plotar_separadamente(nome_composicao)

        # 3. ASSERT
        # O estado de visibilidade do gráfico deve ter sido atualizado para visível
        assert graficos["teste.emt"]["sinal1"]["hidden"] is False

        # Deve chamar _adicionar_grafico_na_arvore_de_arquivo com a assinatura correta (2 argumentos posicionais)
        mw.arvore._adicionar_grafico_na_arvore_de_arquivo.assert_called_once_with(
            "teste.emt", "sinal1"
        )

        # Deve ter notificado o usuário com uma mensagem
        mock_info.assert_called_once()
