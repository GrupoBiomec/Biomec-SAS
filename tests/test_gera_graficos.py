import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from processamento.gera_graficos import GeradorGraficos, JanelaConfig


@pytest.fixture
def mock_plot_widget():
    """Fixture para mockar o PlotWidget e sub-elementos do pyqtgraph."""
    widget = MagicMock()

    # Mock do plotItem
    plot_item = MagicMock()
    plot_item.legend = MagicMock()
    plot_item.vb = MagicMock()
    widget.plotItem = plot_item

    # Mock do ViewBox
    view_box = MagicMock()
    widget.getViewBox.return_value = view_box

    # Mock do Eixo
    axis = MagicMock()
    widget.getAxis.return_value = axis

    return widget


def test_converter_para_array(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    series_input = pd.Series([1.0, 2.0, 3.0])
    list_input = [1.0, 2.0, 3.0]
    array_input = np.array([1.0, 2.0, 3.0])

    # 2. Act
    res_series = gerador._converter_para_array(series_input)
    res_list = gerador._converter_para_array(list_input)
    res_array = gerador._converter_para_array(array_input)

    # 3. Assert
    assert isinstance(res_series, np.ndarray)
    assert np.array_equal(res_series, np.array([1.0, 2.0, 3.0]))
    assert isinstance(res_list, np.ndarray)
    assert np.array_equal(res_list, np.array([1.0, 2.0, 3.0]))
    assert isinstance(res_array, np.ndarray)
    assert np.array_equal(res_array, array_input)


def test_normalizar_dados(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    dados = np.array([1.0, 2.0, 3.0])

    # 2. Act
    res_minmax = gerador.normalizar_dados(dados, metodo="minmax")
    res_zscore = gerador.normalizar_dados(dados, metodo="zscore")

    # 3. Assert
    # MinMax deve mapear [1, 2, 3] para [0, 0.5, 1]
    assert np.array_equal(res_minmax, np.array([0.0, 0.5, 1.0]))

    # Z-Score deve subtrair a média (2) e dividir pelo desvio padrão (0.816...)
    assert np.allclose(res_zscore, np.array([-1.22474487, 0.0, 1.22474487]))


def test_normalizar_dados_array_constante(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    dados = np.array([5.0, 5.0, 5.0])

    # 2. Act
    res_minmax = gerador.normalizar_dados(dados, metodo="minmax")

    # 3. Assert
    # Array constante deve retornar tudo zero para evitar divisão por zero
    assert np.array_equal(res_minmax, np.array([0.0, 0.0, 0.0]))


def test_aplicar_operacao_matematica(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    dados = np.array([-4.0, 9.0, 16.0])

    # 2. Act
    res_abs = gerador.aplicar_operacao(dados, "abs")
    res_sqrt = gerador.aplicar_operacao(dados, "sqrt")
    res_square = gerador.aplicar_operacao(dados, "square")

    # 3. Assert
    assert np.array_equal(res_abs, np.array([4.0, 9.0, 16.0]))
    assert np.array_equal(res_square, np.array([16.0, 81.0, 256.0]))
    # Raiz de número negativo (-4.0) deve retornar NaN, enquanto os outros retornam 3.0 e 4.0
    assert np.isnan(res_sqrt[0])
    assert res_sqrt[1] == 3.0
    assert res_sqrt[2] == 4.0


def test_limpar_reseta_estado_plot(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    gerador.curvas_ativas = [MagicMock(), MagicMock()]

    # 2. Act
    gerador.limpar()

    # 3. Assert
    mock_plot_widget.clear.assert_called_once()
    mock_plot_widget.plotItem.vb.enableAutoRange.assert_called_once_with(axis="xy")
    mock_plot_widget.plotItem.legend.clear.assert_called_once()
    mock_plot_widget.hideAxis.assert_any_call("right")
    mock_plot_widget.hideAxis.assert_any_call("top")
    assert gerador.curvas_ativas == []


def test_plotar_linha_adiciona_curva_corretamente(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    dados_x = [0.0, 1.0, 2.0]
    dados_y = [10.0, 20.0, 30.0]
    config = {
        "titulo": "Meu Grafico",
        "label_x": "Tempo",
        "label_y": "Sinal",
        "nome_legenda": "Sinal A",
        "cor": "r",
        "espessura": 3,
    }

    # Mock legend to be None to test addLegend call
    mock_plot_widget.plotItem.legend = None

    # Mock return value of plot() to represent a curve
    mock_curve = MagicMock()
    mock_plot_widget.plot.return_value = mock_curve

    # 2. Act
    curva_retornada = gerador.plotar_linha(dados_x, dados_y, config)

    # 3. Assert
    mock_plot_widget.setTitle.assert_called_once_with("Meu Grafico")
    mock_plot_widget.setLabel.assert_any_call("bottom", "Tempo")
    mock_plot_widget.setLabel.assert_any_call("left", "Sinal")
    mock_plot_widget.addLegend.assert_called_once()

    # Verifica que chamou plot com os arrays corretos e parâmetros de caneta (pen)
    mock_plot_widget.plot.assert_called_once()
    call_args, call_kwargs = mock_plot_widget.plot.call_args
    assert np.array_equal(call_args[0], np.array([0.0, 1.0, 2.0]))
    assert np.array_equal(call_args[1], np.array([10.0, 20.0, 30.0]))
    assert call_kwargs["name"] == "Sinal A"

    assert curva_retornada is mock_curve
    assert mock_curve in gerador.curvas_ativas


def test_plotar_scatter_adiciona_item_corretamente(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    dados_x = [0.0, 1.0, 2.0]
    dados_y = [10.0, 20.0, 30.0]
    config = {
        "titulo": "Meu Dispersao",
        "label_x": "X",
        "label_y": "Y",
        "nome_legenda": "Pontos A",
        "cor": "g",
    }

    # 2. Act
    with patch("processamento.gera_graficos.pg.ScatterPlotItem") as MockScatter:
        mock_scatter_item = MagicMock()
        MockScatter.return_value = mock_scatter_item
        gerador.plotar_scatter(dados_x, dados_y, config)

        # 3. Assert
        MockScatter.assert_called_once()
        _, scatter_kwargs = MockScatter.call_args
        assert scatter_kwargs["name"] == "Pontos A"
        assert scatter_kwargs["brush"] == "g"
        mock_plot_widget.addItem.assert_called_once_with(mock_scatter_item)
        assert mock_scatter_item in gerador.curvas_ativas


def test_plotar_barras_adiciona_item_corretamente(mock_plot_widget):
    # 1. Arrange
    gerador = GeradorGraficos(mock_plot_widget)
    categorias = ["Cat A", "Cat B"]
    valores = [5.0, 10.0]
    config = {
        "titulo": "Barras",
        "label_x": "Categorias",
        "label_y": "Valores",
        "cor": "b",
    }

    # 2. Act
    with patch("processamento.gera_graficos.pg.BarGraphItem") as MockBar:
        mock_bar_item = MagicMock()
        MockBar.return_value = mock_bar_item
        gerador.plotar_barras(categorias, valores, config)

        # 3. Assert
        MockBar.assert_called_once()
        mock_plot_widget.addItem.assert_called_once_with(mock_bar_item)
        mock_plot_widget.getAxis.assert_called_once_with("bottom")


def test_janela_config_sugestao_unidades():
    # 1. Arrange
    mock_instance = MagicMock()
    mock_instance.unidades_colunas = {"sinal_forca": "N", "sinal_emg": "uV"}

    # 2. Act
    # Testa _obter_unidade
    un_forca = JanelaConfig._obter_unidade(mock_instance, "sinal_forca")
    un_tempo_heuristica = JanelaConfig._obter_unidade(mock_instance, "tempo_ciclo")
    un_frame_heuristica = JanelaConfig._obter_unidade(mock_instance, "frame")
    un_desconhecida = JanelaConfig._obter_unidade(mock_instance, "variavel_x")

    # Testa _formatar_coluna
    fmt_forca = JanelaConfig._formatar_coluna(mock_instance, "sinal_forca")
    fmt_desconhecida = JanelaConfig._formatar_coluna(mock_instance, "variavel_x")

    assert fmt_forca == "sinal_forca [N]"
    assert fmt_desconhecida == "variavel_x"


def test_plotar_sinais_sobrepostos_caso_1_conflito_total(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)

    # 3 sinais com eixos X ou Y diferentes para forçar conflito total
    sinais = [
        {
            "x_data": [1, 2],
            "y_data": [10, 20],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "r",
            "nome": "EMG",
            "tipo": "Dispersão",
        },
        {
            "x_data": [1, 2],
            "y_data": [100, 200],
            "x_unit": "m",
            "y_unit": "N",
            "cor": "g",
            "nome": "Força",
            "tipo": "Linha",
        },
        {
            "x_data": [1, 2],
            "y_data": [1, 2],
            "x_unit": "deg",
            "y_unit": "m",
            "cor": "b",
            "nome": "Posição",
            "tipo": "Linha",
        },
    ]

    # 2. ACT
    gerador.plotar_sinais_sobrepostos(
        sinais, "Título Teste", None, tendencia_visual=True
    )

    # 3. ASSERT
    mock_plot_widget.setTitle.assert_called_once_with(
        "Comparação de Tendência (Sem Escala Unificada)"
    )
    mock_plot_widget.setLabel.assert_any_call("bottom", "")
    mock_plot_widget.setLabel.assert_any_call("left", "")
    # Deve plotar as 2 linhas e adicionar 1 scatter plot
    assert mock_plot_widget.plot.call_count == 2
    assert mock_plot_widget.addItem.call_count == 1


def test_plotar_sinais_sobrepostos_caso_2_identico(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)
    sinais = [
        {
            "x_data": [1, 2],
            "y_data": [10, 20],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "r",
            "nome": "EMG1",
            "label_x": "Tempo",
            "tipo": "Dispersão",
        },
        {
            "x_data": [1, 2],
            "y_data": [15, 25],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "g",
            "nome": "EMG2",
            "label_x": "Tempo",
            "tipo": "Linha",
        },
    ]

    # 2. ACT
    gerador.plotar_sinais_sobrepostos(sinais, "Título Idêntico", None)

    # 3. ASSERT
    mock_plot_widget.setTitle.assert_called_once_with("Título Idêntico")
    mock_plot_widget.setLabel.assert_any_call("bottom", "Tempo (s)")
    mock_plot_widget.setLabel.assert_any_call("left", "Valores (V)")
    assert mock_plot_widget.plot.call_count == 1
    assert mock_plot_widget.addItem.call_count == 1


def test_plotar_sinais_sobrepostos_caso_3_conflito_y(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)
    # X comum (s), Ys diferentes (V e N)
    sinais = [
        {
            "x_data": [1, 2],
            "y_data": [10, 20],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "r",
            "nome": "EMG_disp",
            "label_x": "Tempo",
            "tipo": "Dispersão",
        },
        {
            "x_data": [1, 2],
            "y_data": [12, 22],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "g",
            "nome": "EMG_line",
            "label_x": "Tempo",
            "tipo": "Linha",
        },
        {
            "x_data": [1, 2],
            "y_data": [100, 200],
            "x_unit": "s",
            "y_unit": "N",
            "cor": "b",
            "nome": "Forca_disp",
            "label_x": "Tempo",
            "tipo": "Dispersão",
        },
        {
            "x_data": [1, 2],
            "y_data": [110, 210],
            "x_unit": "s",
            "y_unit": "N",
            "cor": "y",
            "nome": "Forca_line",
            "label_x": "Tempo",
            "tipo": "Linha",
        },
    ]

    mock_scene = MagicMock()
    mock_plot_widget.scene.return_value = mock_scene

    mock_vb = MagicMock()
    mock_plot_widget.getViewBox.return_value = mock_vb

    mock_axis = MagicMock()
    mock_plot_widget.getAxis.return_value = mock_axis

    # 2. ACT & 3. ASSERT
    with patch("processamento.gera_graficos.pg.ViewBox") as MockViewBox:
        mock_vb_extra = MagicMock()
        MockViewBox.return_value = mock_vb_extra
        gerador.plotar_sinais_sobrepostos(sinais, "Conflito Y", None)

        # O ViewBox secundário deve ter recebido 2 itens (uma curva e um scatter)
        assert mock_vb_extra.addItem.call_count == 2

    mock_plot_widget.setLabel.assert_any_call("bottom", "Tempo (s)")
    mock_plot_widget.setLabel.assert_any_call("left", "Valores (V)", color="k")
    mock_plot_widget.setLabel.assert_any_call("right", "Valores (N)", color="k")
    mock_scene.addItem.assert_called_once()
    mock_axis.linkToView.assert_called_once()


def test_plotar_sinais_sobrepostos_caso_4_conflito_x(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)
    # Y comum (V), Xs diferentes (s e frames)
    sinais = [
        {
            "x_data": [1, 2],
            "y_data": [10, 20],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "r",
            "nome": "EMG_x1_disp",
            "tipo": "Dispersão",
        },
        {
            "x_data": [1, 2],
            "y_data": [12, 22],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "g",
            "nome": "EMG_x1_line",
            "tipo": "Linha",
        },
        {
            "x_data": [10, 20],
            "y_data": [15, 25],
            "x_unit": "frames",
            "y_unit": "V",
            "cor": "b",
            "nome": "EMG_x2_disp",
            "tipo": "Dispersão",
        },
        {
            "x_data": [10, 20],
            "y_data": [17, 27],
            "x_unit": "frames",
            "y_unit": "V",
            "cor": "y",
            "nome": "EMG_x2_line",
            "tipo": "Linha",
        },
    ]

    mock_scene = MagicMock()
    mock_plot_widget.scene.return_value = mock_scene
    mock_vb = MagicMock()
    mock_plot_widget.getViewBox.return_value = mock_vb
    mock_axis = MagicMock()
    mock_plot_widget.getAxis.return_value = mock_axis

    # 2. ACT & 3. ASSERT
    with patch("processamento.gera_graficos.pg.ViewBox") as MockViewBox:
        mock_vb_extra = MagicMock()
        MockViewBox.return_value = mock_vb_extra
        gerador.plotar_sinais_sobrepostos(sinais, "Conflito X", None)

        # O ViewBox secundário deve ter recebido 2 itens
        assert mock_vb_extra.addItem.call_count == 2

    mock_plot_widget.setLabel.assert_any_call("left", "Valores (V)")
    mock_plot_widget.setLabel.assert_any_call("bottom", "X (s)", color="k")
    mock_plot_widget.setLabel.assert_any_call("top", "X (frames)", color="k")
    mock_scene.addItem.assert_called_once()
    mock_axis.linkToView.assert_called_once()


def test_plotar_sinais_sobrepostos_com_linhas_referencia(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)
    sinais = [
        {
            "x_data": [1, 2],
            "y_data": [10, 20],
            "x_unit": "s",
            "y_unit": "V",
            "cor": "r",
            "nome": "EMG",
        }
    ]

    # Configuração geral contendo referências coletadas
    config_geral = {
        "_linhas_referencia_coletadas": [
            {
                "titulo": "Média Ref",
                "dados_y": [15, 15],
                "cor": "g",
                "ativo": True,
                "_x_data": [1, 2],
            },
            {"titulo": "Inativa Ref", "dados_y": [2, 2], "cor": "b", "ativo": False},
        ]
    }

    # 2. ACT
    gerador.plotar_sinais_sobrepostos(
        sinais, "Com Refs", None, config_geral=config_geral
    )

    # 3. ASSERT
    # Duas plots: uma para o sinal principal 'EMG' e uma para a referência ativa 'Média Ref'
    assert mock_plot_widget.plot.call_count == 2
    # Verifica que chamou plot com os dados da referência ativa
    args_list = mock_plot_widget.plot.call_args_list
    ref_call = [call for call in args_list if call[1].get("name") == "Média Ref"]
    assert len(ref_call) == 1
    assert np.array_equal(ref_call[0][0][0], np.array([1, 2]))
    assert np.array_equal(ref_call[0][0][1], np.array([15, 15]))


def test_set_zoom_mode(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)
    mock_vb = MagicMock()
    mock_plot_widget.getViewBox.return_value = mock_vb

    # 2. ACT (Ativa Zoom)
    gerador.set_zoom_mode(True)
    # 3. ASSERT
    from pyqtgraph import ViewBox

    mock_vb.setMouseMode.assert_called_once_with(ViewBox.RectMode)

    # 4. ACT (Desativa Zoom)
    gerador.set_zoom_mode(False)
    # 5. ASSERT
    mock_vb.setMouseMode.assert_any_call(ViewBox.PanMode)
    mock_plot_widget.autoRange.assert_called_once()


def test_on_zoom_changed_filtra_legenda(mock_plot_widget):
    # 1. ARRANGE
    gerador = GeradorGraficos(mock_plot_widget)

    # Mock de legenda
    mock_legend = MagicMock()
    mock_legend.items = []
    mock_plot_widget.plotItem.legend = mock_legend

    # Mock view range: X de 0 a 10, Y de 0 a 10
    mock_plot_widget.plotItem.viewRange.return_value = [[0, 10], [0, 10]]

    # Curva 1: Totalmente visível (pontos dentro do range)
    curva_visivel = MagicMock()
    curva_visivel.name.return_value = "Curva Visível"
    curva_visivel.getData.return_value = (np.array([2, 3]), np.array([5, 6]))

    # Curva 2: Fora do range (X > 10)
    curva_invisivel = MagicMock()
    curva_invisivel.name.return_value = "Curva Invisível"
    curva_invisivel.getData.return_value = (np.array([12, 13]), np.array([5, 6]))

    gerador.curvas_ativas = [curva_visivel, curva_invisivel]

    # 2. ACT
    gerador._on_zoom_changed()

    # 3. ASSERT
    mock_legend.addItem.assert_called_once_with(curva_visivel, "Curva Visível")
    mock_legend.removeItem.assert_called_once_with(curva_invisivel)


def test_janela_config_instantiation():
    import sys
    from PyQt6.QtWidgets import QApplication

    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        _app = QApplication.instance()  # noqa: F841
    df = pd.DataFrame({"tempo": [0.0, 1.0], "sinal": [10.0, 20.0]})
    dialog = JanelaConfig(df, unidade_y_default="V", unidades_colunas={"sinal": "V"})
    assert dialog is not None
    assert dialog.combo_x.count() == 2
    assert dialog.combo_y.count() == 3  # blank + tempo + sinal


def test_janela_filtro_methods():
    import sys
    from PyQt6.QtWidgets import QApplication, QMessageBox

    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        _app = QApplication.instance()  # noqa: F841

    from processamento.gera_graficos import JanelaFiltro
    import pandas as pd
    import numpy as np

    dados_x = pd.Series(np.linspace(0, 1, 100))
    dados_y = pd.Series(
        np.sin(2 * np.pi * 5 * dados_x) + 0.1 * np.random.normal(size=100)
    )

    # 1. Instantiate passa_baixa filter window
    dialog = JanelaFiltro(
        tipo_filtro="passa_baixa",
        dados_x=dados_x,
        dados_y=dados_y,
        fs=100.0,
        unidade_x="s",
        unidade_y="V",
        titulo_grafico="Sinal de EMG",
    )

    # Test _executar_filtro success
    resultado, erro = dialog._executar_filtro()
    assert erro is None
    assert len(resultado) == 100

    # Test with rectification (abs value)
    dialog.check_retificar.setChecked(True)
    resultado_rect, erro_rect = dialog._executar_filtro()
    assert erro_rect is None
    # Filters (like Butterworth filtfilt) can yield slight undershoot (negative values) at signal boundaries
    # due to transient/ringing effects. We assert that the rectification happened by checking that
    # the mean is positive (> 0.5) whereas the unrectified filtered signal is near 0.
    assert resultado_rect.mean() > 0.5

    # Test _executar_filtro with error (Mocked Exception)
    dialog._filtro_passa_baixa = MagicMock(side_effect=Exception("Erro Simulado"))
    resultado_err, erro_err = dialog._executar_filtro()
    assert erro_err == "Erro Simulado"
    assert resultado_err is None

    # Reset helper mock
    del dialog._filtro_passa_baixa
    from processamento.limpeza import filtro_passa_baixa

    dialog._filtro_passa_baixa = filtro_passa_baixa
    dialog.spin_fc.setValue(5.0)

    # 2. Test _atualizar_preview
    dialog._atualizar_preview()
    assert dialog.resultado_y is not None
    assert dialog.label_status.text() == ""

    # Trigger error preview
    dialog._filtro_passa_baixa = MagicMock(side_effect=Exception("Erro Simulado"))
    dialog._atualizar_preview()
    assert dialog.resultado_y is None
    assert "Erro Simulado" in dialog.label_status.text()

    # Reset valid
    del dialog._filtro_passa_baixa
    dialog._filtro_passa_baixa = filtro_passa_baixa
    dialog.spin_fc.setValue(5.0)
    dialog._atualizar_preview()

    # 3. Test _toggle_antes_depois
    dialog.btn_toggle.setChecked(True)
    dialog._toggle_antes_depois()
    assert dialog._mostrando_original is True
    assert dialog.btn_toggle.text() == "👁 Mostrar Prévia"

    dialog.btn_toggle.setChecked(False)
    dialog._toggle_antes_depois()
    assert dialog._mostrando_original is False
    assert dialog.btn_toggle.text() == "👁 Mostrar Original"

    # 4. Test _calcular_winter success
    dialog._calcular_fc_winter = MagicMock(return_value=(6.0, None, None))
    dialog._calcular_winter()
    dialog._calcular_fc_winter.assert_called_once()
    assert dialog.spin_fc.value() == 6.0

    # Test Winter method throwing ValueError
    dialog._calcular_fc_winter = MagicMock(
        side_effect=ValueError("Erro no calculo de Winter")
    )
    with patch.object(QMessageBox, "warning") as mock_warn:
        dialog._calcular_winter()
        mock_warn.assert_called_once_with(dialog, "Aviso", "Erro no calculo de Winter")

    # Test get_resultado
    res = dialog.get_resultado()
    assert res["fc"] == 6.0
    assert res["ordem"] == 4
    assert res["tipo"] == "passa_baixa"


def test_janela_offset_calculations():
    import sys
    from PyQt6.QtWidgets import QApplication

    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        _app = QApplication.instance()  # noqa: F841

    from processamento.gera_graficos import JanelaOffset
    import pandas as pd
    import numpy as np

    df = pd.DataFrame(
        {
            "tempo": [0.0, 1.0, 2.0, 3.0, 4.0],
            "sinal_a": [10.0, 11.0, np.nan, 13.0, 14.0],
            "sinal_b": [20.0, 21.0, 22.0, np.nan, 24.0],
        }
    )

    dialog = JanelaOffset(
        df=df, colunas_selecionadas=["sinal_a", "sinal_b"], col_tempo="tempo"
    )

    # Check initialization
    assert len(dialog.curvas_originais) == 2
    assert len(dialog.curvas_offset) == 2

    # 1. Test _executar_atualizacao_plot with offset = 2.0
    dialog.spin_offset.setValue(2.0)
    dialog._executar_atualizacao_plot()

    # Assert offset subtraction (ignoring NaNs)
    assert np.array_equal(dialog._y_refs["sinal_a"], np.array([8.0, 9.0, 11.0, 12.0]))
    assert np.array_equal(dialog._y_refs["sinal_b"], np.array([18.0, 19.0, 20.0, 22.0]))
    assert np.array_equal(
        dialog.curvas_offset["sinal_a"].yData, np.array([8.0, 9.0, 11.0, 12.0])
    )

    # 2. Test _mudar_eixo_x to Frames
    dialog.radio_frames.setChecked(True)
    dialog._mudar_eixo_x()
    assert dialog.curvas_offset["sinal_a"].xData is None

    dialog._executar_atualizacao_plot()
    assert np.array_equal(dialog.curvas_offset["sinal_a"].xData, np.array([0, 1, 2, 3]))

    # Test _mudar_eixo_x back to Tempo
    dialog.radio_tempo.setChecked(True)
    dialog._mudar_eixo_x()
    assert dialog.curvas_offset["sinal_a"].xData is None

    dialog._executar_atualizacao_plot()
    assert np.array_equal(dialog.curvas_offset["sinal_a"].xData, np.array([0, 1, 2, 3]))

    # Test get_resultados
    res = dialog.get_resultados()
    assert res["offset"] == 2.0
    assert res["sobrescrever"] is True


def test_janela_recorte_temporal_calculations():
    import sys
    from PyQt6.QtWidgets import QApplication

    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        _app = QApplication.instance()  # noqa: F841

    from processamento.gera_graficos import JanelaRecorteTemporal
    import pandas as pd

    df = pd.DataFrame(
        {
            "tempo": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            "sinal_a": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            "sinal_b": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0],
        }
    )

    categorias = ["Cat1", "Cat2"]
    colunas_por_cat = {"Cat1": ["sinal_a"], "Cat2": ["sinal_b"]}

    dialog = JanelaRecorteTemporal(
        df=df,
        categorias_selecionadas=categorias,
        colunas_por_cat=colunas_por_cat,
        col_tempo="tempo",
    )

    # 1. Test initial bounds check
    assert dialog.spin_ini.value() == 0.0
    assert dialog.spin_fim.value() == 5.0

    # Move line ini past line fim: should clamp
    dialog.linhas_inicio[0].setValue(6.0)
    dialog._on_linha_ini_movida(dialog.linhas_inicio[0])
    assert dialog.linhas_inicio[0].value() == 5.0
    assert dialog.spin_ini.value() == 5.0

    # Move line fim before line ini (1.0): should clamp
    dialog.linhas_inicio[0].setValue(1.0)
    dialog._on_linha_ini_movida(dialog.linhas_inicio[0])
    dialog.linhas_fim[0].setValue(0.5)
    dialog._on_linha_fim_movida(dialog.linhas_fim[0])
    assert dialog.linhas_fim[0].value() == 1.0
    assert dialog.spin_fim.value() == 1.0

    # 2. Test spinbox sync (move spin_fim first to avoid clamp of spin_ini)
    dialog.spin_fim.setValue(4.0)
    dialog._on_spin_fim_changed(4.0)
    assert dialog.linhas_fim[0].value() == 4.0

    dialog.spin_ini.setValue(2.0)
    dialog._on_spin_ini_changed(2.0)
    assert dialog.linhas_inicio[0].value() == 2.0

    # Clamp on higher spin_ini value
    dialog.spin_ini.setValue(4.5)
    dialog._on_spin_ini_changed(4.5)
    assert dialog.spin_ini.value() == 4.0

    # Reset to valid non-overlapping values before switching axis
    dialog.spin_ini.setValue(2.0)
    dialog._on_spin_ini_changed(2.0)

    # 3. Test _mudar_eixo_x to Frames and verify proportional scaling calculation
    dialog.radio_frames.setChecked(True)
    dialog._mudar_eixo_x()
    assert dialog.spin_ini.value() == 2.0
    assert dialog.spin_fim.value() == 4.0

    # Test get_resultados
    res = dialog.get_resultados()
    assert res["t_ini"] == 2.0
    assert res["t_fim"] == 4.0
    assert res["tipo_x"] == "Frames"
    assert res["deslocar_0"] is True


def test_gerador_graficos_linhas_referencia_range(mock_plot_widget):
    from processamento.gera_graficos import GeradorGraficos

    gerador = GeradorGraficos(mock_plot_widget)

    x = [0, 1, 2]
    y = [10, 20, 30]

    ref_line_1 = {
        "titulo": "Referência Linear",
        "dados_y": [100, 200, 300],
        "cor": "r",
        "ativo": True,
    }
    ref_line_2 = {
        "titulo": "Referência Inativa",
        "dados_y": [5, 5, 5],
        "cor": "g",
        "ativo": False,
    }

    config = {
        "linhas_referencia": [ref_line_1, ref_line_2],
        "cor": "b",
        "nome_legenda": "Original",
    }

    mock_plot_widget.plotItem.legend = None

    # 1. Test plotar_linha reference lines logic
    gerador.plotar_linha(x, y, config)
    assert mock_plot_widget.plot.call_count == 2
    mock_plot_widget.setYRange.assert_called_once_with(9.0, 31.0, padding=0)

    # Reset
    mock_plot_widget.plot.reset_mock()
    mock_plot_widget.setYRange.reset_mock()

    # 2. Test plotar_scatter reference lines logic
    gerador.plotar_scatter(x, y, config)
    assert mock_plot_widget.plot.call_count == 1
    mock_plot_widget.setYRange.assert_called_once_with(9.0, 31.0, padding=0)
