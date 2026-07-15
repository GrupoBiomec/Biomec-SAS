import pytest
import numpy as np
import pandas as pd
from processamento.operacoes import (
    calcular_media_movel,
    calcular_linha_referencia,
    interpolacao_linear,
    interpolacao_spline,
    interpolacao_media,
    operar_variaveis,
    operar_trigonometria,
    operar_calculo_escalar,
    agrupar_pontos_3d,
    operar_angulo_3d,
)

# --- Media Movel ---


def test_calcular_media_movel_fluxo_normal():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], name="sinal")

    # 2. ACT
    res, nome = calcular_media_movel(x, y, janela=3)

    # 3. ASSERT
    assert nome == "Média Móvel (sinal)"
    # np.convolve mode='same' com kernel [1/3, 1/3, 1/3]:
    # padding com zeros implícito ou padding de bordas por convolução normal:
    # para y = [1, 2, 3, 4, 5], no ponto index=1: (1+2+3)/3 = 2.0
    assert res.iloc[1] == pytest.approx(2.0)
    assert res.iloc[2] == pytest.approx(3.0)
    assert res.iloc[3] == pytest.approx(4.0)


def test_calcular_media_movel_limites():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0])
    y = pd.Series([1.0, 2.0], name="sinal")

    # 2. ACT & 3. ASSERT
    # Janela <= 0 deve disparar ValueError
    with pytest.raises(
        ValueError, match="A janela para média móvel deve ser maior que zero."
    ):
        calcular_media_movel(x, y, janela=0)

    # Janela maior que os dados deve ser limitada ao tamanho dos dados
    res, _ = calcular_media_movel(x, y, janela=5)
    assert len(res) == 2
    # Com janela=2 (limitada): convolve y com [0.5, 0.5] modo same
    assert res.iloc[0] == 0.5
    assert res.iloc[1] == 1.5


def test_calcular_media_movel_vazio():
    # 1. ARRANGE
    x = pd.Series(dtype=float)
    y = pd.Series(dtype=float, name="sinal")

    # 2. ACT
    res, nome = calcular_media_movel(x, y, janela=3)

    # 3. ASSERT
    assert len(res) == 0
    assert nome == "Média Móvel (sinal)"


# --- Linha de Referencia ---


def test_calcular_linha_referencia_normal():
    # 1. ARRANGE
    x = pd.Series([1.0, 2.0, 3.0], index=[10, 20, 30])
    coefs = [1.0, 2.0, 0.5]  # y = 1 + 2*x + 0.5*x^2

    # 2. ACT
    res, nome = calcular_linha_referencia(x, coefs)

    # 3. ASSERT
    assert nome == "Ref: Polinômio(grau 2)"
    # Para x = 1: 1 + 2 + 0.5 = 3.5
    # Para x = 2: 1 + 4 + 2 = 7.0
    # Para x = 3: 1 + 6 + 4.5 = 11.5
    assert res.loc[10] == 3.5
    assert res.loc[20] == 7.0
    assert res.loc[30] == 11.5


def test_calcular_linha_referencia_coefs_vazio():
    # 1. ARRANGE
    x = pd.Series([1.0, 2.0, 3.0])
    coefs = []

    # 2. ACT
    res, nome = calcular_linha_referencia(x, coefs)

    # 3. ASSERT
    assert nome == "Ref: Polinômio(grau -1)"
    # Soma de gerador vazio é 0, então deve criar série preenchida com 0
    assert (res == 0).all()


# --- Interpolacoes ---


def test_interpolacoes():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0, 2.0, 3.0])
    y = pd.Series([2.0, np.nan, np.nan, 8.0], name="sinal")

    # 2. ACT
    res_lin, nome_lin = interpolacao_linear(x, y)
    res_med, nome_med = interpolacao_media(x, y)

    # 3. ASSERT
    assert nome_lin == "Interp_Linear(sinal)"
    # Linear: 2.0 -> 4.0 -> 6.0 -> 8.0
    assert res_lin.iloc[1] == 4.0
    assert res_lin.iloc[2] == 6.0

    assert nome_med == "Interp_Media(sinal)"
    # Média: (2.0 + 8.0)/2 = 5.0
    assert res_med.iloc[1] == 5.0
    assert res_med.iloc[2] == 5.0


def test_interpolacao_spline():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])
    y = pd.Series([1.0, np.nan, 9.0, np.nan, 25.0], name="sinal")  # y = (x+1)^2

    # 2. ACT
    res_spl, nome_spl = interpolacao_spline(x, y, order=2)

    # 3. ASSERT
    assert nome_spl == "Interp_Spline(sinal)"
    # Spline grau 2 deve interpolar perfeitamente x=1 -> 4.0, x=3 -> 16.0
    assert res_spl.iloc[1] == pytest.approx(4.0)
    assert res_spl.iloc[3] == pytest.approx(16.0)


def test_interpolacao_spline_falha_poucos_pontos():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0])
    y = pd.Series([1.0, np.nan], name="sinal")

    # 2. ACT & 3. ASSERT
    # Spline de ordem 2 requer pelo menos 3 pontos válidos
    with pytest.raises((ValueError, TypeError, Exception)):
        interpolacao_spline(x, y, order=2)


# --- Operar Variaveis ---


def test_operar_variaveis_aritmetica():
    # 1. ARRANGE
    a = pd.Series([10.0, 20.0])
    b = pd.Series([2.0, 4.0])

    # 2. ACT & 3. ASSERT
    res_soma, err = operar_variaveis(a, b, 0)
    assert err is None and (res_soma == [12.0, 24.0]).all()

    res_sub, err = operar_variaveis(a, b, 1)
    assert err is None and (res_sub == [8.0, 16.0]).all()

    res_mult, err = operar_variaveis(a, b, 2)
    assert err is None and (res_mult == [20.0, 80.0]).all()

    res_div, err = operar_variaveis(a, b, 3)
    assert err is None and (res_div == [5.0, 5.0]).all()


def test_operar_variaveis_divisao_zero():
    # 1. ARRANGE
    a = pd.Series([10.0, 20.0])

    # 2. ACT
    # Divisão por constante zero
    res_const, err_const = operar_variaveis(a, 0.0, 3)
    # Divisão por série que contém zero
    res_ser, err_ser = operar_variaveis(a, pd.Series([2.0, 0.0]), 3)

    # 3. ASSERT
    assert res_const is None
    assert err_const == "Divisão por zero não é permitida."

    assert (
        err_ser is None
    )  # Não retorna erro na assinatura se for série, mas gera inf/nan
    assert res_ser.iloc[0] == 5.0
    assert np.isinf(res_ser.iloc[1])


def test_operar_variaveis_invalidos():
    # 1. ARRANGE
    a = pd.Series([1.0])
    b = pd.Series([2.0])

    # 2. ACT
    res_invalid, err_invalid = operar_variaveis(a, b, 99)
    res_error, err_error = operar_variaveis(a, "texto_invalido_operando", 0)

    # 3. ASSERT
    assert res_invalid is None
    assert err_invalid == "Operação inválida."

    assert res_error is None
    assert "Erro na operação aritmética" in err_error


# --- Operar Trigonometria ---


def test_operar_trigonometria_unidades():
    # 1. ARRANGE
    graus = pd.Series([0.0, 90.0, 180.0])
    rads = pd.Series([0.0, np.pi / 2, np.pi])

    # 2. ACT & 3. ASSERT
    res_deg, err1 = operar_trigonometria(graus, "seno", unidade="deg")
    assert err1 is None
    assert res_deg.iloc[1] == pytest.approx(1.0)

    res_rad, err2 = operar_trigonometria(rads, "cosseno", unidade="rad")
    assert err2 is None
    assert res_rad.iloc[1] == pytest.approx(0.0)

    res_tan, err3 = operar_trigonometria(rads, "tangente", unidade="rad")
    assert err3 is None
    assert res_tan.iloc[0] == pytest.approx(0.0)


def test_operar_trigonometria_invalidos():
    # 1. ARRANGE
    valores = pd.Series([0.0])

    # 2. ACT
    res_op, err_op = operar_trigonometria(valores, "invalida")
    res_val, err_val = operar_trigonometria(pd.Series(["nao_numerico"]), "seno")

    # 3. ASSERT
    assert res_op is None
    assert err_op == "Operação trigonométrica inválida."

    assert res_val is None
    assert "Erro no cálculo trigonométrico" in err_val


# --- Operar Calculo Escalar ---


def test_operar_calculo_escalar_integral_e_derivadas():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0, 2.0, 3.0])
    y = pd.Series([1.0, 2.0, 1.0, 2.0])

    # 2. ACT
    res_int, err_int = operar_calculo_escalar(x, y, "integral")
    res_der1, err_der1 = operar_calculo_escalar(x, y, "derivada_1")
    res_der2, err_der2 = operar_calculo_escalar(x, y, "derivada_2")

    # 3. ASSERT
    # Integral acumulada (método trapezoidal):
    # Áreas individuais: (1+2)/2 * 1 = 1.5; (2+1)/2 * 1 = 1.5; (1+2)/2 * 1 = 1.5
    # Acumulado: [0.0, 1.5, 3.0, 4.5]
    assert err_int is None
    assert list(res_int.values) == [0.0, 1.5, 3.0, 4.5]

    # Derivada 1 (np.gradient):
    # index 0: (2 - 1)/1 = 1.0
    # index 1: (1 - 1)/2 = 0.0
    assert err_der1 is None
    assert res_der1.iloc[0] == pytest.approx(1.0)
    assert res_der1.iloc[1] == pytest.approx(0.0)

    # Derivada 2:
    assert err_der2 is None
    assert len(res_der2) == 4


def test_operar_calculo_escalar_modulo_inverso_raiz():
    # 1. ARRANGE
    x = pd.Series([0.0, 1.0, 2.0])
    y = pd.Series([-4.0, 0.0, 9.0])

    # 2. ACT
    res_mod, err_mod = operar_calculo_escalar(x, y, "modulo")
    res_inv, err_inv = operar_calculo_escalar(x, y, "inverso")
    res_sqrt, err_sqrt = operar_calculo_escalar(x, y, "raiz_quadrada")

    # 3. ASSERT
    assert err_mod is None
    assert list(res_mod.values) == [4.0, 0.0, 9.0]

    assert err_inv is None
    assert res_inv.iloc[0] == -0.25
    assert np.isnan(res_inv.iloc[1])  # Divisao por zero vira NaN
    assert res_inv.iloc[2] == pytest.approx(1.0 / 9.0)

    assert err_sqrt is None
    assert np.isnan(res_sqrt.iloc[0])  # Negativos viram NaN
    assert res_sqrt.iloc[1] == 0.0
    assert res_sqrt.iloc[2] == 3.0


def test_operar_calculo_escalar_edge_cases():
    # 1. ARRANGE
    x_vazio = pd.Series(dtype=float)
    y_vazio = pd.Series(dtype=float)
    x_um = pd.Series([1.0])
    y_um = pd.Series([5.0])
    x_dois = pd.Series([1.0, 2.0])
    y_dois = pd.Series([5.0, 6.0])

    # 2. ACT
    # Vazios
    res_vazio, err_vazio = operar_calculo_escalar(x_vazio, y_vazio, "integral")

    # 1 ponto integral
    res_int_um, err_int_um = operar_calculo_escalar(x_um, y_um, "integral")
    # 1 ponto derivada 1
    res_der1_um, err_der1_um = operar_calculo_escalar(x_um, y_um, "derivada_1")
    # 2 pontos derivada 2
    res_der2_dois, err_der2_dois = operar_calculo_escalar(x_dois, y_dois, "derivada_2")

    # 3. ASSERT
    assert len(res_vazio) == 0
    assert err_vazio is None

    assert list(res_int_um.values) == [0.0]
    assert err_int_um is None

    assert res_der1_um is None
    assert "São necessários pelo menos 2 pontos" in err_der1_um

    assert res_der2_dois is None
    assert "São necessários pelo menos 3 pontos" in err_der2_dois


# --- Agrupar Pontos 3D ---


def test_agrupar_pontos_3d():
    # 1. ARRANGE
    cols = [
        "Membro_X [mm]",
        "Membro_Y [mm]",
        "Membro_Z [mm]",  # Grupo completo 1
        "Joelho.x",
        "Joelho.y",
        "Joelho.z",  # Grupo completo 2
        "Incompleto_X",
        "Incompleto_Y",  # Grupo incompleto
        "OutroSinal",  # Sem correspondência
    ]

    # 2. ACT
    pontos = agrupar_pontos_3d(cols)

    # 3. ASSERT
    assert "Membro" in pontos
    assert pontos["Membro"] == {
        "x": "Membro_X [mm]",
        "y": "Membro_Y [mm]",
        "z": "Membro_Z [mm]",
    }
    assert "Joelho" in pontos
    assert pontos["Joelho"] == {"x": "Joelho.x", "y": "Joelho.y", "z": "Joelho.z"}
    assert "Incompleto" not in pontos
    assert "OutroSinal" not in pontos


# --- Operar Angulo 3D ---


def test_operar_angulo_3d_relativo():
    # 1. ARRANGE
    # Definindo um ângulo reto (90 graus)
    # p1 = (1, 0, 0), vertice = (0, 0, 0), p3 = (0, 1, 0)
    df = pd.DataFrame(
        {
            "p1_x": [1.0],
            "p1_y": [0.0],
            "p1_z": [0.0],
            "v_x": [0.0],
            "v_y": [0.0],
            "v_z": [0.0],
            "p3_x": [0.0],
            "p3_y": [1.0],
            "p3_z": [0.0],
        }
    )
    pontos = {
        "p1": {"x": "p1_x", "y": "p1_y", "z": "p1_z"},
        "vertice": {"x": "v_x", "y": "v_y", "z": "v_z"},
        "p3": {"x": "p3_x", "y": "p3_y", "z": "p3_z"},
    }

    # 2. ACT
    res, err = operar_angulo_3d(df, "relativo", pontos, unidade="graus")

    # 3. ASSERT
    assert err is None
    assert res.iloc[0] == pytest.approx(90.0)


def test_operar_angulo_3d_vetores():
    # 1. ARRANGE
    # Dois vetores paralelos (0 graus): v1 = (1, 0, 0) e v2 = (1, 0, 0)
    df = pd.DataFrame(
        {
            "v1_ini_x": [0.0],
            "v1_ini_y": [0.0],
            "v1_ini_z": [0.0],
            "v1_fim_x": [1.0],
            "v1_fim_y": [0.0],
            "v1_fim_z": [0.0],
            "v2_ini_x": [0.0],
            "v2_ini_y": [0.0],
            "v2_ini_z": [0.0],
            "v2_fim_x": [2.0],
            "v2_fim_y": [0.0],
            "v2_fim_z": [0.0],
        }
    )
    pontos = {
        "p1_ini": {"x": "v1_ini_x", "y": "v1_ini_y", "z": "v1_ini_z"},
        "p1_fim": {"x": "v1_fim_x", "y": "v1_fim_y", "z": "v1_fim_z"},
        "p2_ini": {"x": "v2_ini_x", "y": "v2_ini_y", "z": "v2_ini_z"},
        "p2_fim": {"x": "v2_fim_x", "y": "v2_fim_y", "z": "v2_fim_z"},
    }

    # 2. ACT
    res, err = operar_angulo_3d(df, "vetores", pontos, unidade="radianos")

    # 3. ASSERT
    assert err is None
    assert res.iloc[0] == pytest.approx(0.0)


def test_operar_angulo_3d_zero_magnitude():
    # 1. ARRANGE
    # Um dos vetores tem magnitude zero (coincide no mesmo ponto)
    df = pd.DataFrame(
        {
            "p1_x": [0.0],
            "p1_y": [0.0],
            "p1_z": [0.0],
            "v_x": [0.0],
            "v_y": [0.0],
            "v_z": [0.0],
            "p3_x": [0.0],
            "p3_y": [0.0],
            "p3_z": [0.0],
        }
    )
    pontos = {
        "p1": {"x": "p1_x", "y": "p1_y", "z": "p1_z"},
        "vertice": {"x": "v_x", "y": "v_y", "z": "v_z"},
        "p3": {"x": "p3_x", "y": "p3_y", "z": "p3_z"},
    }

    # 2. ACT
    res, err = operar_angulo_3d(df, "relativo", pontos, unidade="graus")

    # 3. ASSERT
    assert err is None
    assert np.isnan(
        res.iloc[0]
    )  # Magnitude zero deve resultar em NaN no cosseno/angulo


def test_operar_angulo_3d_invalidos():
    # 1. ARRANGE
    df = pd.DataFrame({"a": [1.0]})
    pontos = {}

    # 2. ACT
    res_mode, err_mode = operar_angulo_3d(df, "modo_invalido", pontos, unidade="graus")
    res_err, err_err = operar_angulo_3d(df, "relativo", pontos, unidade="graus")

    # 3. ASSERT
    assert res_mode is None
    assert err_mode == "Modo de ângulo desconhecido."

    assert res_err is None
    assert "Erro no cálculo do ângulo 3D" in err_err
