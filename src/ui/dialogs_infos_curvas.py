from ui.utils import PadraoDialog
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class JanelaInformacoesCurva(PadraoDialog):
    """Janela que exibe as informações estatísticas de uma curva."""

    def __init__(
        self,
        nome_grafico,
        info,
        label_x="X",
        label_y="Y",
        var_x="",
        var_y="",
        unidade_x="",
        unidade_y="",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Informações da Curva")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        def fmt(val, decimais=4):
            if val is None:
                return "N/A"
            return f"{val:.{decimais}f}"

        def fmt_y_com_x(val_y, val_x, un_x=""):
            """Formata valor Y com a posição X correspondente entre parênteses."""
            if val_y is None:
                return "N/A"
            y_str = fmt(val_y)
            if val_x is not None:
                x_str = fmt(val_x)
                if un_x:
                    return f"{y_str}  (X = {x_str} {un_x})"
                else:
                    return f"{y_str}  (X = {x_str})"
            return y_str

        texto = f"<b>Gráfico:</b> {nome_grafico}<br><br>"

        # Eixo X
        texto += f"<b>Eixo X:</b> {label_x}<br>"
        texto += f"Valor Mínimo: {fmt(info['x_minimo'])}<br>"
        texto += f"Valor Máximo: {fmt(info['x_maximo'])}<br><br>"

        # Eixo Y
        texto += f"<b>Eixo Y:</b> {label_y}<br>"
        texto += f"Valor Mínimo: {fmt_y_com_x(info['valor_minimo'], info['x_no_minimo'], unidade_x)}<br>"
        texto += f"Valor Máximo: {fmt_y_com_x(info['valor_maximo'], info['x_no_maximo'], unidade_x)}<br>"
        texto += f"Amplitude: {fmt(info['amplitude'])}<br>"
        if "rms" in info and info["rms"] is not None:
            texto += f"RMS (Root Mean Square): {fmt(info['rms'])}<br><br>"
        else:
            texto += "<br>"

        # Picos Globais
        texto += f"Pico Máximo Global: {fmt_y_com_x(info['valor_maximo'], info['x_no_maximo'], unidade_x)}<br>"
        texto += f"Pico Mínimo Global: {fmt_y_com_x(info['valor_minimo'], info['x_no_minimo'], unidade_x)}<br><br>"

        # Amostragem
        if info["taxa_amostragem"] is not None:
            fs = info["taxa_amostragem"]
            texto += f"Taxa de Amostragem: {fmt(fs, 2)} Hz<br>"
        else:
            texto += "Taxa de Amostragem: N/A<br>"

        texto += (
            f"Amostras Válidas: {info['amostras_validas']} / {info['total_amostras']}"
        )

        lbl = QLabel(texto)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl)

        btn = QPushButton("Fechar")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
