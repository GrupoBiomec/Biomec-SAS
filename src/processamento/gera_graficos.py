from ui.utils import PadraoDialog
import pyqtgraph as pg
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QScrollArea,
    QMessageBox,
    QRadioButton,
    QFrame,
    QGridLayout,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt


class JanelaConfig(PadraoDialog):

    def __init__(self, df, parent=None, unidade_y_default="", unidades_colunas=None):
        super().__init__(parent)
        self.df = df
        self.unidade_y_default = unidade_y_default
        self.unidades_colunas = unidades_colunas or {}
        self.setWindowTitle("Configurar Gráfico")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)

        # Título do gráfico
        layout.addWidget(QLabel("Título do Gráfico:"))
        self.input_titulo = QLineEdit()
        layout.addWidget(self.input_titulo)

        # Tipo de gráfico
        layout.addWidget(QLabel("Tipo de Gráfico:"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Linha", "Dispersão"])
        layout.addWidget(self.combo_tipo)

        # Seleção de eixo X
        layout.addWidget(QLabel("Eixo X:"))
        self.combo_x = QComboBox()
        for col in df.columns.tolist():
            label = self._formatar_coluna(col)
            self.combo_x.addItem(label, col)  # label exibido, col é o dado real

        # Tenta definir a coluna de tempo como padrão no eixo X
        achou_X = False
        for i in range(self.combo_x.count()):
            col_name = self.combo_x.itemData(i)
            if col_name and col_name.lower() in ["time", "tempo"]:
                self.combo_x.setCurrentIndex(i)
                achou_X = True
                break

        if not achou_X:
            for i in range(self.combo_x.count()):
                col_name = self.combo_x.itemData(i)
                if col_name and col_name.lower() in ["frame", "frames", "t", "item"]:
                    self.combo_x.setCurrentIndex(i)
                    break

        layout.addWidget(self.combo_x)

        # Unidade do Eixo X
        layout.addWidget(QLabel("Unidade X:"))
        self.input_unidade_x = QLineEdit()
        self.input_unidade_x.setPlaceholderText("Ex: s, frames")
        layout.addWidget(self.input_unidade_x)

        # Seleção de eixo Y
        layout.addWidget(QLabel("Eixo Y:"))
        self.combo_y = QComboBox()
        self.combo_y.addItem("", "")  # Opção em branco como default
        for col in df.columns.tolist():
            label = self._formatar_coluna(col)
            self.combo_y.addItem(label, col)
        self.combo_y.setCurrentIndex(0)
        layout.addWidget(self.combo_y)

        # Unidade do Eixo Y
        layout.addWidget(QLabel("Unidade Y:"))
        self.input_unidade_y = QLineEdit()
        self.input_unidade_y.setPlaceholderText("Ex: V, m/s")
        self.input_unidade_y.setText(unidade_y_default)
        layout.addWidget(self.input_unidade_y)

        # Interface
        self.combo_x.currentIndexChanged.connect(self._sugerir_unidade_x)
        self._sugerir_unidade_x()

        self.combo_y.currentIndexChanged.connect(self._sugerir_unidade_y)
        self._sugerir_unidade_y()

        botoes_layout = QHBoxLayout()
        btn_ok = QPushButton("Criar Gráfico")
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        botoes_layout.addWidget(btn_ok)
        botoes_layout.addWidget(btn_cancelar)
        layout.addLayout(botoes_layout)

    def _formatar_coluna(self, nome_coluna):
        """Formata nome da coluna com unidade entre colchetes para exibição."""
        unidade = self.unidades_colunas.get(nome_coluna)
        if unidade:
            return f"{nome_coluna} [{unidade}]"
        return nome_coluna

    def _obter_unidade(self, nome_coluna):
        """Obtém a unidade de uma coluna do mapeamento ou por heurística."""
        # 1. Consulta o mapeamento
        if nome_coluna in self.unidades_colunas:
            return self.unidades_colunas[nome_coluna]

        # 2. Heurísticas para colunas sem mapeamento
        texto_lower = str(nome_coluna).lower().strip()
        if (
            texto_lower in ["time", "tempo", "t", "item"]
            or "tempo" in texto_lower
            or "time" in texto_lower
            or "item" in texto_lower
        ):
            return "s"
        if texto_lower in ["frame", "frames"]:
            return "frames"

        return None

    def _sugerir_unidade_x(self):
        col = self.combo_x.currentData()
        unidade = self._obter_unidade(col) if col else None
        self.input_unidade_x.setText(unidade if unidade is not None else "")

    def _sugerir_unidade_y(self):
        col = self.combo_y.currentData()
        unidade = self._obter_unidade(col) if col else None
        if unidade is not None:
            self.input_unidade_y.setText(unidade)
        else:
            self.input_unidade_y.setText(self.unidade_y_default)

    def accept(self):
        if not self.combo_y.currentData():
            QMessageBox.warning(
                self,
                "Aviso",
                "Selecione uma variável para o Eixo Y antes de criar o gráfico!",
            )
            return
        super().accept()

    def get_configuracoes(self):
        # Retorna configurações do gráfico com nomes limpos (sem unidade)
        config = {
            "titulo": self.input_titulo.text(),
            "tipo": self.combo_tipo.currentText(),
            "eixo_x": self.combo_x.currentData(),  # nome limpo da coluna
            "eixo_y": self.combo_y.currentData(),  # nome limpo da coluna
            "unidade_x": self.input_unidade_x.text().strip(),
            "unidade_y": self.input_unidade_y.text().strip(),
        }

        return config


class GeradorGraficos:

    def __init__(self, plot_widget):  # Sugestao de unidade pelo formato do dado

        self.plot_widget = plot_widget
        self.plot_widget.setMenuEnabled(False)
        if hasattr(self.plot_widget, "plotItem") and self.plot_widget.plotItem:
            self.plot_widget.plotItem.setMenuEnabled(False)
        self.curvas_ativas = []

        # Conecta sinal de mudança de range visual para o Zoom
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._on_zoom_changed)

    def limpar(self):
        # Remove todos os gráficos
        self.plot_widget.clear()

        # Reseta o auto-range para que os novos gráficos não fiquem com o zoom do anterior
        self.plot_widget.plotItem.vb.enableAutoRange(axis="xy")

        if self.plot_widget.plotItem.legend is not None:
            self.plot_widget.plotItem.legend.clear()

        self.plot_widget.hideAxis("right")
        self.plot_widget.hideAxis("top")

        # Remove extras viewboxes se foram criados por twinx/twiny (qnd tem mais de um eixo y)
        if (
            hasattr(self, "vb_extra")
            and self.vb_extra in self.plot_widget.scene().items()
        ):
            self.plot_widget.scene().removeItem(self.vb_extra)
            del self.vb_extra

        self.curvas_ativas = []

    def set_zoom_mode(self, active: bool):
        if active:
            self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)
            self.plot_widget.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.PanMode)
            self.plot_widget.setCursor(Qt.CursorShape.ArrowCursor)
            self.plot_widget.autoRange()  # Reseta o zoom

    def _on_zoom_changed(self):
        # Filtra a legenda baseada na área visível
        if not self.curvas_ativas or not self.plot_widget.plotItem.legend:
            return

        view_range = self.plot_widget.plotItem.viewRange()
        xmin, xmax = view_range[0][0], view_range[0][1]
        ymin, ymax = view_range[1][0], view_range[1][1]

        for curva in self.curvas_ativas:
            nome = getattr(curva, "name", lambda: None)()
            if not nome:
                continue

            x_data, y_data = None, None
            if isinstance(curva, pg.PlotDataItem) or isinstance(
                curva, pg.PlotCurveItem
            ):
                x_data, y_data = curva.getData()
            elif hasattr(curva, "getData"):
                dados = curva.getData()
                if len(dados) >= 2:
                    x_data, y_data = dados[0], dados[1]

            if x_data is None or y_data is None or len(x_data) == 0:
                continue

            # Verifica se há algum ponto da curva dentro da caixa visível
            visivel = np.any(
                (x_data >= xmin)
                & (x_data <= xmax)
                & (y_data >= ymin)
                & (y_data <= ymax)
            )

            # Remove ou adiciona na legenda dinamicamente
            if visivel:
                # O addItem de pyqtgraph não duplica se já existe na legenda com a mesma curva, mas é seguro checar
                # na verdade o addItem precisa da curva e do nome
                achou_item = False
                for sample, label in self.plot_widget.plotItem.legend.items:
                    if sample.item is curva:
                        achou_item = True
                        break
                if not achou_item:
                    self.plot_widget.plotItem.legend.addItem(curva, nome)
            else:
                self.plot_widget.plotItem.legend.removeItem(curva)

    def plotar_linha(
        self, dados_x, dados_y, config=None
    ):  # config: dict com {'titulo', 'label_x', 'label_y', 'cor', 'nome_legenda'}

        config = config or {}

        x = self._converter_para_array(dados_x)
        y = self._converter_para_array(dados_y)

        # Aplicar configurações
        if config.get("titulo"):
            self.plot_widget.setTitle(config["titulo"])
        if config.get("label_x"):
            self.plot_widget.setLabel("bottom", config["label_x"])
        if config.get("label_y"):
            self.plot_widget.setLabel("left", config["label_y"])

        # Plotar
        cor = config.get("cor", "b")
        espessura = config.get("espessura", 2)
        pen = pg.mkPen(color=cor, width=espessura)

        connect = config.get("connect", "all")

        nome_legenda = config.get("nome_legenda")
        if nome_legenda:
            if self.plot_widget.plotItem.legend is None:
                self.plot_widget.addLegend()
            curva = self.plot_widget.plot(
                x, y, pen=pen, name=nome_legenda, connect=connect
            )
        else:
            curva = self.plot_widget.plot(x, y, pen=pen, connect=connect)

        # Plota múltiplas linhas de referência (polinômios)
        linhas_ref = config.get("linhas_referencia", [])
        linhas_ativas = [lr for lr in linhas_ref if lr.get("ativo", True)]
        if linhas_ativas:
            # Captura o range Y dos dados originais antes de plotar as referências
            y_limpo = y[np.isfinite(y)]
            if len(y_limpo) > 0:
                y_min, y_max = float(y_limpo.min()), float(y_limpo.max())
                margem = (y_max - y_min) * 0.05 if y_max != y_min else 1.0
                range_y_original = (y_min - margem, y_max + margem)
            else:
                range_y_original = None

            if self.plot_widget.plotItem.legend is None:
                self.plot_widget.addLegend()
            for lr in linhas_ativas:
                y_ref = self._converter_para_array(lr["dados_y"])
                cor_ref = lr.get("cor", "r")
                pen_ref = pg.mkPen(color=cor_ref, style=Qt.PenStyle.DashLine, width=2)
                nome_ref = lr.get("titulo", "Referência")
                self.plot_widget.plot(x, y_ref, pen=pen_ref, name=nome_ref)

            # Restaura o range Y dos dados originais para não achatar o gráfico
            if range_y_original is not None:
                self.plot_widget.setYRange(
                    range_y_original[0], range_y_original[1], padding=0
                )

        self.curvas_ativas.append(curva)

        return curva

    def plotar_barras(self, categorias, valores, config=None):

        config = config or {}

        x = np.arange(len(categorias))
        y = self._converter_para_array(valores)

        cor = config.get("cor", "b")
        bargraph = pg.BarGraphItem(x=x, height=y, width=0.6, brush=cor)
        self.plot_widget.addItem(bargraph)

        if config.get("titulo"):
            self.plot_widget.setTitle(config["titulo"])
        if config.get("label_x"):
            self.plot_widget.setLabel("bottom", config["label_x"])
        if config.get("label_y"):
            self.plot_widget.setLabel("left", config["label_y"])

        # Labels do eixo X
        cats = (
            categorias.tolist() if hasattr(categorias, "tolist") else list(categorias)
        )
        ax = self.plot_widget.getAxis("bottom")
        ax.setTicks([[(i, str(cat)) for i, cat in enumerate(cats)]])

    def plotar_scatter(self, dados_x, dados_y, config=None):  # de dispersao

        config = config or {}

        x = self._converter_para_array(dados_x)
        y = self._converter_para_array(dados_y)

        cor = config.get("cor", "b")

        nome_legenda = config.get("nome_legenda")
        if nome_legenda:
            if self.plot_widget.plotItem.legend is None:
                self.plot_widget.addLegend()
            scatter = pg.ScatterPlotItem(
                x=x, y=y, size=10, brush=cor, name=nome_legenda
            )
        else:
            scatter = pg.ScatterPlotItem(x=x, y=y, size=10, brush=cor)

        self.plot_widget.addItem(scatter)

        if config.get("titulo"):
            self.plot_widget.setTitle(config["titulo"])
        if config.get("label_x"):
            self.plot_widget.setLabel("bottom", config["label_x"])
        if config.get("label_y"):
            self.plot_widget.setLabel("left", config["label_y"])

        # Plota múltiplas linhas de referência (polinômios)
        linhas_ref = config.get("linhas_referencia", [])
        linhas_ativas = [lr for lr in linhas_ref if lr.get("ativo", True)]
        if linhas_ativas:
            # Captura o range Y dos dados originais antes de plotar as referências
            y_limpo = y[np.isfinite(y)]
            if len(y_limpo) > 0:
                y_min, y_max = float(y_limpo.min()), float(y_limpo.max())
                margem = (y_max - y_min) * 0.05 if y_max != y_min else 1.0
                range_y_original = (y_min - margem, y_max + margem)
            else:
                range_y_original = None

            if self.plot_widget.plotItem.legend is None:
                self.plot_widget.addLegend()
            for lr in linhas_ativas:
                y_ref = self._converter_para_array(lr["dados_y"])
                cor_ref = lr.get("cor", "r")
                pen_ref = pg.mkPen(color=cor_ref, style=Qt.PenStyle.DashLine, width=2)
                nome_ref = lr.get("titulo", "Referência")
                self.plot_widget.plot(x, y_ref, pen=pen_ref, name=nome_ref)

            # Restaura o range Y dos dados originais para não achatar o gráfico
            if range_y_original is not None:
                self.plot_widget.setYRange(
                    range_y_original[0], range_y_original[1], padding=0
                )

        self.curvas_ativas.append(scatter)

    def plotar_sinais_sobrepostos(
        self, sinais, titulo, ui_parent, tendencia_visual=False, config_geral=None
    ):

        self.plot_widget.clear()
        config_geral = config_geral or {}
        unidades_x_unicas = list(dict.fromkeys([s["x_unit"] for s in sinais]))
        unidades_y_unicas = list(dict.fromkeys([s["y_unit"] for s in sinais]))

        self.plot_widget.addLegend()

        # Helper: calcula o range Y de todos os sinais (dados originais, sem referência)
        def _range_y_sinais():
            todos_y = []
            for s in sinais:
                y_arr = self._converter_para_array(s["y_data"])
                y_limpo = y_arr[np.isfinite(y_arr)]
                if len(y_limpo) > 0:
                    todos_y.append(y_limpo)
            if todos_y:
                todos = np.concatenate(todos_y)
                y_min, y_max = float(todos.min()), float(todos.max())
                margem = (y_max - y_min) * 0.05 if y_max != y_min else 1.0
                return (y_min - margem, y_max + margem)
            return None

        # Helper: plota as linhas de referência dos gráficos-fonte e trava o range Y
        def _plotar_referencia_e_travar():
            # Coleta referências ativas de todos os sinais
            todas_refs = config_geral.get("_linhas_referencia_coletadas", [])
            linhas_ativas = [lr for lr in todas_refs if lr.get("ativo", True)]

            if not linhas_ativas:
                return

            range_y = _range_y_sinais()

            if self.plot_widget.plotItem.legend is None:
                self.plot_widget.addLegend()

            x_fallback = self._converter_para_array(sinais[0]["x_data"])
            for lr in linhas_ativas:
                try:
                    # Usa x_data próprio do gráfico-fonte (se disponível)
                    if "_x_data" in lr:
                        x_ref = self._converter_para_array(lr["_x_data"])
                    else:
                        x_ref = x_fallback
                    y_ref = self._converter_para_array(lr["dados_y"])
                    cor_ref = lr.get("cor", "r")
                    pen_ref = pg.mkPen(
                        color=cor_ref, style=Qt.PenStyle.DashLine, width=2
                    )
                    nome_ref = lr.get("titulo", "Referência")
                    self.plot_widget.plot(x_ref, y_ref, pen=pen_ref, name=nome_ref)
                except Exception as e:
                    print(
                        f"Aviso: Não foi possível plotar referência '{lr.get('titulo', '?')}': {e}"
                    )

            # Restaura o range Y dos sinais para não achatar o gráfico
            if range_y is not None:
                self.plot_widget.setYRange(range_y[0], range_y[1], padding=0)

        # CASO 1: Conflito Total
        if (
            tendencia_visual
            or len(unidades_x_unicas) > 2
            or len(unidades_y_unicas) > 2
            or (len(unidades_x_unicas) > 1 and len(unidades_y_unicas) > 1)
        ):
            self.plot_widget.setTitle("Comparação de Tendência (Sem Escala Unificada)")
            # As escalas numéricas continuam, mas sem a string descritiva do Eixo
            self.plot_widget.setLabel("bottom", "")
            self.plot_widget.setLabel("left", "")

            for s in sinais:
                cfg = {"cor": s["cor"], "nome_legenda": s["nome"]}
                if s.get("tipo") == "Dispersão":
                    self.plotar_scatter(s["x_data"], s["y_data"], config=cfg)
                else:
                    self.plotar_linha(s["x_data"], s["y_data"], config=cfg)
            _plotar_referencia_e_travar()
            return

        self.plot_widget.setTitle(titulo)

        # CASO 2: Unidades Idênticas
        if len(unidades_x_unicas) <= 1 and len(unidades_y_unicas) <= 1:
            u_x = unidades_x_unicas[0] if unidades_x_unicas else ""
            u_y = unidades_y_unicas[0] if unidades_y_unicas else ""

            lbl_x = (
                f"{sinais[0].get('label_x', 'X')} ({u_x})"
                if u_x
                else sinais[0].get("label_x", "X")
            )
            lbl_y = f"Valores ({u_y})" if u_y else "Adimensional"

            self.plot_widget.setLabel("bottom", lbl_x)
            self.plot_widget.setLabel("left", lbl_y)

            for s in sinais:
                cfg = {"cor": s["cor"], "nome_legenda": s["nome"]}
                if s.get("tipo") == "Dispersão":
                    self.plotar_scatter(s["x_data"], s["y_data"], config=cfg)
                else:
                    self.plotar_linha(s["x_data"], s["y_data"], config=cfg)

            _plotar_referencia_e_travar()
            return

        # CASO 3: Conflito Eixo Y (X igual e Y diferente)
        if len(unidades_x_unicas) == 1 and len(unidades_y_unicas) == 2:
            u_x = unidades_x_unicas[0]
            lbl_x = (
                f"{sinais[0].get('label_x', 'X')} ({u_x})"
                if u_x
                else sinais[0].get("label_x", "X")
            )
            self.plot_widget.setLabel("bottom", lbl_x)

            uy1, uy2 = unidades_y_unicas[0], unidades_y_unicas[1]

            # Cor do eixo: cor da curva se única no grupo, preto se múltiplas
            curvas_uy1 = [s for s in sinais if s["y_unit"] == uy1]
            curvas_uy2 = [s for s in sinais if s["y_unit"] == uy2]
            cor_uy1 = curvas_uy1[0]["cor"] if len(curvas_uy1) == 1 else "k"
            cor_uy2 = curvas_uy2[0]["cor"] if len(curvas_uy2) == 1 else "k"

            # Setup Y Principal (cor da primeira curva com uy1)
            self.plot_widget.setLabel(
                "left", f"Valores ({uy1})" if uy1 else "Adimensional", color=cor_uy1
            )
            self.plot_widget.getAxis("left").setPen(pg.mkPen(color=cor_uy1))

            # Setup Y Secundário (cor da primeira curva com uy2)
            self.vb_extra = pg.ViewBox()
            self.plot_widget.scene().addItem(self.vb_extra)
            self.plot_widget.getAxis("right").linkToView(self.vb_extra)
            self.vb_extra.setXLink(self.plot_widget)
            self.plot_widget.showAxis("right")
            self.plot_widget.setLabel(
                "right", f"Valores ({uy2})" if uy2 else "Adimensional", color=cor_uy2
            )
            self.plot_widget.getAxis("right").setPen(pg.mkPen(color=cor_uy2))

            def updateViews():
                if hasattr(self, "vb_extra"):
                    self.vb_extra.setGeometry(
                        self.plot_widget.getViewBox().sceneBoundingRect()
                    )
                    self.vb_extra.linkedViewChanged(
                        self.plot_widget.getViewBox(), self.vb_extra.XAxis
                    )

            updateViews()
            self.plot_widget.getViewBox().sigResized.connect(updateViews)

            for s in sinais:
                if s["y_unit"] == uy1:
                    cfg = {"cor": s["cor"], "nome_legenda": s["nome"]}
                    if s.get("tipo") == "Dispersão":
                        self.plotar_scatter(s["x_data"], s["y_data"], config=cfg)
                    else:
                        self.plotar_linha(s["x_data"], s["y_data"], config=cfg)
                else:
                    pen = pg.mkPen(color=s["cor"], width=2)
                    x_vals = self._converter_para_array(s["x_data"])
                    y_vals = self._converter_para_array(s["y_data"])

                    if s.get("tipo") == "Dispersão":
                        item = pg.ScatterPlotItem(
                            x=x_vals, y=y_vals, size=10, brush=s["cor"], name=s["nome"]
                        )
                        self.vb_extra.addItem(item)
                    else:
                        item = pg.PlotCurveItem(
                            x=x_vals, y=y_vals, pen=pen, name=s["nome"]
                        )
                        self.vb_extra.addItem(item)

                    if self.plot_widget.plotItem.legend is not None:
                        inv_pen = pg.mkPen(color=s["cor"], width=2)
                        self.plot_widget.plot([], [], pen=inv_pen, name=s["nome"])

            _plotar_referencia_e_travar()
            return

        # CASO 4: Conflito Eixo X
        if len(unidades_x_unicas) == 2 and len(unidades_y_unicas) == 1:
            u_y = unidades_y_unicas[0]
            lbl_y = f"Valores ({u_y})" if u_y else "Adimensional"
            self.plot_widget.setLabel("left", lbl_y)

            ux1, ux2 = unidades_x_unicas[0], unidades_x_unicas[1]

            # Cor do eixo: cor da curva se única no grupo, preto se múltiplas
            curvas_ux1 = [s for s in sinais if s["x_unit"] == ux1]
            curvas_ux2 = [s for s in sinais if s["x_unit"] == ux2]
            cor_ux1 = curvas_ux1[0]["cor"] if len(curvas_ux1) == 1 else "k"
            cor_ux2 = curvas_ux2[0]["cor"] if len(curvas_ux2) == 1 else "k"

            # Setup X Principal (cor da primeira curva com ux1)
            self.plot_widget.setLabel(
                "bottom", f"X ({ux1})" if ux1 else "Adimensional", color=cor_ux1
            )
            self.plot_widget.getAxis("bottom").setPen(pg.mkPen(color=cor_ux1))

            # Setup X Secundário (cor da primeira curva com ux2)
            self.vb_extra = pg.ViewBox()
            self.plot_widget.scene().addItem(self.vb_extra)
            self.plot_widget.getAxis("top").linkToView(self.vb_extra)
            self.vb_extra.setYLink(self.plot_widget)
            self.plot_widget.showAxis("top")
            self.plot_widget.setLabel(
                "top", f"X ({ux2})" if ux2 else "Adimensional", color=cor_ux2
            )
            self.plot_widget.getAxis("top").setPen(pg.mkPen(color=cor_ux2))

            def updateViewsY():
                if hasattr(self, "vb_extra"):
                    self.vb_extra.setGeometry(
                        self.plot_widget.getViewBox().sceneBoundingRect()
                    )
                    self.vb_extra.linkedViewChanged(
                        self.plot_widget.getViewBox(), self.vb_extra.YAxis
                    )

            updateViewsY()
            self.plot_widget.getViewBox().sigResized.connect(updateViewsY)

            for s in sinais:
                if s["x_unit"] == ux1:
                    cfg = {"cor": s["cor"], "nome_legenda": s["nome"]}
                    if s.get("tipo") == "Dispersão":
                        self.plotar_scatter(s["x_data"], s["y_data"], config=cfg)
                    else:
                        self.plotar_linha(s["x_data"], s["y_data"], config=cfg)
                else:
                    # Plot explicitly to vb_extra
                    pen = pg.mkPen(color=s["cor"], width=2)
                    x_vals = self._converter_para_array(s["x_data"])
                    y_vals = self._converter_para_array(s["y_data"])

                    if s.get("tipo") == "Dispersão":
                        item = pg.ScatterPlotItem(
                            x=x_vals, y=y_vals, size=10, brush=s["cor"], name=s["nome"]
                        )
                        self.vb_extra.addItem(item)
                    else:
                        item = pg.PlotCurveItem(
                            x=x_vals, y=y_vals, pen=pen, name=s["nome"]
                        )
                        self.vb_extra.addItem(item)

                    if self.plot_widget.plotItem.legend is not None:
                        inv_pen = pg.mkPen(color=s["cor"], width=2)
                        self.plot_widget.plot([], [], pen=inv_pen, name=s["nome"])

            _plotar_referencia_e_travar()
            return

    # OPERAÇÕES MATEMÁTICAS - NumPy

    def aplicar_operacao(self, dados, operacao):

        arr = self._converter_para_array(dados)

        operacoes = {
            "sqrt": np.sqrt,
            "log": np.log,
            "log10": np.log10,
            "abs": np.abs,
            "square": np.square,
            "exp": np.exp,
            "sin": np.sin,
            "cos": np.cos,
        }

        if operacao in operacoes:
            return operacoes[operacao](arr)
        return arr

    def normalizar_dados(self, dados, metodo="minmax"):

        arr = self._converter_para_array(dados)

        if metodo == "minmax":
            diff = arr.max() - arr.min()
            if diff == 0:
                return np.zeros_like(arr)
            return (arr - arr.min()) / diff
        elif metodo == "zscore":
            std = arr.std()
            if std == 0:
                return np.zeros_like(arr)
            return (arr - arr.mean()) / std

        return arr

    def _converter_para_array(self, dados):

        if isinstance(dados, pd.Series):
            return dados.values
        elif isinstance(dados, list):
            return np.array(dados)
        elif isinstance(dados, np.ndarray):
            return dados
        else:
            return np.array(dados)


class JanelaSobreporGraficos(PadraoDialog):
    # Janela para selecionar quais gráficos sobrepor

    def __init__(self, graficos_disponiveis, parent=None):
        super().__init__(parent)

        self.graficos_disponiveis = graficos_disponiveis
        self.checkboxes = []

        self.setWindowTitle("Sobrepor Gráficos")
        self.setMinimumSize(400, 350)

        layout = QVBoxLayout(self)

        titulo = QLabel("Selecione os gráficos para sobrepor:")
        titulo.setStyleSheet("font-weight: bold;")
        layout.addWidget(titulo)

        layout.addWidget(QLabel("Título:"))
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Comparação Joelhos")
        layout.addWidget(self.input_nome)
        layout.addSpacing(10)

        # Área com scroll para checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for grafico in graficos_disponiveis:
            checkbox = QCheckBox(grafico["label"])
            checkbox.setProperty("grafico_data", grafico)  # Guarda dados
            self.checkboxes.append(checkbox)
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Botão "Selecionar todos"
        btn_todos = QPushButton("Selecionar Todos")
        btn_todos.clicked.connect(self._selecionar_todos)
        layout.addWidget(btn_todos)

        # Botões OK/Cancelar
        botoes_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._validar_e_aceitar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_ok)
        botoes_layout.addWidget(btn_cancelar)
        layout.addLayout(botoes_layout)

    def _selecionar_todos(self):
        # Marca/desmarca todos os checkboxes

        todos_marcados = all(cb.isChecked() for cb in self.checkboxes)

        for checkbox in self.checkboxes:
            checkbox.setChecked(not todos_marcados)

    def _validar_e_aceitar(self):
        # Valida seleção antes de aceitar
        selecionados = self.get_selecionados()

        if len(selecionados) < 2:
            QMessageBox.warning(
                self,
                "Seleção Inválida",
                "Selecione pelo menos 2 gráficos para sobrepor.",
            )
            return

        self.accept()

    def get_selecionados(self):
        # Retorna lista de gráficos selecionados
        selecionados = []
        for checkbox in self.checkboxes:
            if checkbox.isChecked():
                selecionados.append(checkbox.property("grafico_data"))
        return selecionados

    def get_nome(self):
        return self.input_nome.text().strip()


class DraggableSquare(QLabel):
    def __init__(self, text, grafico_data, parent=None):
        super().__init__(text, parent)
        self.grafico_data = grafico_data
        self.setStyleSheet(
            "background-color: lightblue; color: black; border: 1px solid blue; padding: 5px;"
        )

        try:
            align = Qt.AlignmentFlag.AlignCenter
        except AttributeError:
            align = Qt.AlignCenter

        self.setAlignment(align)
        self.setFixedSize(100, 100)  # Formato Quadrado Fixo
        self.setWordWrap(True)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        try:
            left_btn = Qt.MouseButton.LeftButton
        except AttributeError:
            left_btn = Qt.LeftButton

        if event.button() == left_btn:
            self._drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is not None:
            new_pos = self.mapToParent(event.pos() - self._drag_start_pos)

            # Constrain to parent bounds
            parent_rect = self.parent().rect()
            if new_pos.x() < 0:
                new_pos.setX(0)
            if new_pos.y() < 0:
                new_pos.setY(0)
            if new_pos.x() > parent_rect.width() - self.width():
                new_pos.setX(parent_rect.width() - self.width())
            if new_pos.y() > parent_rect.height() - self.height():
                new_pos.setY(parent_rect.height() - self.height())

            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None

        parent = self.parent()
        if not parent:
            return

        colliding = True
        max_iters = 10
        while colliding and max_iters > 0:
            colliding = False
            for child in parent.findChildren(DraggableSquare):
                if child is not self and child.isVisible():
                    rect_self = self.geometry()
                    rect_other = child.geometry()

                    if rect_self.intersects(rect_other):
                        colliding = True

                        overlap_left = rect_self.right() - rect_other.left()
                        overlap_right = rect_other.right() - rect_self.left()
                        overlap_top = rect_self.bottom() - rect_other.top()
                        overlap_bottom = rect_other.bottom() - rect_self.top()

                        min_overlap = min(
                            overlap_left, overlap_right, overlap_top, overlap_bottom
                        )

                        if min_overlap == overlap_left:
                            self.move(rect_other.left() - rect_self.width(), self.y())
                        elif min_overlap == overlap_right:
                            self.move(rect_other.right(), self.y())
                        elif min_overlap == overlap_top:
                            self.move(self.x(), rect_other.top() - rect_self.height())
                        elif min_overlap == overlap_bottom:
                            self.move(self.x(), rect_other.bottom())

                        # Re-constrain to parent bounds
                        parent_rect = parent.rect()
                        if self.x() < 0:
                            self.move(0, self.y())
                        if self.y() < 0:
                            self.move(self.x(), 0)
                        if self.x() > parent_rect.width() - self.width():
                            self.move(parent_rect.width() - self.width(), self.y())
                        if self.y() > parent_rect.height() - self.height():
                            self.move(self.x(), parent_rect.height() - self.height())
            max_iters -= 1


class JanelaExibicaoSimultanea(PadraoDialog):
    def __init__(self, graficos_disponiveis, parent=None):
        super().__init__(parent)
        self.graficos_disponiveis = graficos_disponiveis
        self.checkboxes = []
        self.labels_arrastaveis = {}

        self.setWindowTitle("Configurar Layout de Visualização")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Título da Composição:"))
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Visão Geral Músculo X")
        layout.addWidget(self.input_nome)

        # Main splitter or HBox for (Checkboxes) and (Workspace)
        hbox = QHBoxLayout()

        # Left side: Graph selection
        vbox_left = QVBoxLayout()
        vbox_left.addWidget(QLabel("Selecione de 2 a 4 gráficos:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(250)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)

        for grafico in graficos_disponiveis:
            cb = QCheckBox(grafico["label"])
            cb.setProperty("grafico_data", grafico)
            cb.stateChanged.connect(self._on_check_changed)
            self.checkboxes.append(cb)
            self.scroll_layout.addWidget(cb)

        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        vbox_left.addWidget(scroll)

        # Right side: Workspace
        vbox_right = QVBoxLayout()
        vbox_right.addWidget(
            QLabel("Mova os gráficos livremente pelo quadro para ajustar a exibição:")
        )

        self.workspace = QFrame()
        self.workspace.setStyleSheet(
            "background-color: white; border: 2px solid lightgray; border-radius: 5px;"
        )
        self.workspace.setMinimumSize(250, 250)

        vbox_right.addWidget(self.workspace)

        hbox.addLayout(vbox_left)
        hbox.addLayout(vbox_right)
        layout.addLayout(hbox)

        # Buttons
        botoes_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._validar_e_aceitar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_ok)
        botoes_layout.addWidget(btn_cancelar)
        layout.addLayout(botoes_layout)

    def _on_check_changed(self, state):
        cb = self.sender()
        nome = cb.text()

        checados = [c for c in self.checkboxes if c.isChecked()]
        if len(checados) > 4:
            QMessageBox.warning(
                self, "Limite Excedido", "Você pode selecionar no máximo 4 gráficos."
            )
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
            return

        if cb.isChecked():
            # Create and add DraggableSquare
            nome_curto = cb.property("grafico_data")["grafico"]
            lbl = DraggableSquare(
                nome_curto, cb.property("grafico_data"), self.workspace
            )
            self.labels_arrastaveis[nome] = lbl

            # Find an empty predefined position slot
            possible_positions = [(10, 10), (120, 10), (10, 120), (120, 120)]

            placed = False
            for px, py in possible_positions:
                is_free = True
                for other_lbl in self.labels_arrastaveis.values():
                    if other_lbl is not lbl:
                        ox, oy = other_lbl.x(), other_lbl.y()
                        if not (
                            px + 100 <= ox
                            or px >= ox + 100
                            or py + 100 <= oy
                            or py >= oy + 100
                        ):
                            is_free = False
                            break

                if is_free:
                    lbl.move(px, py)
                    placed = True
                    break

            if not placed:
                offset = len(self.labels_arrastaveis) * 15
                lbl.move(offset, offset)

            lbl.show()
        else:
            # Remove DraggableSquare
            if nome in self.labels_arrastaveis:
                lbl = self.labels_arrastaveis.pop(nome)
                lbl.setParent(None)
                lbl.deleteLater()

    def _validar_e_aceitar(self):
        checados = [c for c in self.checkboxes if c.isChecked()]
        if len(checados) < 2:
            QMessageBox.warning(
                self, "Seleção Inválida", "Selecione pelo menos 2 gráficos."
            )
            return

        self.accept()

    def get_nome(self):
        return self.input_nome.text().strip()

    def get_layout_config(self):
        items = []
        for nome, lbl in self.labels_arrastaveis.items():
            items.append(
                {
                    "arquivo": lbl.grafico_data["arquivo"],
                    "grafico": lbl.grafico_data["grafico"],
                    "label": f"{lbl.grafico_data['arquivo']} -> {lbl.grafico_data['grafico']}",
                    "x": lbl.pos().x(),
                    "y": lbl.pos().y(),
                }
            )

        N = len(items)
        if N == 2:
            dx = abs(items[0]["x"] - items[1]["x"])
            dy = abs(items[0]["y"] - items[1]["y"])
            if dx >= dy:
                items.sort(key=lambda i: i["x"])
                items[0].update({"row": 0, "col": 0})
                items[1].update({"row": 0, "col": 1})
            else:
                items.sort(key=lambda i: i["y"])
                items[0].update({"row": 0, "col": 0})
                items[1].update({"row": 1, "col": 0})

        elif N == 3:
            pairs = [(0, 1, 2), (0, 2, 1), (1, 2, 0)]
            min_dy = float("inf")
            pair_dy = None
            min_dx = float("inf")
            pair_dx = None
            for p in pairs:
                dy = abs(items[p[0]]["y"] - items[p[1]]["y"])
                dx = abs(items[p[0]]["x"] - items[p[1]]["x"])
                if dy < min_dy:
                    min_dy = dy
                    pair_dy = p
                if dx < min_dx:
                    min_dx = dx
                    pair_dx = p

            if min_dy <= min_dx:
                # piramide
                row_pair = [items[pair_dy[0]], items[pair_dy[1]]]
                solo = items[pair_dy[2]]
                row_pair.sort(key=lambda i: i["x"])

                if solo["y"] < min(i["y"] for i in row_pair):
                    solo.update({"row": 0, "col": 0, "colspan": 2})
                    row_pair[0].update({"row": 1, "col": 0})
                    row_pair[1].update({"row": 1, "col": 1})
                else:
                    row_pair[0].update({"row": 0, "col": 0})
                    row_pair[1].update({"row": 0, "col": 1})
                    solo.update({"row": 1, "col": 0, "colspan": 2})
            else:
                # L-Shape (orientacao da coluna)
                col_pair = [items[pair_dx[0]], items[pair_dx[1]]]
                solo = items[pair_dx[2]]
                col_pair.sort(key=lambda i: i["y"])

                if solo["x"] < min(i["x"] for i in col_pair):
                    solo.update({"row": 0, "col": 0, "rowspan": 2})
                    col_pair[0].update({"row": 0, "col": 1})
                    col_pair[1].update({"row": 1, "col": 1})
                else:
                    col_pair[0].update({"row": 0, "col": 0})
                    col_pair[1].update({"row": 1, "col": 0})
                    solo.update({"row": 0, "col": 1, "rowspan": 2})

        elif N == 4:
            items.sort(key=lambda i: i["y"])
            top = sorted(items[:2], key=lambda i: i["x"])
            bottom = sorted(items[2:], key=lambda i: i["x"])
            top[0].update({"row": 0, "col": 0})
            top[1].update({"row": 0, "col": 1})
            bottom[0].update({"row": 1, "col": 0})
            bottom[1].update({"row": 1, "col": 1})

        # Reconstruir como matrix com spans para a MainWindow
        max_row = max((i.get("row", 0) for i in items), default=0)
        max_col = max((i.get("col", 0) for i in items), default=0)

        config_matrix = []
        for r in range(max_row + 1):
            row_list = []
            for c in range(max_col + 1):
                found = next(
                    (i for i in items if i.get("row") == r and i.get("col") == c), None
                )
                if found:
                    node = {
                        "arquivo": found["arquivo"],
                        "grafico": found["grafico"],
                        "label": found["label"],
                        "colspan": found.get("colspan", 1),
                        "rowspan": found.get("rowspan", 1),
                    }
                    row_list.append(node)
                else:
                    row_list.append(None)

            while row_list and row_list[-1] is None:
                row_list.pop()

            config_matrix.append(row_list)

        return config_matrix


class JanelaLinhaReferencia(PadraoDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Linha de Referência")
        self.setMinimumSize(350, 430)

        self.layout_principal = QVBoxLayout(self)

        layout_titulo = QHBoxLayout()
        layout_titulo.addWidget(QLabel("Título da Referência:"))
        self.input_titulo = QLineEdit()
        self.input_titulo.setPlaceholderText("Ex: Tendência Linear")
        layout_titulo.addWidget(self.input_titulo)
        self.layout_principal.addLayout(layout_titulo)

        layout_termos = QHBoxLayout()
        layout_termos.addWidget(QLabel("Quantidade de termos (Grau + 1):"))
        self.spin_termos = QSpinBox()
        self.spin_termos.setRange(1, 20)
        self.spin_termos.setValue(4)  # Ex: grau 3 -> 4 termos
        self.spin_termos.valueChanged.connect(self._atualizar_entradas)
        layout_termos.addWidget(self.spin_termos)
        self.layout_principal.addLayout(layout_termos)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.widget_coefs = QWidget()
        self.layout_coefs = QVBoxLayout(self.widget_coefs)
        self.scroll.setWidget(self.widget_coefs)
        self.layout_principal.addWidget(self.scroll)

        self.entradas_coef = []
        self._atualizar_entradas()

        botoes = QHBoxLayout()
        btn_ok = QPushButton("Aplicar")
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addStretch()
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        self.layout_principal.addLayout(botoes)

    def accept(self):
        super().accept()

    def _atualizar_entradas(self):
        while self.layout_coefs.count():
            item = self.layout_coefs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.entradas_coef.clear()

        n_termos = self.spin_termos.value()
        for i in range(n_termos):
            linha = QHBoxLayout()
            label = QLabel(f"Coeficiente de x^{i}:")
            spin = QDoubleSpinBox()
            spin.setRange(-1000000, 1000000)
            spin.setDecimals(5)
            spin.setSingleStep(0.00001)
            spin.setValue(0.0)

            linha.addWidget(label)
            linha.addWidget(spin)

            w = QWidget()
            w.setLayout(linha)
            self.layout_coefs.addWidget(w)
            self.entradas_coef.append(spin)

        self.layout_coefs.addStretch()

    def get_titulo(self):
        return self.input_titulo.text().strip()

    def get_coeficientes(self):
        return [spin.value() for spin in self.entradas_coef]


class JanelaFiltro(PadraoDialog):
    """Janela de configuração e prévia de filtros Butterworth (Passa-Baixa/Passa-Alta).

    Permite ao usuário ajustar parâmetros do filtro e visualizar uma prévia em tempo real
    antes de aplicar as mudanças no gráfico principal.
    """

    def __init__(
        self,
        tipo_filtro,
        dados_x,
        dados_y,
        fs,
        unidade_x="",
        unidade_y="",
        titulo_grafico="",
        parent=None,
    ):
        super().__init__(parent)
        from processamento.limpeza import (
            filtro_passa_baixa,
            filtro_passa_alta,
            calcular_fc_winter,
        )

        self.tipo_filtro = tipo_filtro
        self.dados_x = dados_x
        self.dados_y = dados_y
        self.fs = fs
        self.unidade_x = unidade_x
        self.unidade_y = unidade_y
        self.titulo_grafico = titulo_grafico
        self.resultado_y = None  # Armazena o resultado final filtrado
        self._mostrando_original = False  # Estado do toggle antes/depois

        # Referências às funções de filtro
        self._filtro_passa_baixa = filtro_passa_baixa
        self._filtro_passa_alta = filtro_passa_alta
        self._calcular_fc_winter = calcular_fc_winter

        nome_filtro = "Passa-Baixa" if tipo_filtro == "passa_baixa" else "Passa-Alta"
        self.setWindowTitle(f"Filtro {nome_filtro}")
        self.setMinimumSize(750, 550)

        layout_principal = QVBoxLayout(self)

        #  Cabeçalho informativo
        label_info = QLabel(
            f"<b>Filtro Butterworth {nome_filtro}</b> — {titulo_grafico}"
        )
        label_info.setStyleSheet("font-size: 13px; padding: 4px;")
        layout_principal.addWidget(label_info)

        #  Preview do gráfico
        self.preview_plot = pg.PlotWidget()
        self.preview_plot.setMenuEnabled(False)
        self.preview_plot.setBackground("w")
        self.preview_plot.showGrid(x=True, y=True)
        self.preview_plot.setMinimumHeight(300)
        self.preview_plot.setContentsMargins(0, 0, 0, 15)
        layout_principal.addWidget(self.preview_plot)

        #  Info de frequência
        label_fs = QLabel(
            f"Freq. Amostragem: {self.fs:.1f} Hz  |  Nyquist: {self.fs/2:.1f} Hz"
        )
        label_fs.setStyleSheet("color: #555; padding: 2px 4px;")
        layout_principal.addWidget(label_fs)

        #  Painel de parâmetros (com borda)
        frame_params = QFrame()
        frame_params.setObjectName("frame_params")
        frame_params.setStyleSheet("""
            QFrame#frame_params { 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                padding: 8px; 
            }
            QFrame#frame_params QLabel { 
                border: none; 
            }
            QFrame#frame_params QDoubleSpinBox, 
            QFrame#frame_params QSpinBox { 
                border: 1px solid #999; 
                border-radius: 3px; 
                padding: 3px 6px; 
            }
        """)
        layout_params = QGridLayout(frame_params)

        # Frequência de corte (fc)
        layout_params.addWidget(QLabel("Frequência de Corte (Hz):"), 0, 0)
        self.spin_fc = QDoubleSpinBox()
        self.spin_fc.setRange(0.1, self.fs / 2 - 0.01)
        self.spin_fc.setValue(min(6.0, self.fs / 2 - 0.01))
        self.spin_fc.setDecimals(2)
        self.spin_fc.setSingleStep(0.5)
        self.spin_fc.setSuffix(" Hz")
        layout_params.addWidget(self.spin_fc, 0, 1)

        # Ordem do filtro
        label_ordem = QLabel("Ordem do Filtro:")
        layout_params.addWidget(label_ordem, 0, 2, Qt.AlignmentFlag.AlignRight)
        self.spin_ordem = QSpinBox()
        self.spin_ordem.setRange(1, 10)
        self.spin_ordem.setValue(4)
        layout_params.addWidget(self.spin_ordem, 0, 3)

        layout_principal.addWidget(frame_params)

        #  Botão Winter + Checkbox retificação (somente para passa-baixa)
        self.check_retificar = QCheckBox("Retificar sinal (|y|) antes de filtrar")
        self.check_retificar.setToolTip(
            "Aplica valor absoluto no sinal antes do filtro.\nÚtil para obter o envelope de sinais EMG."
        )
        #  Label de status (só para erros)
        self.label_status = QLabel("")
        self.label_status.setStyleSheet(
            "color: red; font-style: italic; padding: 2px 10px;"
        )
        self.label_status.setWordWrap(True)
        from PyQt6.QtWidgets import QSizePolicy

        self.label_status.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.label_status.hide()

        layout_opcoes = QHBoxLayout()

        if tipo_filtro == "passa_baixa":
            btn_winter = QPushButton("Calcular frequência ótima - Winter")
            btn_winter.setStyleSheet("padding: 4px 10px; background-color: #e8e8e8;")
            btn_winter.setToolTip(
                "Calcula a frequência de corte ótima pelo método de análise residual de Winter."
            )
            btn_winter.clicked.connect(self._calcular_winter)
            layout_opcoes.addWidget(btn_winter)

        layout_opcoes.addWidget(self.label_status)
        layout_opcoes.addStretch()
        layout_principal.addLayout(layout_opcoes)

        if tipo_filtro == "passa_baixa":
            layout_principal.addWidget(self.check_retificar)
        else:
            self.check_retificar.hide()

        #  Botões de ação
        layout_botoes = QHBoxLayout()

        # Botão Antes/Depois (toggle)
        self.btn_toggle = QPushButton("👁 Mostrar Original")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setStyleSheet("""
            QPushButton { padding: 6px 14px; }
            QPushButton:checked { background-color: #e0e0ff; }
        """)
        self.btn_toggle.clicked.connect(self._toggle_antes_depois)
        layout_botoes.addWidget(self.btn_toggle)

        layout_botoes.addStretch()

        # Botão Aplicar
        btn_aplicar = QPushButton("✅ Aplicar Filtro")
        btn_aplicar.setStyleSheet("padding: 6px 18px; font-weight: bold;")
        btn_aplicar.clicked.connect(self._confirmar_aplicacao)
        layout_botoes.addWidget(btn_aplicar)

        # Botão Cancelar
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("padding: 6px 14px;")
        btn_cancelar.clicked.connect(self.reject)
        layout_botoes.addWidget(btn_cancelar)

        layout_principal.addLayout(layout_botoes)

        # Conecta mudança de parâmetros para auto-preview
        self.spin_fc.valueChanged.connect(self._atualizar_preview)
        self.spin_ordem.valueChanged.connect(self._atualizar_preview)
        self.check_retificar.stateChanged.connect(self._atualizar_preview)

        # Plota o original e executa a primeira prévia
        self._atualizar_preview()

    def _executar_filtro(self):
        """Executa o filtro com os parâmetros atuais e retorna os dados filtrados."""
        fc = self.spin_fc.value()
        ordem = int(self.spin_ordem.value())

        # Retificação (abs) antes do filtro, se marcado (só disponível para passa-baixa)
        dados_y_input = self.dados_y
        if self.tipo_filtro == "passa_baixa" and self.check_retificar.isChecked():
            import pandas as pd

            dados_y_input = (
                self.dados_y.abs()
                if hasattr(self.dados_y, "abs")
                else pd.Series(np.abs(self.dados_y))
            )
            if hasattr(self.dados_y, "name"):
                dados_y_input.name = self.dados_y.name
            if hasattr(self.dados_y, "index"):
                dados_y_input.index = self.dados_y.index

        try:
            if self.tipo_filtro == "passa_baixa":
                resultado, _ = self._filtro_passa_baixa(
                    self.dados_x, dados_y_input, fc=fc, fs=self.fs, order=ordem
                )
            else:
                resultado, _ = self._filtro_passa_alta(
                    self.dados_x, dados_y_input, fc=fc, fs=self.fs, order=ordem
                )
            return resultado, None
        except Exception as e:
            return None, str(e)

    def _atualizar_preview(self):
        """Recalcula o filtro e atualiza o gráfico de prévia."""
        self.preview_plot.clear()

        x_arr = (
            self.dados_x.values
            if hasattr(self.dados_x, "values")
            else np.array(self.dados_x)
        )
        y_arr = (
            self.dados_y.values
            if hasattr(self.dados_y, "values")
            else np.array(self.dados_y)
        )

        # Plota o sinal original (cinza)
        pen_original = pg.mkPen(color="#AAAAAA", width=1.5)
        self.preview_plot.plot(x_arr, y_arr, pen=pen_original, name="Original")

        # Executa o filtro
        resultado, erro = self._executar_filtro()

        if erro:
            self.label_status.setText(f"⚠️ Erro: {erro}")
            self.label_status.show()
            self.resultado_y = None
            return

        self.label_status.hide()

        self.resultado_y = resultado
        y_filtrado = (
            resultado.values if hasattr(resultado, "values") else np.array(resultado)
        )

        # Plota o sinal filtrado (azul)
        pen_filtrado = pg.mkPen(color="#2196F3", width=2)
        self.preview_plot.plot(x_arr, y_filtrado, pen=pen_filtrado, name="Filtrado")

        # Labels dos eixos
        import re

        lbl_x = (
            re.sub(r"\s*\[.*?\]$", "", str(self.titulo_grafico))
            if self.titulo_grafico
            else "X"
        )
        lbl_y = self.unidade_y if self.unidade_y else "Y"

        eixo_x_str = f"({self.unidade_x})" if self.unidade_x else ""
        eixo_y_str = f"({self.unidade_y})" if self.unidade_y else ""

        self.preview_plot.setLabel("bottom", f"Eixo X {eixo_x_str}")
        self.preview_plot.setLabel("left", f"Eixo Y {eixo_y_str}")

        nome_filtro = (
            "Passa-Baixa" if self.tipo_filtro == "passa_baixa" else "Passa-Alta"
        )
        self.preview_plot.setTitle(
            f"Prévia — {nome_filtro} (fc={self.spin_fc.value():.1f} Hz, ordem={self.spin_ordem.value()})"
        )

        # Legenda
        if self.preview_plot.plotItem.legend is None:
            self.preview_plot.addLegend()

        self.label_status.hide()

        # Reseta o toggle
        self.btn_toggle.setChecked(False)
        self._mostrando_original = False
        self.btn_toggle.setText("👁 Mostrar Original")

    def _toggle_antes_depois(self):
        """Alterna entre mostrar somente o original ou a prévia com ambos."""
        self._mostrando_original = self.btn_toggle.isChecked()
        self.preview_plot.clear()

        x_arr = (
            self.dados_x.values
            if hasattr(self.dados_x, "values")
            else np.array(self.dados_x)
        )
        y_arr = (
            self.dados_y.values
            if hasattr(self.dados_y, "values")
            else np.array(self.dados_y)
        )

        eixo_x_str = f"({self.unidade_x})" if self.unidade_x else ""
        eixo_y_str = f"({self.unidade_y})" if self.unidade_y else ""

        if self._mostrando_original:
            # Mostra somente o original
            pen_original = pg.mkPen(color="#F44336", width=2)
            self.preview_plot.plot(x_arr, y_arr, pen=pen_original, name="Original")
            self.preview_plot.setTitle(f"Sinal Original — {self.titulo_grafico}")
            self.btn_toggle.setText("👁 Mostrar Prévia")
        else:
            # Mostra ambos (original em cinza + filtrado em azul)
            pen_original = pg.mkPen(color="#AAAAAA", width=1.5)
            self.preview_plot.plot(x_arr, y_arr, pen=pen_original, name="Original")

            if self.resultado_y is not None:
                y_filtrado = (
                    self.resultado_y.values
                    if hasattr(self.resultado_y, "values")
                    else np.array(self.resultado_y)
                )
                pen_filtrado = pg.mkPen(color="#2196F3", width=2)
                self.preview_plot.plot(
                    x_arr, y_filtrado, pen=pen_filtrado, name="Filtrado"
                )

            nome_filtro = (
                "Passa-Baixa" if self.tipo_filtro == "passa_baixa" else "Passa-Alta"
            )
            self.preview_plot.setTitle(
                f"Prévia — {nome_filtro} (fc={self.spin_fc.value():.1f} Hz, ordem={self.spin_ordem.value()})"
            )
            self.btn_toggle.setText("👁 Mostrar Original")

        self.preview_plot.setLabel("bottom", f"Eixo X {eixo_x_str}")
        self.preview_plot.setLabel("left", f"Eixo Y {eixo_y_str}")

        if self.preview_plot.plotItem.legend is None:
            self.preview_plot.addLegend()

    def _calcular_winter(self):
        """Calcula a frequência ótima pelo Método de Winter e ajusta o spinbox."""
        y_arr = (
            self.dados_y.values
            if hasattr(self.dados_y, "values")
            else np.array(self.dados_y)
        )
        ordem = int(self.spin_ordem.value())

        try:
            fc_otima, _, _ = self._calcular_fc_winter(y_arr, self.fs, order=ordem)

            # Arredonda para 1 casa decimal
            fc_otima = round(fc_otima, 1)

            # Ajusta o spinbox (dispara auto-preview via valueChanged)
            self.spin_fc.setValue(fc_otima)

        except ValueError as e:
            QMessageBox.warning(self, "Aviso", str(e))

    def _confirmar_aplicacao(self):
        """Recalcula com os parâmetros finais e aceita."""
        resultado, erro = self._executar_filtro()
        if erro:
            QMessageBox.critical(
                self, "Erro", f"Não foi possível aplicar o filtro:\n{erro}"
            )
            return
        self.resultado_y = resultado
        self.accept()

    def get_resultado(self):
        """Retorna os dados filtrados e os parâmetros usados."""
        return {
            "dados_filtrados": self.resultado_y,
            "fc": self.spin_fc.value(),
            "ordem": int(self.spin_ordem.value()),
            "tipo": self.tipo_filtro,
            "retificar": self.tipo_filtro == "passa_baixa"
            and self.check_retificar.isChecked(),
        }


class JanelaOffset(PadraoDialog):
    def __init__(self, df, colunas_selecionadas, col_tempo, parent=None):
        super().__init__(parent)
        self.df = df
        self.colunas_selecionadas = colunas_selecionadas
        self.col_tempo = col_tempo

        from PyQt6.QtCore import QTimer

        self.timer_plot = QTimer(self)
        self.timer_plot.setSingleShot(True)
        self.timer_plot.timeout.connect(self._executar_atualizacao_plot)
        self._y_refs = {}

        self.setWindowTitle("Pré-visualização do Offset")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        layout.addWidget(self.plot_widget)

        # Controles
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(QLabel("Eixo X:"))

        from PyQt6.QtWidgets import QDoubleSpinBox, QButtonGroup

        self.grp_x = QButtonGroup(self)
        self.radio_tempo = QRadioButton("Tempo")
        self.radio_frames = QRadioButton("Frames")
        self.grp_x.addButton(self.radio_tempo)
        self.grp_x.addButton(self.radio_frames)
        if self.col_tempo:
            self.radio_tempo.setChecked(True)
        else:
            self.radio_frames.setChecked(True)
        self.radio_tempo.toggled.connect(self._mudar_eixo_x)
        controls_layout.addWidget(self.radio_tempo)
        controls_layout.addWidget(self.radio_frames)

        controls_layout.addSpacing(20)

        controls_layout.addWidget(QLabel("Offset (subtrair):"))

        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-1e9, 1e9)
        self.spin_offset.setDecimals(4)
        self.spin_offset.setValue(0.0)
        self.spin_offset.valueChanged.connect(self._atualizar_plot)
        controls_layout.addWidget(self.spin_offset)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Opções de salvamento
        options_layout = QVBoxLayout()
        self.grp_save = QButtonGroup(self)
        self.radio_novo = QRadioButton("Criar novas variáveis (Preservar originais)")
        self.radio_sobre = QRadioButton("Substituir definitivo no arquivo original")
        self.grp_save.addButton(self.radio_novo)
        self.grp_save.addButton(self.radio_sobre)
        self.radio_sobre.setChecked(True)

        options_layout.addWidget(self.radio_sobre)
        options_layout.addWidget(self.radio_novo)
        layout.addLayout(options_layout)

        self.check_criar_graficos = QCheckBox(
            "Criar gráficos para novas variáveis na árvore"
        )
        self.check_criar_graficos.setChecked(False)
        self.check_criar_graficos.setVisible(False)
        layout.addWidget(self.check_criar_graficos)

        self.radio_novo.toggled.connect(self.check_criar_graficos.setVisible)

        # Botões
        botoes = QHBoxLayout()
        btn_ok = QPushButton("Aplicar")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addLayout(botoes)

        self.curvas_originais = {}
        self.curvas_offset = {}

        self._inicializar_plot()

    def _inicializar_plot(self):
        import pandas as pd

        cores = ["b", "r", "darkgreen", "purple", "brown", "k", "darkorange"]
        t_full = (
            self.df[self.col_tempo].values
            if self.col_tempo
            else np.arange(len(self.df))
        )

        for i, col in enumerate(self.colunas_selecionadas):
            y_full = self.df[col].values
            mask = ~pd.isna(y_full)
            if self.col_tempo:
                mask = mask & ~pd.isna(t_full)

            y = y_full[mask]
            t = t_full[mask]
            cor = cores[i % len(cores)]

            # Original (claro/tracejado)
            pen_orig = pg.mkPen(color=cor, width=1, style=Qt.PenStyle.DashLine)
            self.curvas_originais[col] = self.plot_widget.plot(
                t, y, pen=pen_orig, name=f"{col} (Original)"
            )

            # Offset (em destaque)
            pen_off = pg.mkPen(color=cor, width=2)
            self.curvas_offset[col] = self.plot_widget.plot(
                t, y, pen=pen_off, name=f"{col} (Offset)"
            )

    def _atualizar_plot(self):
        self.timer_plot.start(100)

    def _executar_atualizacao_plot(self):
        import pandas as pd

        offset = self.spin_offset.value()
        t_full = (
            self.df[self.col_tempo].values
            if self.col_tempo
            else np.arange(len(self.df))
        )

        for col in self.colunas_selecionadas:
            y_full = self.df[col].values
            mask = ~pd.isna(y_full)
            if self.col_tempo:
                mask = mask & ~pd.isna(t_full)

            y = (y_full[mask] - offset).copy()
            x = self.curvas_offset[col].xData
            self._y_refs[col] = y  # Keep strong reference
            self.curvas_offset[col].setData(x=x, y=y)

    def _mudar_eixo_x(self):
        import pandas as pd

        modo = "Tempo" if self.radio_tempo.isChecked() else "Frames"
        t_full = (
            self.df[self.col_tempo].values
            if self.col_tempo
            else np.arange(len(self.df))
        )
        t_frames = np.arange(len(self.df))

        for col in self.colunas_selecionadas:
            y_full = self.df[col].values
            mask = ~pd.isna(y_full)
            if self.col_tempo:
                mask = mask & ~pd.isna(t_full)

            x_data = (
                t_full[mask] if modo == "Tempo" and self.col_tempo else t_frames[mask]
            )

            self.curvas_originais[col].setData(x=x_data)
            self.curvas_offset[col].setData(x=x_data)

        self.plot_widget.autoRange()

    def get_resultados(self):
        return {
            "offset": self.spin_offset.value(),
            "sobrescrever": self.radio_sobre.isChecked(),
            "criar_graficos": self.check_criar_graficos.isChecked(),
        }


class JanelaRecorteTemporal(PadraoDialog):
    def __init__(
        self, df, categorias_selecionadas, colunas_por_cat, col_tempo, parent=None
    ):
        super().__init__(parent)
        self.df = df
        self.categorias = categorias_selecionadas
        self.colunas_por_cat = colunas_por_cat
        self.col_tempo = col_tempo

        self.setWindowTitle("Recorte Temporal (Trim)")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        self.layout_graficos = pg.GraphicsLayoutWidget()
        self.layout_graficos.setBackground("w")
        layout.addWidget(self.layout_graficos)

        self.plots = []
        self.linhas_inicio = []
        self.linhas_fim = []

        import pandas as pd

        t_full = (
            self.df[self.col_tempo].values
            if self.col_tempo
            else np.arange(len(self.df))
        )

        # Calcula t_min and t_max ignorando NaNs
        valid_t = t_full[~pd.isna(t_full)]
        t_min, t_max = float(np.min(valid_t)), float(np.max(valid_t))
        self.t_atual = t_full

        cores = ["k"]

        self.curvas_trim = []

        # plota cada categoria
        for i, cat in enumerate(self.categorias):
            p = self.layout_graficos.addPlot(title=cat)
            p.showGrid(x=True, y=True)
            p.setMouseEnabled(x=False, y=False)
            p.hideButtons()
            p.setMenuEnabled(False)
            if i > 0:
                p.setXLink(self.plots[0])
            self.layout_graficos.nextRow()

            colunas = self.colunas_por_cat[cat]
            for j, col in enumerate(colunas):
                if col in self.df.columns:
                    y_full = self.df[col].values
                    mask = ~pd.isna(y_full)
                    if self.col_tempo:
                        mask = mask & ~pd.isna(t_full)
                    y = y_full[mask]
                    t_plot = t_full[mask]

                    cor = cores[j % len(cores)]
                    item = p.plot(t_plot, y, pen=pg.mkPen(color=cor, width=1))
                    self.curvas_trim.append((col, item))

            linha_ini = pg.InfiniteLine(
                pos=t_min,
                angle=90,
                movable=True,
                pen=pg.mkPen("g", width=2),
                bounds=[t_min, t_max],
            )
            linha_fim = pg.InfiniteLine(
                pos=t_max,
                angle=90,
                movable=True,
                pen=pg.mkPen("r", width=2),
                bounds=[t_min, t_max],
            )

            linha_ini.sigPositionChanged.connect(self._on_linha_ini_movida)
            linha_fim.sigPositionChanged.connect(self._on_linha_fim_movida)

            p.addItem(linha_ini)
            p.addItem(linha_fim)

            self.plots.append(p)
            self.linhas_inicio.append(linha_ini)
            self.linhas_fim.append(linha_fim)

        self._updating_lines = False

        # Controles
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Eixo X:"))
        from PyQt6.QtWidgets import QDoubleSpinBox, QCheckBox, QButtonGroup

        self.grp_x = QButtonGroup(self)
        self.radio_tempo = QRadioButton("Tempo")
        self.radio_frames = QRadioButton("Frames")
        self.grp_x.addButton(self.radio_tempo)
        self.grp_x.addButton(self.radio_frames)
        if self.col_tempo:
            self.radio_tempo.setChecked(True)
        else:
            self.radio_frames.setChecked(True)
        self.radio_tempo.toggled.connect(self._mudar_eixo_x)
        controls.addWidget(self.radio_tempo)
        controls.addWidget(self.radio_frames)

        controls.addWidget(QLabel("Corte Inicial:"))
        self.spin_ini = QDoubleSpinBox()
        self.spin_ini.setRange(t_min, t_max)
        self.spin_ini.setValue(t_min)
        self.spin_ini.setDecimals(4)
        self.spin_ini.setSingleStep(0.1)
        self.spin_ini.valueChanged.connect(self._on_spin_ini_changed)
        controls.addWidget(self.spin_ini)

        controls.addWidget(QLabel("Corte Final:"))
        self.spin_fim = QDoubleSpinBox()
        self.spin_fim.setRange(t_min, t_max)
        self.spin_fim.setValue(t_max)
        self.spin_fim.setDecimals(4)
        self.spin_fim.setSingleStep(0.1)
        self.spin_fim.valueChanged.connect(self._on_spin_fim_changed)
        controls.addWidget(self.spin_fim)

        controls.addStretch()
        layout.addLayout(controls)

        self.check_deslocar = QCheckBox("Deslocar tempo cortado para 0s")
        self.check_deslocar.setChecked(True)
        layout.addWidget(self.check_deslocar)

        self.grp_save = QButtonGroup(self)
        self.radio_novo = QRadioButton("Salvar como Novo Arquivo")
        self.radio_sobre = QRadioButton("Substituir Definitivo no arquivo atual")
        self.grp_save.addButton(self.radio_novo)
        self.grp_save.addButton(self.radio_sobre)
        self.radio_sobre.setChecked(True)
        layout.addWidget(self.radio_novo)
        layout.addWidget(self.radio_sobre)

        botoes = QHBoxLayout()
        btn_ok = QPushButton("Aplicar Recorte")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addLayout(botoes)

    def _on_linha_ini_movida(self, line):
        if self._updating_lines:
            return
        self._updating_lines = True
        val = line.value()

        # Nao permite que linha inicio ultrapasse linha fim
        if self.linhas_fim and val > self.linhas_fim[0].value():
            val = self.linhas_fim[0].value()
            line.setValue(val)

        self.spin_ini.setValue(val)
        for l in self.linhas_inicio:
            if l != line:
                l.setValue(val)
        self._updating_lines = False

    def _on_linha_fim_movida(self, line):
        if self._updating_lines:
            return
        self._updating_lines = True
        val = line.value()

        # Nao permite que linha fim ultrapasse linha inicio
        if self.linhas_inicio and val < self.linhas_inicio[0].value():
            val = self.linhas_inicio[0].value()
            line.setValue(val)

        self.spin_fim.setValue(val)
        for l in self.linhas_fim:
            if l != line:
                l.setValue(val)
        self._updating_lines = False

    def _on_spin_ini_changed(self, val):
        if self._updating_lines:
            return
        self._updating_lines = True

        if self.linhas_fim and val > self.linhas_fim[0].value():
            val = self.linhas_fim[0].value()
            self.spin_ini.setValue(val)

        for l in self.linhas_inicio:
            l.setValue(val)
        self._updating_lines = False

    def _on_spin_fim_changed(self, val):
        if self._updating_lines:
            return
        self._updating_lines = True

        if self.linhas_inicio and val < self.linhas_inicio[0].value():
            val = self.linhas_inicio[0].value()
            self.spin_fim.setValue(val)

        for l in self.linhas_fim:
            l.setValue(val)
        self._updating_lines = False

    def _mudar_eixo_x(self):
        import pandas as pd

        modo = "Tempo" if self.radio_tempo.isChecked() else "Frames"
        t_full = (
            self.df[self.col_tempo].values
            if self.col_tempo
            else np.arange(len(self.df))
        )
        t_frames = np.arange(len(self.df))

        self.t_atual = t_full if modo == "Tempo" and self.col_tempo else t_frames
        valid_t = self.t_atual[~pd.isna(self.t_atual)]
        t_min, t_max = float(np.min(valid_t)), float(np.max(valid_t))

        # Desabilita os sinais temporariamente
        self._updating_lines = True

        self.spin_ini.setRange(t_min, t_max)
        self.spin_fim.setRange(t_min, t_max)

        # Escala valores atuais baseada na proporção
        if len(valid_t) > 1:
            ratio_ini = (self.linhas_inicio[0].value() - self.spin_ini.minimum()) / max(
                1, (self.spin_ini.maximum() - self.spin_ini.minimum())
            )
            ratio_fim = (self.linhas_fim[0].value() - self.spin_fim.minimum()) / max(
                1, (self.spin_fim.maximum() - self.spin_fim.minimum())
            )
        else:
            ratio_ini, ratio_fim = 0, 1

        new_ini = t_min + ratio_ini * (t_max - t_min)
        new_fim = t_min + ratio_fim * (t_max - t_min)

        self.spin_ini.setValue(new_ini)
        self.spin_fim.setValue(new_fim)

        for l in self.linhas_inicio:
            l.setValue(new_ini)
            l.setBounds([t_min, t_max])
        for l in self.linhas_fim:
            l.setValue(new_fim)
            l.setBounds([t_min, t_max])

        for col, item in self.curvas_trim:
            y_full = self.df[col].values
            mask = ~pd.isna(y_full)
            if self.col_tempo:
                mask = mask & ~pd.isna(t_full)

            x_data = (
                t_full[mask] if modo == "Tempo" and self.col_tempo else t_frames[mask]
            )
            item.setData(x=x_data, y=y_full[mask])

        self._updating_lines = False

        for p in self.plots:
            p.autoRange()

    def get_resultados(self):
        return {
            "t_ini": self.spin_ini.value(),
            "t_fim": self.spin_fim.value(),
            "tipo_x": "Tempo" if self.radio_tempo.isChecked() else "Frames",
            "deslocar_0": self.check_deslocar.isChecked(),
            "sobrescrever": self.radio_sobre.isChecked(),
        }
