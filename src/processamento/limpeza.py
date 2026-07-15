import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt


def _traduzir_erro_filtro(erro, order):
    """Traduz mensagens de erro comuns do scipy para português."""
    msg = str(erro)

    if "padlen" in msg or "input vector x must be greater" in msg:
        min_pontos = 3 * (order + 1) + 1
        return (
            "O sinal tem poucos pontos válidos para essa ordem de filtro. "
            "Reduza a ordem do filtro ou use um sinal com mais dados."
        )

    if "digital filter critical frequenc" in msg.lower():
        return "Frequência de corte inválida para o filtro."

    if "empty" in msg.lower() or "zero-size" in msg.lower():
        return "O sinal está vazio ou não possui dados válidos para filtrar."

    # retorna tradução genérica com erro original
    return f"Erro ao aplicar o filtro: {msg}"


def _filtfilt_nan_safe(b, a, y_values, order=4):
    """Aplica filtfilt tratando NaN: filtra apenas valores válidos e
    preserva NaN nas posições originais.

    scipy.filtfilt propaga NaN para todo o sinal se houver qualquer NaN
    no input. Esta função contorna isso extraindo apenas os valores
    válidos, aplicando o filtro, e recolocando os resultados.
    """
    mask_valido = ~np.isnan(y_values)

    if not mask_valido.any():
        raise ValueError("O sinal não possui nenhum valor válido (todos são NaN).")

    n_validos = mask_valido.sum()
    min_pontos = 3 * (order + 1) + 1
    if n_validos < min_pontos:
        raise ValueError(
            f"O sinal tem apenas {n_validos} pontos válidos, "
            f"mas o mínimo para ordem {order} é {min_pontos}. "
            f"Reduza a ordem do filtro ou use um sinal com mais dados."
        )

    if mask_valido.all():
        return filtfilt(b, a, y_values)  # Sem NaN, aplica direto

    # Filtra apenas os valores válidos
    y_valido = y_values[mask_valido]
    try:
        y_filtrado_valido = filtfilt(b, a, y_valido)
    except Exception as e:
        raise ValueError(_traduzir_erro_filtro(e, order)) from None

    # Recoloca nas posições originais, mantendo NaN
    resultado = y_values.copy().astype(float)
    resultado[mask_valido] = y_filtrado_valido

    return resultado


def filtro_passa_baixa(
    x: pd.Series, y: pd.Series, fc: float, fs: float, order: int = 4
) -> tuple[pd.Series, str]:
    """
    Aplica um filtro Butterworth passa-baixa Bidirecional (zero-phase) nos dados.
    Trata NaN automaticamente (valores NaN são preservados na saída).
    """
    nyq = 0.5 * fs
    normal_cutoff = fc / nyq

    if normal_cutoff >= 1.0:
        raise ValueError(
            f"Frequência de corte ({fc} Hz) deve ser menor que "
            f"a frequência de Nyquist ({nyq} Hz)."
        )

    try:
        b, a = butter(order, normal_cutoff, btype="low", analog=False)
        y_filtrado = _filtfilt_nan_safe(b, a, y.values, order=order)
    except ValueError:
        raise  # Já está traduzido
    except Exception as e:
        raise ValueError(_traduzir_erro_filtro(e, order)) from None

    resultado = pd.Series(y_filtrado, index=x.index)
    novo_nome = f"Passa-Baixa({fc}Hz)({y.name})"

    return resultado, novo_nome


def filtro_passa_alta(
    x: pd.Series, y: pd.Series, fc: float, fs: float, order: int = 4
) -> tuple[pd.Series, str]:
    """
    Aplica um filtro Butterworth passa-alta Bidirecional (zero-phase) nos dados.
    Trata NaN automaticamente (valores NaN são preservados na saída).
    """
    nyq = 0.5 * fs
    normal_cutoff = fc / nyq

    if normal_cutoff >= 1.0:
        raise ValueError(
            f"Frequência de corte ({fc} Hz) deve ser menor que "
            f"a frequência de Nyquist ({nyq} Hz)."
        )

    try:
        b, a = butter(order, normal_cutoff, btype="high", analog=False)
        y_filtrado = _filtfilt_nan_safe(b, a, y.values, order=order)
    except ValueError:
        raise  # Já está traduzido
    except Exception as e:
        raise ValueError(_traduzir_erro_filtro(e, order)) from None

    resultado = pd.Series(y_filtrado, index=x.index)
    novo_nome = f"Passa-Alta({fc}Hz)({y.name})"

    return resultado, novo_nome


def calcular_fc_winter(y_values, fs, order=4, fc_min=1.0, fc_step=0.5):
    """Calcula a frequência de corte ótima pelo Método de Winter (análise residual).

    Testa diversas frequências de corte e calcula o resíduo RMS entre o sinal
    original e o filtrado. A frequência ótima é o ponto onde a curva de resíduos
    se afasta da reta de ruído (o 'joelho' da curva).

    Parâmetros:
        y_values: np.ndarray com os dados do sinal (pode conter NaN)
        fs: frequência de amostragem (Hz)
        order: ordem do filtro Butterworth (default: 4)
        fc_min: frequência mínima a testar (Hz)
        fc_step: incremento entre frequências testadas (Hz)

    Retorna:
        fc_otima: frequência de corte ótima (Hz)
        fcs: array de frequências testadas
        residuos: array de resíduos RMS correspondentes
    """
    nyq = 0.5 * fs

    # Remove NaN para o cálculo
    mask_valido = ~np.isnan(y_values)
    if not mask_valido.any():
        raise ValueError("O sinal não possui valores válidos para análise.")

    y_limpo = y_values[mask_valido]
    n_pontos = len(y_limpo)
    min_pontos = 3 * (order + 1) + 1

    if n_pontos < min_pontos:
        raise ValueError(
            f"O sinal tem apenas {n_pontos} pontos válidos. "
            f"Mínimo para ordem {order}: {min_pontos}."
        )

    # Gera frequências candidatas
    fc_max = nyq - fc_step
    fcs = np.arange(fc_min, fc_max, fc_step)

    if len(fcs) < 3:
        raise ValueError("Faixa de frequências muito estreita para análise residual.")

    # Calcula resíduos RMS para cada fc
    residuos = []
    fcs_validos = []

    for fc in fcs:
        wn = fc / nyq
        if wn >= 1.0 or wn <= 0:
            continue
        try:
            b, a = butter(order, wn, btype="low", analog=False)
            y_filt = filtfilt(b, a, y_limpo)
            rms = np.sqrt(np.mean((y_limpo - y_filt) ** 2))
            residuos.append(rms)
            fcs_validos.append(fc)
        except Exception:
            continue

    if len(fcs_validos) < 3:
        raise ValueError("Não foi possível calcular resíduos suficientes.")

    fcs_arr = np.array(fcs_validos)
    res_arr = np.array(residuos)

    # Normaliza ambos os eixos para [0, 1] para que a distância perpendicular
    # não seja dominada pelo eixo com maior escala
    fc_norm = (fcs_arr - fcs_arr[0]) / (fcs_arr[-1] - fcs_arr[0])
    res_norm = (res_arr - res_arr[-1]) / (res_arr[0] - res_arr[-1])

    # Corda: reta do primeiro ponto (0, 1) ao último (1, 0) no espaço normalizado
    # Vetor da corda: (1, -1), perpendicular: (1, 1) / sqrt(2)
    # Distância perpendicular de cada ponto à corda:
    # d = |( (x - x1)*(y2 - y1) - (y - y1)*(x2 - x1) )| / L
    # Com (x1,y1)=(0,1), (x2,y2)=(1,0): d = |(x*(-1) - (y-1)*1)| / sqrt(2)
    # = |(-x - y + 1)| / sqrt(2) = |(1 - x - y)| / sqrt(2)
    distancias = np.abs(1 - fc_norm - res_norm)

    idx_otimo = np.argmax(distancias)
    fc_otima = fcs_arr[idx_otimo]

    return fc_otima, fcs_arr, res_arr


def calcular_fs(tempos):
    """Calcula a frequência de amostragem a partir do array de tempos em segundos."""
    tempos = np.asarray(tempos)
    dt = np.diff(tempos)
    dt = dt[~np.isnan(dt)]
    if len(dt) == 0:
        return 100.0
    dt_mean = np.mean(dt)
    if dt_mean <= 0:
        return 100.0
    return 1.0 / dt_mean


def recomputar_dados_com_filtros(dados_x, dados_y, filtros_ativos):
    """Aplica uma lista de filtros aos dados de entrada respeitando a ordem e flags de retificação."""
    dados_y_processados = np.array(dados_y, copy=True)
    if len(dados_x) == 0 or len(dados_y_processados) == 0:
        return dados_y_processados

    for filtro in filtros_ativos:
        if not filtro.get("ativo", True):
            continue

        if filtro.get("retificar", False):
            dados_y_processados = np.abs(dados_y_processados)

        tipo = filtro.get("tipo")
        fc = filtro.get("fc")
        fs = filtro.get("fs")

        if fc is not None and fs is not None and fs > 0:
            nyq = 0.5 * fs
            if fc >= nyq:
                continue  # Ignora filtro mal dimensionado

            normal_cutoff = fc / nyq
            ordem = filtro.get("ordem", 4)

            b, a = butter(
                ordem,
                normal_cutoff,
                btype="low" if tipo == "passa_baixa" else "high",
                analog=False,
            )

            # Trata NaNs antes do filtfilt (que propaga NaNs)
            mask = ~np.isnan(dados_y_processados)
            if np.any(mask):
                if len(dados_y_processados[mask]) > 3 * max(len(a), len(b)):
                    dados_y_processados[mask] = filtfilt(
                        b, a, dados_y_processados[mask]
                    )

    return dados_y_processados
