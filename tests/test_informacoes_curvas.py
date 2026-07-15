import pytest
import numpy as np
from processamento.informacoes_curvas import AnaliseCurva


def test_analise_curva_fluxo_normal():
    # 1. ARRANGE
    t = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    y = np.array([1.0, 3.0, 2.0, -1.0, 0.0])

    # 2. ACT
    analise = AnaliseCurva(t, y)
    v_max, x_max = analise.valor_maximo()
    v_min, x_min = analise.valor_minimo()
    fs = analise.taxa_amostragem()
    amp = analise.amplitude()
    tot, val = analise.num_amostras()
    rms = analise.rms_curva()
    res = analise.resumo()

    # 3. ASSERT
    assert v_max == 3.0
    assert x_max == 0.1
    assert v_min == -1.0
    assert x_min == 0.3
    assert fs == pytest.approx(10.0)
    assert amp == 4.0
    assert tot == 5
    assert val == 5
    assert rms == pytest.approx(np.sqrt(np.mean(y**2)))
    assert res["valor_maximo"] == 3.0
    assert res["x_no_maximo"] == 0.1
    assert res["valor_minimo"] == -1.0
    assert res["x_no_minimo"] == 0.3
    assert res["amplitude"] == 4.0
    assert res["taxa_amostragem"] == pytest.approx(10.0)
    assert res["total_amostras"] == 5
    assert res["amostras_validas"] == 5


def test_analise_curva_vazio():
    # 1. ARRANGE
    t = np.array([])
    y = np.array([])

    # 2. ACT
    analise = AnaliseCurva(t, y)
    v_max, x_max = analise.valor_maximo()
    v_min, x_min = analise.valor_minimo()
    fs = analise.taxa_amostragem()
    amp = analise.amplitude()
    tot, val = analise.num_amostras()
    rms = analise.rms_curva()
    res = analise.resumo()

    # 3. ASSERT
    assert v_max is None
    assert x_max is None
    assert v_min is None
    assert x_min is None
    assert fs is None
    assert amp is None
    assert tot == 0
    assert val == 0
    assert rms == 0.0
    assert res["rms"] == 0.0
    assert res["x_minimo"] is None
    assert res["x_maximo"] is None


def test_analise_curva_tudo_nan():
    # 1. ARRANGE
    t = np.array([0.0, 1.0, 2.0])
    y = np.array([np.nan, np.nan, np.nan])

    # 2. ACT
    analise = AnaliseCurva(t, y)
    v_max, x_max = analise.valor_maximo()
    v_min, x_min = analise.valor_minimo()
    fs = analise.taxa_amostragem()
    amp = analise.amplitude()
    tot, val = analise.num_amostras()
    rms = analise.rms_curva()
    res = analise.resumo()

    # 3. ASSERT
    assert v_max is None
    assert x_max is None
    assert v_min is None
    assert x_min is None
    assert fs is None
    assert amp is None
    assert tot == 3
    assert val == 0
    assert rms == 0.0
    assert res["rms"] == 0.0


def test_analise_curva_com_nans():
    # 1. ARRANGE
    t = np.array([0.0, 0.5, 1.0, 1.5])
    y = np.array([2.0, np.nan, -1.0, np.nan])

    # 2. ACT
    analise = AnaliseCurva(t, y)
    v_max, x_max = analise.valor_maximo()
    v_min, x_min = analise.valor_minimo()
    fs = analise.taxa_amostragem()
    amp = analise.amplitude()
    tot, val = analise.num_amostras()
    rms = analise.rms_curva()

    # 3. ASSERT
    assert v_max == 2.0
    assert x_max == 0.0
    assert v_min == -1.0
    assert x_min == 1.0
    assert fs == pytest.approx(
        1.0
    )  # diffs_positivos de [0.0, 1.0] -> diff de 1.0 -> fs = 1.0
    assert amp == 3.0
    assert tot == 4
    assert val == 2
    assert rms == pytest.approx(np.sqrt((2.0**2 + (-1.0) ** 2) / 2.0))


def test_analise_curva_taxa_amostragem_constante_ou_decrescente():
    # 1. ARRANGE
    t1 = np.array([1.0, 1.0, 1.0])
    y1 = np.array([1.0, 2.0, 3.0])
    t2 = np.array([3.0, 2.0, 1.0])
    y2 = np.array([1.0, 2.0, 3.0])

    # 2. ACT
    analise1 = AnaliseCurva(t1, y1)
    fs1 = analise1.taxa_amostragem()

    analise2 = AnaliseCurva(t2, y2)
    fs2 = analise2.taxa_amostragem()

    # 3. ASSERT
    assert fs1 is None
    assert fs2 is None


def test_analise_curva_um_ponto():
    # 1. ARRANGE
    t = np.array([1.5])
    y = np.array([2.5])

    # 2. ACT
    analise = AnaliseCurva(t, y)
    v_max, x_max = analise.valor_maximo()
    fs = analise.taxa_amostragem()
    tot, val = analise.num_amostras()
    rms = analise.rms_curva()

    # 3. ASSERT
    assert v_max == 2.5
    assert x_max == 1.5
    assert fs is None
    assert tot == 1
    assert val == 1
    assert rms == 2.5
