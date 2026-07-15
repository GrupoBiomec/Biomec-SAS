import pytest
from unittest.mock import MagicMock


# Função alvo a ser testada
def padronizar_janela(janela):
    janela.adjustSize()
    parent = janela.parentWidget()
    if parent:
        max_w = parent.width()
        max_h = parent.height()

        w = min(janela.width(), max_w)
        h = min(janela.height(), max_h)

        janela.resize(w, h)
        janela.setFixedSize(w, h)
    else:
        janela.setFixedSize(janela.size())


@pytest.fixture
def mock_parent():
    """Fixture para fornecer um objeto pai mockado com dimensões fixas."""
    # 1. ARRANGE
    parent = MagicMock()
    parent.width.return_value = 800
    parent.height.return_value = 600
    return parent


@pytest.fixture
def mock_janela(mock_parent):
    """Fixture para fornecer uma janela mockada vinculada a um pai."""
    # 1. ARRANGE
    janela = MagicMock()
    janela.parentWidget.return_value = mock_parent
    janela.width.return_value = 600
    janela.height.return_value = 400
    janela.size.return_value = MagicMock()
    return janela


def test_padronizar_janela_com_parent_menor_limita_tamanho_ao_parent(
    mock_janela, mock_parent
):
    # 1. ARRANGE
    # A janela solicita um tamanho maior (1000x800) que o pai (800x600)
    mock_janela.width.return_value = 1000
    mock_janela.height.return_value = 800

    # 2. ACT
    padronizar_janela(mock_janela)

    # 3. ASSERT
    # O tamanho deve ser limitado ao tamanho máximo do pai (800x600)
    mock_janela.resize.assert_called_once_with(800, 600)
    mock_janela.setFixedSize.assert_called_once_with(800, 600)


def test_padronizar_janela_com_parent_maior_mantem_tamanho_solicitado(mock_janela):
    # 1. ARRANGE
    # A janela solicita um tamanho menor (600x400) que o pai (800x600)
    mock_janela.width.return_value = 600
    mock_janela.height.return_value = 400

    # 2. ACT
    padronizar_janela(mock_janela)

    # 3. ASSERT
    # O tamanho solicitado deve ser mantido
    mock_janela.resize.assert_called_once_with(600, 400)
    mock_janela.setFixedSize.assert_called_once_with(600, 400)


def test_padronizar_janela_sem_parent_fixa_tamanho_atual():
    # 1. ARRANGE
    janela = MagicMock()
    janela.parentWidget.return_value = None
    tamanho_mock = MagicMock()
    janela.size.return_value = tamanho_mock

    # 2. ACT
    padronizar_janela(janela)

    # 3. ASSERT
    # Sem pai, a janela deve fixar seu tamanho atual
    janela.setFixedSize.assert_called_once_with(tamanho_mock)
