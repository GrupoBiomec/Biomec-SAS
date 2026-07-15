import numpy as np


class AnaliseCurva:
    """Calcula informações descritivas sobre uma curva (sinal biomecânico)."""

    def __init__(self, dados_x, dados_y):

        self.x = np.asarray(dados_x, dtype=float)
        self.y = np.asarray(dados_y, dtype=float)

        # Máscara de valores válidos (sem NaN)
        self.mask_valido = ~np.isnan(self.y)
        self.y_valido = self.y[self.mask_valido]
        self.x_valido = self.x[self.mask_valido]

    def valor_maximo(self):
        """Retorna y máximo e o X correspondente."""
        if len(self.y_valido) == 0:
            return None, None
        idx = np.argmax(self.y_valido)
        return float(self.y_valido[idx]), float(self.x_valido[idx])

    def valor_minimo(self):
        """Retorna y mínimo e X correspondente."""
        if len(self.y_valido) == 0:
            return None, None
        idx = np.argmin(self.y_valido)
        return float(self.y_valido[idx]), float(self.x_valido[idx])

    def pico_global_maximo(self):
        """Retorna o pico máximo global (mesmo que valor_maximo para picos globais)."""
        return self.valor_maximo()

    def pico_global_minimo(self):
        """Retorna o pico mínimo global (vale mais profundo)."""
        return self.valor_minimo()

    def taxa_amostragem(self):
        """Calcula a taxa de amostragem (Hz) a partir dos intervalos do eixo X.

        Returns:
            float ou None: Frequência em Hz se X representar tempo em segundos,
                          ou intervalo médio entre amostras caso contrário.
        """
        if len(self.x_valido) < 2:
            return None

        diffs = np.diff(self.x_valido)
        diffs_positivos = diffs[diffs > 0]

        if len(diffs_positivos) == 0:
            return None

        dt_medio = float(np.median(diffs_positivos))

        if dt_medio > 0:
            return 1.0 / dt_medio
        return None

    def amplitude(self):
        """Retorna a amplitude total do sinal"""
        v_max, _ = self.valor_maximo()
        v_min, _ = self.valor_minimo()
        if v_max is not None and v_min is not None:
            return v_max - v_min
        return None

    def num_amostras(self):
        """Retorna o número total de amostras e de amostras válidas."""
        return len(self.y), len(self.y_valido)

    def rms_curva(self):
        if len(self.y_valido) == 0:
            return 0.0
        return np.sqrt(np.mean(self.y_valido**2))

    def resumo(self):
        """Retorna um dicionário com todas as métricas calculadas."""
        v_max, x_max = self.valor_maximo()
        v_min, x_min = self.valor_minimo()
        total, validos = self.num_amostras()
        fs = self.taxa_amostragem()

        # Min/Max do eixo X
        x_minimo = float(self.x_valido.min()) if len(self.x_valido) > 0 else None
        x_maximo = float(self.x_valido.max()) if len(self.x_valido) > 0 else None

        return {
            "valor_maximo": v_max,
            "x_no_maximo": x_max,
            "valor_minimo": v_min,
            "x_no_minimo": x_min,
            "x_minimo": x_minimo,
            "x_maximo": x_maximo,
            "amplitude": self.amplitude(),
            "taxa_amostragem": fs,
            "total_amostras": total,
            "amostras_validas": validos,
            "rms": self.rms_curva(),
        }
