import os
import tempfile
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from arquivos.exportadores.exp_graficos import exportar_graficos


@pytest.fixture
def mock_main_window_for_export():
    mw = MagicMock()

    # Mock Estado
    estado = MagicMock()
    estado.arquivo_ativo = "arquivo_teste"
    estado.grafico_ativo = "grafico_teste"

    # Mock dataframe and units
    df = pd.DataFrame({"tempo": [0.0, 1.0], "sinal": [1.0, 2.0]})
    estado.get_dataframe.return_value = df
    estado.get_unidades_colunas.return_value = {"tempo": "s", "sinal": "V"}
    estado.get_config_grafico.return_value = {
        "eixo_x": "tempo",
        "eixo_y": "sinal",
        "filtros_ativos": [],
    }
    mw.estado = estado

    # Mock widgets and helper elements
    mw.exibidor_graficos = MagicMock()

    # Grab mocks to return a dummy QPixmap-like object
    mock_pixmap = MagicMock()
    mock_pixmap.size.return_value.scale = MagicMock()

    mw.area_grafico = MagicMock()
    mw.area_grafico.grab.return_value = mock_pixmap

    mw.area_simultanea = MagicMock()
    mw.area_simultanea.grab.return_value = mock_pixmap

    return mw


def test_exportar_graficos_txt_sucesso(mock_main_window_for_export):
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        dest_txt = os.path.join(tmpdir, "output.txt")

        with (
            patch("arquivos.exportadores.exp_graficos.QFileDialog") as mock_fd,
            patch("arquivos.exportadores.exp_graficos.QMessageBox") as mock_mb,
        ):

            mock_fd.getSaveFileName.return_value = (dest_txt, "")

            # Executa a exportação
            exportar_graficos(mw, selecionados, "TXT")

            # Verificações
            assert os.path.exists(dest_txt)
            with open(dest_txt, "r", encoding="utf-8") as f:
                content = f.read()
                assert (
                    "--- Gráfico: grafico_teste (Arquivo: arquivo_teste) ---" in content
                )
                assert "Eixo X: tempo" in content
                assert "Eixo Y: sinal" in content

            mock_mb.information.assert_called_once()


def test_exportar_graficos_pdf_sucesso(mock_main_window_for_export):
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        dest_pdf = os.path.join(tmpdir, "output.pdf")

        with (
            patch("arquivos.exportadores.exp_graficos.QFileDialog") as mock_fd,
            patch("arquivos.exportadores.exp_graficos.QMessageBox") as mock_mb,
            patch("arquivos.exportadores.exp_graficos.QPdfWriter") as mock_pdf_writer,
            patch("arquivos.exportadores.exp_graficos.QPainter") as mock_painter,
        ):

            mock_fd.getSaveFileName.return_value = (dest_pdf, "")

            # Executa a exportação
            exportar_graficos(mw, selecionados, "PDF")

            # Verificações
            mock_fd.getSaveFileName.assert_called_once()
            mock_pdf_writer.assert_called_once_with(dest_pdf)
            mock_painter.assert_called_once()
            mock_mb.information.assert_called_once()


def test_exportar_graficos_cancelamento(mock_main_window_for_export):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]

    # 2. ACT
    with patch(
        "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
        return_value=("", ""),
    ):
        exportar_graficos(mw, selecionados, "TXT")

    # 3. ASSERT: Não deve abrir nenhuma caixa de informação ou erro
    mw.estado.get_dataframe.assert_not_called()


def test_exportar_graficos_extensao_automatico(mock_main_window_for_export, tmp_path):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]
    dest_sem_ext = str(tmp_path / "saida")
    dest_com_ext = dest_sem_ext + ".txt"

    # 2. ACT
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=(dest_sem_ext, ""),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.information"),
    ):
        exportar_graficos(mw, selecionados, "TXT")

    # 3. ASSERT: O arquivo deve ser salvo com a extensão correspondente
    assert os.path.exists(dest_com_ext)


def test_exportar_graficos_tipo_sobreposicao_e_simultanea(
    mock_main_window_for_export, tmp_path
):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    # Mistura sobreposição e exibição simultânea
    selecionados = [
        {
            "tipo_item": "sobreposicao",
            "arquivo": None,
            "grafico": "grafico_sobreposicao",
        },
        {"tipo_item": "simultanea", "arquivo": None, "grafico": "grafico_simultanea"},
    ]
    dest_pdf = str(tmp_path / "saida.pdf")

    # 2. ACT
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=(dest_pdf, ""),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.information"),
        patch("arquivos.exportadores.exp_graficos.QPdfWriter"),
        patch("arquivos.exportadores.exp_graficos.QPainter") as mock_painter,
    ):

        exportar_graficos(mw, selecionados, "PDF")

    # 3. ASSERT: Verifique se os componentes de tela corretos foram "grabbed"
    assert mw.area_simultanea.grab.call_count == 1
    assert mw.area_grafico.grab.call_count == 1


def test_exportar_graficos_multiplas_paginas_pdf(mock_main_window_for_export, tmp_path):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico1"},
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico2"},
    ]
    dest_pdf = str(tmp_path / "saida.pdf")

    # 2. ACT
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=(dest_pdf, ""),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.information"),
        patch("arquivos.exportadores.exp_graficos.QPdfWriter") as mock_writer_class,
        patch("arquivos.exportadores.exp_graficos.QPainter"),
    ):

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        exportar_graficos(mw, selecionados, "PDF")

    # 3. ASSERT: Para múltiplas páginas no PDF, newPage() deve ser invocado
    mock_writer.newPage.assert_called_once()


def test_exportar_graficos_com_filtros_e_calculado(
    mock_main_window_for_export, tmp_path
):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]
    dest_txt = str(tmp_path / "saida.txt")

    # Mock config com filtros ativos e dados_y_calc
    mw.estado.get_config_grafico.return_value = {
        "eixo_x": "tempo",
        "eixo_y": "sinal",
        "dados_y_calc": [10.0, 20.0],
        "filtros_ativos": [{"tipo": "filtro_teste", "ativo": True}],
        "unidade_x": "s",
        "unidade_y": "V",
    }

    # 2. ACT
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=(dest_txt, ""),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.information"),
        patch(
            "arquivos.exportadores.exp_graficos.recomputar_dados_com_filtros",
            return_value=[15.0, 25.0],
        ) as mock_recomp,
    ):

        exportar_graficos(mw, selecionados, "TXT")

    # 3. ASSERT: Verifique se a lógica de filtros e recomputar foi chamada
    mock_recomp.assert_called_once()
    assert os.path.exists(dest_txt)
    with open(dest_txt, "r", encoding="utf-8") as f:
        content = f.read()
        assert "RMS (Root Mean Square)" in content


def test_exportar_graficos_txt_vazio(mock_main_window_for_export):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    # Apenas itens não-normais que não geram dados de TXT
    selecionados = [
        {
            "tipo_item": "sobreposicao",
            "arquivo": None,
            "grafico": "grafico_sobreposicao",
        }
    ]

    # 2. ACT
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=("saida.txt", ""),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.warning") as mock_warn,
    ):

        exportar_graficos(mw, selecionados, "TXT")

    # 3. ASSERT: Deve avisar que o TXT ficaria vazio e abortar
    mock_warn.assert_called_once()


def test_exportar_graficos_formato_zip(mock_main_window_for_export, tmp_path):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]
    dest_zip = str(tmp_path / "saida.zip")

    # Escreve um arquivo dummy de PDF quando QPdfWriter for instanciado para o ZIP de teste
    def mock_pdf_writer_side_effect(path_pdf):
        with open(path_pdf, "wb") as f:
            f.write(b"dummy pdf data")
        return MagicMock()

    # 2. ACT
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=(dest_zip, ""),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.information"),
        patch(
            "arquivos.exportadores.exp_graficos.QPdfWriter",
            side_effect=mock_pdf_writer_side_effect,
        ),
        patch("arquivos.exportadores.exp_graficos.QPainter"),
    ):

        exportar_graficos(mw, selecionados, "ZIP")

    # 3. ASSERT: Arquivo ZIP gerado com o PDF e o TXT internos
    assert os.path.exists(dest_zip)
    import zipfile

    with zipfile.ZipFile(dest_zip, "r") as zipf:
        namelist = zipf.namelist()
        assert "graficos.pdf" in namelist
        assert "informacoes.txt" in namelist


def test_exportar_graficos_excecao(mock_main_window_for_export):
    # 1. ARRANGE
    mw = mock_main_window_for_export
    selecionados = [
        {"tipo_item": "normal", "arquivo": "arquivo_teste", "grafico": "grafico_teste"}
    ]

    # 2. ACT & 3. ASSERT
    # Dispara exceção de dentro do bloco try (por exemplo, ao usar o TemporaryDirectory)
    with (
        patch(
            "arquivos.exportadores.exp_graficos.QFileDialog.getSaveFileName",
            return_value=("saida.txt", ""),
        ),
        patch(
            "arquivos.exportadores.exp_graficos.tempfile.TemporaryDirectory",
            side_effect=Exception("Erro no sistema de arquivos"),
        ),
        patch("arquivos.exportadores.exp_graficos.QMessageBox.critical") as mock_crit,
    ):

        exportar_graficos(mw, selecionados, "TXT")
        mock_crit.assert_called_once()
