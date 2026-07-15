import pytest
import pandas as pd
import numpy as np
from processamento.limpeza import (
    filtro_passa_baixa,
    filtro_passa_alta,
    calcular_fc_winter,
    calcular_fs,
    recomputar_dados_com_filtros,
)


@pytest.fixture
def sinal_limpo_com_tempo():
    """Fixture para fornecer tempo e sinal limpos, sem NaNs."""
    # 1. ARRANGE
    t = np.linspace(0, 1, 100)  # fs = 99.0 Hz aprox (dt = 0.0101s)
    # Sinal senoidal de 5 Hz mais ruído de alta frequência
    y = np.sin(2 * np.pi * 5 * t) + 0.1 * np.sin(2 * np.pi * 35 * t)
    return pd.Series(t, name="tempo"), pd.Series(y, name="sinal")


@pytest.fixture
def sinal_com_nan(sinal_limpo_com_tempo):
    """Fixture que fornece um sinal contendo valores NaN."""
    # 1. ARRANGE
    t, y = sinal_limpo_com_tempo
    y_nan = y.copy()
    y_nan.iloc[10:20] = np.nan
    return t, y_nan


def test_calcular_fs_sinal_regular_calcula_frequencia_correta(sinal_limpo_com_tempo):
    # 1. ARRANGE
    t, _ = sinal_limpo_com_tempo

    # 2. ACT
    fs = calcular_fs(t.values)

    # 3. ASSERT
    assert fs == pytest.approx(99.0)


def test_filtro_passa_baixa_sucesso_atenua_alta_frequencia(sinal_limpo_com_tempo):
    # 1. ARRANGE
    t, y = sinal_limpo_com_tempo
    fs = calcular_fs(t.values)

    # 2. ACT
    res, nome_novo = filtro_passa_baixa(t, y, fc=10.0, fs=fs, order=4)

    # 3. ASSERT
    assert nome_novo == "Passa-Baixa(10.0Hz)(sinal)"
    assert len(res) == len(y)
    # O ruído de 35Hz deve ser amplamente atenuado; variabilidade deve diminuir
    assert res.std() < y.std()


def test_filtro_passa_baixa_corte_maior_nyquist_lanca_value_error(
    sinal_limpo_com_tempo,
):
    # 1. ARRANGE
    t, y = sinal_limpo_com_tempo
    fs = calcular_fs(t.values)
    # Nyquist = 49.5 Hz. fc = 50 Hz excede o limite.

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="deve ser menor que a frequência de Nyquist"):
        filtro_passa_baixa(t, y, fc=50.0, fs=fs, order=4)


def test_filtro_passa_alta_sucesso_remove_tendencia(sinal_limpo_com_tempo):
    # 1. ARRANGE
    t, y = sinal_limpo_com_tempo
    fs = calcular_fs(t.values)
    # Adiciona offset (tendência constante)
    y_com_offset = y + 5.0

    # 2. ACT
    res, nome_novo = filtro_passa_alta(t, y_com_offset, fc=2.0, fs=fs, order=4)

    # 3. ASSERT
    assert nome_novo == "Passa-Alta(2.0Hz)(sinal)"
    # Passa-alta deve remover a média constante (deslocando de volta próximo a zero)
    assert res.mean() == pytest.approx(0.0, abs=0.2)


def test_calcular_fc_winter_sucesso_retorna_frequencia_otima(sinal_limpo_com_tempo):
    # 1. ARRANGE
    t, y = sinal_limpo_com_tempo
    fs = calcular_fs(t.values)

    # 2. ACT
    fc_otima, fcs, residuos = calcular_fc_winter(
        y.values, fs=fs, order=4, fc_min=1.0, fc_step=0.5
    )

    # 3. ASSERT
    assert fc_otima > 0
    assert len(fcs) == len(residuos)
    assert fc_otima in fcs


def test_calcular_fc_winter_sem_dados_validos_lanca_value_error():
    # 1. ARRANGE
    dados_nan = np.array([np.nan, np.nan, np.nan])

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="O sinal não possui valores válidos"):
        calcular_fc_winter(dados_nan, fs=100.0)


def test_recomputar_dados_com_filtros_com_nan_e_retificacao(sinal_com_nan):
    # 1. ARRANGE
    t, y = sinal_com_nan
    fs = calcular_fs(t.values)

    # Primeiro testamos apenas a retificação (fc=None)
    filtros_retificacao_apenas = [
        {
            "tipo": "passa_baixa",
            "fc": None,
            "fs": fs,
            "ordem": 2,
            "retificar": True,
            "ativo": True,
        }
    ]

    # Segundo testamos retificação + filtragem (pode apresentar pequenos undershoots devido ao overshoot do filtro)
    filtros_completos = [
        {
            "tipo": "passa_baixa",
            "fc": 5.0,
            "fs": fs,
            "ordem": 2,
            "retificar": True,
            "ativo": True,
        }
    ]

    # 2. ACT
    resultado_retificado_apenas = recomputar_dados_com_filtros(
        t.values, y.values, filtros_retificacao_apenas
    )
    resultado_filtrado = recomputar_dados_com_filtros(
        t.values, y.values, filtros_completos
    )

    # 3. ASSERT
    # Apenas retificado: Todos os valores válidos devem ser estritamente não-negativos
    valores_retificados = resultado_retificado_apenas[
        ~np.isnan(resultado_retificado_apenas)
    ]
    assert (valores_retificados >= 0).all()

    # Com filtragem: NaNs originais na posição 10 a 20 devem ser mantidos nas posições originais
    assert np.isnan(resultado_filtrado[12])
    assert len(resultado_filtrado) == len(y)
