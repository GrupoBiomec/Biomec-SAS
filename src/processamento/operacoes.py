import pandas as pd
import numpy as np


def calcular_media_movel(
    x: pd.Series, y: pd.Series, janela: int = 5
) -> tuple[pd.Series, str]:
    # calcula a Média Móvel Simples e ajusta os dados X
    if janela <= 0:
        raise ValueError("A janela para média móvel deve ser maior que zero.")

    y_nome = y.name if y.name is not None else "Y"
    novo_nome = f"Média Móvel ({y_nome})"

    if len(y) == 0:
        return pd.Series(dtype=float), novo_nome

    if janela > len(y):
        janela = len(y)

    # np.convolve modo 'same' retorna array do mesmo tamanho, com padding
    media_movel_y = np.convolve(y.values, np.ones(janela) / janela, mode="same")

    # cria a Série de resultado usando o índice original de X
    resultado_y = pd.Series(media_movel_y, index=x.index)

    return resultado_y, novo_nome


def calcular_linha_referencia(
    x: pd.Series, coeficientes: list[float]
) -> tuple[pd.Series, str]:
    """
    Gera uma linha de referência baseada num polinômio fornecido (y = c0 + c1*x + c2*x^2 ...)
    Alinhado perfeitamente ao Eixo X nativo do dataframe.
    """
    x_vals = x.values
    # y = c0*x^0 + c1*x^1 + c2*x^2 + ...
    y_vals = sum(coef * (x_vals**i) for i, coef in enumerate(coeficientes))

    resultado = pd.Series(y_vals, index=x.index)
    grau = len(coeficientes) - 1

    #  título
    novo_nome = f"Ref: Polinômio(grau {grau})"
    return resultado, novo_nome


def interpolacao_linear(x: pd.Series, y: pd.Series) -> tuple[pd.Series, str]:
    resultado = y.interpolate(method="linear")
    novo_nome = f"Interp_Linear({y.name})"
    return resultado, novo_nome


def interpolacao_spline(
    x: pd.Series, y: pd.Series, order: int = 3
) -> tuple[pd.Series, str]:
    resultado = y.interpolate(method="spline", order=order)
    novo_nome = f"Interp_Spline({y.name})"
    return resultado, novo_nome


def interpolacao_media(x: pd.Series, y: pd.Series) -> tuple[pd.Series, str]:
    resultado = y.fillna(y.mean())
    novo_nome = f"Interp_Media({y.name})"
    return resultado, novo_nome


def operar_variaveis(
    valores_a: pd.Series, valores_b, operacao: int
) -> tuple[pd.Series, str]:
    """
    Aplica uma operação aritmética entre dois operandos para criar uma nova variável.

    Args:
        valores_a: Série pandas com os dados da variável A.
        valores_b: Série pandas (variável) ou constante float para o operando B.
        operacao: Índice da operação (0=soma, 1=subtração, 2=multiplicação, 3=divisão).

    Returns:
        Tupla (resultado: pd.Series, mensagem_erro: str ou None).
        Se houver erro, resultado fica None
    """
    try:
        if operacao == 0:  # Soma
            return valores_a + valores_b, None
        elif operacao == 1:  # Subtração
            return valores_a - valores_b, None
        elif operacao == 2:  # Multiplicação
            return valores_a * valores_b, None
        elif operacao == 3:  # Divisão
            if isinstance(valores_b, (int, float)):
                if valores_b == 0:
                    return None, "Divisão por zero não é permitida."
            else:
                if (valores_b == 0).any():
                    # Avisa mas continua (resultado terá NaN/inf)
                    pass
            return valores_a / valores_b, None
        else:
            return None, "Operação inválida."
    except Exception as e:
        return None, f"Erro na operação aritmética: {str(e)}"


def operar_trigonometria(
    valores: pd.Series, operacao: str, unidade: str = "rad"
) -> tuple[pd.Series, str]:
    """
    Aplica uma função trigonométrica aos dados angulares.

    Args:
        valores: Série pandas com os dados angulares.
        operacao: 'seno', 'cosseno' ou 'tangente'.
        unidade: Unidade angular dos dados de entrada ('rad', 'deg', 'graus', 'radianos').
                 Se for graus/deg, converte automaticamente para radianos antes do cálculo.

    Returns:
        Tupla (resultado: pd.Series, mensagem_erro: str ou None).
    """
    try:
        # Converte graus para radianos se necessário
        vals = valores.values.copy().astype(float)
        if unidade.lower().strip() in ("deg", "graus", "°"):
            vals = np.deg2rad(vals)

        if operacao == "seno":
            return pd.Series(np.sin(vals), index=valores.index), None
        elif operacao == "cosseno":
            return pd.Series(np.cos(vals), index=valores.index), None
        elif operacao == "tangente":
            return pd.Series(np.tan(vals), index=valores.index), None
        else:
            return None, "Operação trigonométrica inválida."
    except Exception as e:
        return None, f"Erro no cálculo trigonométrico: {str(e)}"


def operar_calculo_escalar(
    dados_x: pd.Series, dados_y: pd.Series, operacao: str
) -> tuple[pd.Series, str]:
    """
    Args:
        dados_x: Série pandas do eixo X (usada em integral e derivadas).
        dados_y: Série pandas da variável alvo.
        operacao: Uma de 'integral', 'derivada_1', 'derivada_2',
                  'modulo', 'inverso', 'raiz_quadrada'.

    Returns:
        Tupla (resultado: pd.Series, mensagem_erro: str ou None).
    """
    try:
        y_arr = dados_y.values
        x_arr = dados_x.values

        if len(x_arr) == 0:
            return pd.Series(dtype=float), None

        if operacao == "integral":
            if len(x_arr) < 2:
                return pd.Series([0.0], index=dados_x.index), None
            areas = (y_arr[:-1] + y_arr[1:]) / 2 * np.diff(x_arr)
            integral_cum = np.insert(np.cumsum(areas), 0, 0)
            return pd.Series(integral_cum, index=dados_x.index), None

        elif operacao == "derivada_1":
            if len(x_arr) < 2:
                return (
                    None,
                    "São necessários pelo menos 2 pontos para calcular a derivada.",
                )
            deriv = np.gradient(y_arr, x_arr)
            return pd.Series(deriv, index=dados_x.index), None

        elif operacao == "derivada_2":
            if len(x_arr) < 3:
                return (
                    None,
                    "São necessários pelo menos 3 pontos para calcular a segunda derivada.",
                )
            deriv1 = np.gradient(y_arr, x_arr)
            deriv2 = np.gradient(deriv1, x_arr)
            return pd.Series(deriv2, index=dados_x.index), None

        elif operacao == "modulo":
            return pd.Series(np.abs(y_arr), index=dados_x.index), None

        elif operacao == "inverso":
            numerador = np.ones_like(y_arr, dtype=float)
            resultado = np.where(y_arr != 0, np.divide(numerador, y_arr), np.nan)
            return pd.Series(resultado, index=dados_x.index), None

        elif operacao == "raiz_quadrada":
            resultado = np.where(y_arr >= 0, np.sqrt(y_arr), np.nan)
            return pd.Series(resultado, index=dados_x.index), None

        else:
            return None, "Operação inválida."
    except Exception as e:
        return None, f"Erro no cálculo escalar: {str(e)}"


def agrupar_pontos_3d(colunas: list[str]) -> dict:

    # Agrupa colunas do df que representam um ponto 3D (usando expressao regular)
    """
    Args:
        colunas: Lista de nomes das colunas.
    Returns:
        Dicionário { 'NomeBase': {'x': 'col_x', 'y': 'col_y', 'z': 'col_z'} }
    """
    import re

    points = {}
    pattern = re.compile(r"^(.*?)(?:_|\.)([xyzXYZ])(\s*\[.*?\])?$")

    for col in colunas:
        match = pattern.match(col)
        if match:
            base, comp, unit = match.groups()
            comp = comp.lower()
            if base not in points:
                points[base] = {}
            points[base][comp] = col

    # Filtra apenas os que têm as 3 componentes
    return {
        base: comps
        for base, comps in points.items()
        if all(c in comps for c in ("x", "y", "z"))
    }


def operar_angulo_3d(
    df: pd.DataFrame, modo: str, pontos: dict, unidade: str
) -> tuple[pd.Series, str]:

    # Calcula um ângulo baseado na posição 3D dos pontos fornecidos.
    """
    Args:
        df: DataFrame com as colunas selecionadas.
        modo: 'relativo' ou 'vetores'.
        pontos: Dicionário identificando o papel de cada ponto
                Para 'relativo': necessita das chaves 'p1', 'vertice', 'p3'.
                Para 'vetores': necessita das chaves 'p1_ini', 'p1_fim', 'p2_ini', 'p2_fim'.
                Cada valor é um sub-dicionário {'x': 'col_X', 'y': 'col_Y', 'z': 'col_Z'}.
        unidade: 'graus' ou 'radianos'.

    Returns:
        Tupla (resultado: pd.Series, mensagem_erro: str ou None).
    """
    try:

        def get_coords(p_dict):
            """Retorna matriz Nx3 para o ponto"""
            x = df[p_dict["x"]].values
            y = df[p_dict["y"]].values
            z = df[p_dict["z"]].values
            return np.column_stack((x, y, z))

        if modo == "relativo":
            p1 = get_coords(pontos["p1"])
            vertice = get_coords(pontos["vertice"])
            p3 = get_coords(pontos["p3"])

            u = p1 - vertice
            v = p3 - vertice

        elif modo == "vetores":
            v1_ini = get_coords(pontos["p1_ini"])
            v1_fim = get_coords(pontos["p1_fim"])
            v2_ini = get_coords(pontos["p2_ini"])
            v2_fim = get_coords(pontos["p2_fim"])

            u = v1_fim - v1_ini
            v = v2_fim - v2_ini
        else:
            return None, "Modo de ângulo desconhecido."

        # Produto Escalar
        # np.sum(u * v, axis=1) faz o dot product frame a frame
        dot_product = np.sum(u * v, axis=1)

        # Normas
        norm_u = np.linalg.norm(u, axis=1)
        norm_v = np.linalg.norm(v, axis=1)

        # Evitando divisão por zero se o vetor tiver magnitude zero
        denom = norm_u * norm_v

        # Onde a norma for 0, definimos como NaN
        with np.errstate(divide="ignore", invalid="ignore"):
            cos_theta = dot_product / denom

        # Garante que por erro de precisão o cosseno não saia de [-1, 1]
        cos_theta = np.clip(cos_theta, -1.0, 1.0)

        ang_rad = np.arccos(cos_theta)

        if unidade == "graus":
            resultado = ang_rad * (180.0 / np.pi)
        else:
            resultado = ang_rad

        return pd.Series(resultado, index=df.index), None

    except Exception as e:
        return None, f"Erro no cálculo do ângulo 3D: {str(e)}"
