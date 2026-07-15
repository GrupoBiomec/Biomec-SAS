from ui.utils import PadraoDialog
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QCheckBox,
    QMessageBox,
    QScrollArea,
    QWidget,
    QSpinBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
)
from PyQt6.QtCore import Qt


class CollapsibleBox(QWidget):
    """Um widget customizado expansível com um botão de setinha."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(f"▶ {title}")
        self.toggle_button.setStyleSheet(
            "text-align: left; font-weight: bold; padding: 8px; font-size: 13px;"
        )
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)

        self.content_area = QFrame()
        self.content_area.setStyleSheet(
            "QFrame { background-color: #f9f9f9; border-radius: 4px; border: 1px solid #ddd; margin-left: 10px; margin-right: 10px; }"
        )
        self.content_area.setVisible(False)
        self.content_layout = QVBoxLayout(self.content_area)

        self.toggle_button.toggled.connect(self._on_toggle)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 10)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)

    def _on_toggle(self, checked):
        title = self.toggle_button.text()[2:]
        self.toggle_button.setText(f"▼ {title}" if checked else f"▶ {title}")
        self.content_area.setVisible(checked)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class FormularioBase(QWidget):
    """Classe base para os formulários de operações."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(5, 5, 5, 5)

        # Cabeçalho com botão excluir
        topo_layout = QHBoxLayout()
        topo_layout.addStretch()
        btn_remover = QPushButton("Excluir")
        btn_remover.setStyleSheet("color: red; padding: 2px 8px;")
        btn_remover.clicked.connect(self.deleteLater)
        topo_layout.addWidget(btn_remover)
        self.layout_principal.addLayout(topo_layout)

        # Container para os inputs
        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout_principal.addLayout(self.form_layout)

        # Campo comum a todas as operações
        self.input_nova_var = QLineEdit()
        self.input_nova_var.setMinimumWidth(200)
        self.form_layout.addRow("Nome da nova variável:", self.input_nova_var)

        # Separador
        linha = QFrame()
        linha.setFrameShape(QFrame.Shape.HLine)
        linha.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout_principal.addWidget(linha)

    def validar_base(self):
        return bool(self.input_nova_var.text().strip())


class FormAritmetica(FormularioBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_op = QComboBox()
        self.combo_op.setMinimumWidth(200)
        self.combo_op.addItems(["+", "-", "*", "/"])
        self.input_var_a = QLineEdit()
        self.input_var_a.setMinimumWidth(200)
        self.input_var_a.setPlaceholderText("Nome esperado")

        self.combo_tipo_b = QComboBox()
        self.combo_tipo_b.setMinimumWidth(200)
        self.combo_tipo_b.addItems(["Variável", "Constante"])

        self.input_var_b = QLineEdit()
        self.input_var_b.setMinimumWidth(200)
        self.input_var_b.setPlaceholderText("Nome esperado")

        from PyQt6.QtWidgets import QDoubleSpinBox

        self.spin_const_b = QDoubleSpinBox()
        self.spin_const_b.setMinimumWidth(200)
        self.spin_const_b.setRange(-999999999, 999999999)
        self.spin_const_b.setDecimals(4)

        self.form_layout.addRow("Operação:", self.combo_op)
        self.form_layout.addRow("Variável A:", self.input_var_a)
        self.form_layout.addRow("Tipo do 2º Operando:", self.combo_tipo_b)
        self.form_layout.addRow("Variável B:", self.input_var_b)
        self.form_layout.addRow("Constante B:", self.spin_const_b)

        def toggle_b():
            is_var = self.combo_tipo_b.currentIndex() == 0
            self.input_var_b.setVisible(is_var)
            self.form_layout.labelForField(self.input_var_b).setVisible(is_var)
            self.spin_const_b.setVisible(not is_var)
            self.form_layout.labelForField(self.spin_const_b).setVisible(not is_var)

        self.combo_tipo_b.currentIndexChanged.connect(toggle_b)
        toggle_b()

    def validar_dados(self):
        if not self.validar_base():
            return False
        if not self.input_var_a.text().strip():
            return False
        if self.combo_tipo_b.currentIndex() == 0:
            if not self.input_var_b.text().strip():
                return False
        return True

    def obter_dados(self):
        dados = {
            "tipo": "Aritmética Básica",
            "nome_nova": self.input_nova_var.text().strip(),
            "operador": self.combo_op.currentText(),
            "var_a": self.input_var_a.text().strip(),
            "is_const_b": self.combo_tipo_b.currentIndex() == 1,
        }
        if dados["is_const_b"]:
            dados["val_b"] = self.spin_const_b.value()
        else:
            dados["var_b"] = self.input_var_b.text().strip()
        return dados


class FormTrigonometria(FormularioBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_op = QComboBox()
        self.combo_op.setMinimumWidth(200)
        self.combo_op.addItems(["sin", "cos", "tan"])
        self.input_var = QLineEdit()
        self.input_var.setMinimumWidth(200)
        self.input_var.setPlaceholderText("Nome esperado")

        self.form_layout.addRow("Função:", self.combo_op)
        self.form_layout.addRow("Variável Angular:", self.input_var)

    def validar_dados(self):
        if not self.validar_base():
            return False
        return bool(self.input_var.text().strip())

    def obter_dados(self):
        return {
            "tipo": "Trigonometria",
            "nome_nova": self.input_nova_var.text().strip(),
            "operador": self.combo_op.currentText(),
            "var": self.input_var.text().strip(),
        }


class FormCalculoEscalar(FormularioBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_op = QComboBox()
        self.combo_op.setMinimumWidth(200)
        self.combo_op.addItems(
            [
                "integral",
                "derivada 1a",
                "derivada 2a",
                "modulo",
                "raiz quadrada",
                "inverso",
            ]
        )
        self.input_var_principal = QLineEdit()
        self.input_var_principal.setMinimumWidth(200)
        self.input_var_principal.setPlaceholderText("Nome esperado")
        self.input_var_tempo = QLineEdit()
        self.input_var_tempo.setMinimumWidth(200)
        self.input_var_tempo.setPlaceholderText("Nome esperado")

        self.form_layout.addRow("Operação:", self.combo_op)
        self.form_layout.addRow("Variável Principal:", self.input_var_principal)
        self.form_layout.addRow("Var. Tempo (X):", self.input_var_tempo)

    def validar_dados(self):
        if not self.validar_base():
            return False
        if not self.input_var_principal.text().strip():
            return False
        if self.combo_op.currentText() in ["integral", "derivada 1a", "derivada 2a"]:
            if not self.input_var_tempo.text().strip():
                return False
        return True

    def obter_dados(self):
        return {
            "tipo": "Cálculo e Funções Escalares",
            "nome_nova": self.input_nova_var.text().strip(),
            "operador": self.combo_op.currentText(),
            "var_principal": self.input_var_principal.text().strip(),
            "var_tempo": self.input_var_tempo.text().strip(),
        }


class FormAngulos(FormularioBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.combo_unidade = QComboBox()
        self.combo_unidade.setMinimumWidth(200)
        self.combo_unidade.addItems(["graus", "radianos"])
        self.combo_modo = QComboBox()
        self.combo_modo.setMinimumWidth(200)
        self.combo_modo.addItems(
            ["Ângulo Relativo (3 pontos)", "Ângulo entre Vetores (4 pontos)"]
        )

        self.input_p1 = QLineEdit()
        self.input_p1.setMinimumWidth(200)
        self.input_p1.setPlaceholderText("Nome esperado")
        self.input_p2 = QLineEdit()
        self.input_p2.setMinimumWidth(200)
        self.input_p2.setPlaceholderText("Nome esperado")
        self.input_p3 = QLineEdit()
        self.input_p3.setMinimumWidth(200)
        self.input_p3.setPlaceholderText("Nome esperado")
        self.input_p4 = QLineEdit()
        self.input_p4.setMinimumWidth(200)
        self.input_p4.setPlaceholderText("Nome esperado")

        self.form_layout.addRow("Unidade:", self.combo_unidade)
        self.form_layout.addRow("Modo:", self.combo_modo)
        self.form_layout.addRow("Ponto 1:", self.input_p1)
        self.form_layout.addRow("Ponto 2 (Vértice):", self.input_p2)
        self.form_layout.addRow("Ponto 3:", self.input_p3)
        self.form_layout.addRow("Ponto 4 (Vetores):", self.input_p4)

        def toggle_p4():
            visivel = "4" in self.combo_modo.currentText()
            self.input_p4.setVisible(visivel)
            self.form_layout.labelForField(self.input_p4).setVisible(visivel)

        self.combo_modo.currentIndexChanged.connect(toggle_p4)
        toggle_p4()

    def validar_dados(self):
        if not self.validar_base():
            return False
        if not (
            self.input_p1.text().strip()
            and self.input_p2.text().strip()
            and self.input_p3.text().strip()
        ):
            return False
        if "4" in self.combo_modo.currentText() and not self.input_p4.text().strip():
            return False
        return True

    def obter_dados(self):
        modo = "relativo" if "3" in self.combo_modo.currentText() else "vetores"
        dados = {
            "tipo": "Definir Ângulos",
            "nome_nova": self.input_nova_var.text().strip(),
            "unidade": self.combo_unidade.currentText(),
            "modo": modo,
            "p1": self.input_p1.text().strip(),
            "p2": self.input_p2.text().strip(),
            "p3": self.input_p3.text().strip(),
        }
        if modo == "vetores":
            dados["p4"] = self.input_p4.text().strip()
        return dados


class FormGrafico(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 10)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout = QVBoxLayout(self.frame)

        h_header = QHBoxLayout()
        lbl_titulo = QLabel("<b>Configuração de Gráfico</b>")
        btn_remover = QPushButton("Remover")
        btn_remover.clicked.connect(self.deleteLater)
        h_header.addWidget(lbl_titulo)
        h_header.addStretch()
        h_header.addWidget(btn_remover)
        self.frame_layout.addLayout(h_header)

        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.frame_layout.addLayout(self.form_layout)
        self.layout_principal.addWidget(self.frame)

        self.input_nome = QLineEdit()
        self.input_nome.setMinimumWidth(200)
        self.input_nome.setPlaceholderText("(opcional)")

        self.combo_tipo = QComboBox()
        self.combo_tipo.setMinimumWidth(200)
        self.combo_tipo.addItems(["Linha", "Dispersão"])

        self.input_eixo_x = QLineEdit()
        self.input_eixo_x.setMinimumWidth(200)
        self.input_eixo_x.setText("time")
        self.input_eixo_x.setPlaceholderText("Variável X esperada")

        self.input_eixo_y = QLineEdit()
        self.input_eixo_y.setMinimumWidth(200)
        self.input_eixo_y.setPlaceholderText("Variável Y esperada")

        self.form_layout.addRow("Nome do novo gráfico:", self.input_nome)
        self.form_layout.addRow("Tipo do gráfico:", self.combo_tipo)
        self.form_layout.addRow("Eixo X esperado:", self.input_eixo_x)
        self.form_layout.addRow("Eixo Y esperado:", self.input_eixo_y)

    def validar_dados(self):
        return bool(
            self.input_eixo_y.text().strip() and self.input_eixo_x.text().strip()
        )

    def obter_dados(self):
        return {
            "tipo": "Criar Gráfico",
            "nome_grafico": self.input_nome.text().strip(),
            "tipo_grafico": self.combo_tipo.currentText(),
            "eixo_x": self.input_eixo_x.text().strip(),
            "eixo_y": self.input_eixo_y.text().strip(),
        }


class SecaoExpansivel(CollapsibleBox):
    """Caixa expansível que contém uma lista de formulários de um mesmo tipo."""

    def __init__(self, titulo, classe_formulario, parent=None):
        super().__init__(titulo, parent)
        self.classe_formulario = classe_formulario

        # Container interno para os formulários
        self.container_forms = QWidget()
        self.layout_forms = QVBoxLayout(self.container_forms)
        self.layout_forms.setContentsMargins(0, 0, 0, 0)
        self.addWidget(self.container_forms)

        # Botão de adicionar no final da seção
        self.btn_add = QPushButton(f"+ Adicionar {titulo}")
        self.btn_add.setStyleSheet("margin: 5px; padding: 5px;")
        self.btn_add.clicked.connect(self.adicionar_formulario)
        self.addWidget(self.btn_add)

    def adicionar_formulario(self, dados_iniciais=None):
        form = self.classe_formulario()
        self.layout_forms.addWidget(form)
        return form

    def obter_dados(self):
        dados_ops = []
        for i in range(self.layout_forms.count()):
            widget = self.layout_forms.itemAt(i).widget()
            if widget is not None and not widget.isHidden():
                dados_ops.append(widget)
        return dados_ops

    def limpar(self):
        while self.layout_forms.count():
            child = self.layout_forms.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class JanelaCriarScript(PadraoDialog):
    def __init__(self, estado, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.setWindowTitle("Criar Novo Script")
        self.setMinimumSize(650, 750)

        layout_principal = QVBoxLayout(self)

        # --- 1. Informações Gerais ---
        grupo_geral = QGroupBox("Informações Gerais")
        form_geral = QFormLayout(grupo_geral)

        self.input_titulo = QLineEdit()
        form_geral.addRow("Título do Script:", self.input_titulo)

        self.combo_salvamento = QComboBox()
        self.combo_salvamento.addItems(
            ["Substituir arquivo original", "Salvar como novo arquivo"]
        )
        form_geral.addRow("Modo de Salvamento:", self.combo_salvamento)

        h_modelo = QHBoxLayout()
        self.combo_modelo = QComboBox()
        self.combo_modelo.addItem("Nenhum")  # Default
        self.combo_modelo.addItems(list(self.estado.guarda_arquivos.keys()))
        btn_modelo = QPushButton("Puxar Modelo")
        btn_modelo.clicked.connect(self.usar_modelo)
        h_modelo.addWidget(self.combo_modelo)
        h_modelo.addWidget(btn_modelo)
        form_geral.addRow("Usar Arquivo Modelo:", h_modelo)

        self.chk_plotar = QCheckBox("Plotar automaticamente as novas variáveis criadas")
        form_geral.addRow("", self.chk_plotar)

        layout_principal.addWidget(grupo_geral)

        # --- 2. Áreas Expansíveis (Formulário do Script) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        # Recorte Temporal (Widget Especial, pois só pode ter 1)
        self.secao_recorte = CollapsibleBox("Recorte Temporal")
        self.chk_habilitar_recorte = QCheckBox("Habilitar Recorte Temporal")
        self.secao_recorte.addWidget(self.chk_habilitar_recorte)

        self.form_recorte = QWidget()
        layout_form_recorte = QFormLayout(self.form_recorte)
        layout_form_recorte.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        layout_form_recorte.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        self.combo_base = QComboBox()
        self.combo_base.setMinimumWidth(200)
        self.combo_base.addItems(["Tempo (s)", "Frames"])  # Mudança p/ default Tempo
        layout_form_recorte.addRow("Base do Recorte:", self.combo_base)

        self.spin_inicio = QDoubleSpinBox()
        self.spin_inicio.setRange(0, 999999)
        self.spin_fim = QDoubleSpinBox()
        self.spin_fim.setRange(0, 999999)
        h_limites = QHBoxLayout()
        h_limites.addWidget(QLabel("Início:"))
        h_limites.addWidget(self.spin_inicio)
        h_limites.addWidget(QLabel("Fim:"))
        h_limites.addWidget(self.spin_fim)
        h_limites.addStretch()
        layout_form_recorte.addRow("", h_limites)  # Removido label "Limites:"

        self.chk_zerar = QCheckBox("Deslocar tempo para iniciar em 0")
        layout_form_recorte.addRow("", self.chk_zerar)

        self.form_recorte.setEnabled(False)
        self.chk_habilitar_recorte.toggled.connect(self.form_recorte.setEnabled)
        self.secao_recorte.addWidget(self.form_recorte)

        self.scroll_layout.addWidget(self.secao_recorte)

        # Seções de Operações
        self.secao_angulos = SecaoExpansivel("Definir Ângulos", FormAngulos)
        self.secao_aritmetica = SecaoExpansivel("Operação Aritmética", FormAritmetica)
        self.secao_trig = SecaoExpansivel("Operação Trigonométrica", FormTrigonometria)
        self.secao_escalar = SecaoExpansivel(
            "Operações de Cálculo e Funções Escalares", FormCalculoEscalar
        )
        self.secao_graficos = SecaoExpansivel(
            "Gráficos Criados Automaticamente", FormGrafico
        )

        self.scroll_layout.addWidget(self.secao_angulos)
        self.scroll_layout.addWidget(self.secao_aritmetica)
        self.scroll_layout.addWidget(self.secao_trig)
        self.scroll_layout.addWidget(self.secao_escalar)
        self.scroll_layout.addWidget(self.secao_graficos)

        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        layout_principal.addWidget(self.scroll_area)

        # --- 3. Botões ---
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_salvar = QPushButton("Salvar Script")
        btn_salvar.clicked.connect(self.salvar_script)
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_salvar)
        layout_principal.addLayout(layout_botoes)

    def usar_modelo(self):
        nome_arq = self.combo_modelo.currentText()
        if (
            nome_arq == "Nenhum"
            or not nome_arq
            or nome_arq not in self.estado.guarda_arquivos
        ):
            return

        pipeline = self.estado.guarda_arquivos[nome_arq].get("pipeline", [])

        # Limpar ops atuais
        self.chk_habilitar_recorte.setChecked(False)
        self.secao_angulos.limpar()
        self.secao_aritmetica.limpar()
        self.secao_trig.limpar()
        self.secao_escalar.limpar()

        for step in pipeline:
            cat = step.get("categoria")
            acao = step.get("acao")

            if acao == "Recorte Temporal":
                self.secao_recorte.toggle_button.setChecked(True)
                self.chk_habilitar_recorte.setChecked(True)
                self.combo_base.setCurrentText(
                    "Frames" if step.get("modo") == "frames" else "Tempo (s)"
                )
                self.spin_inicio.setValue(step.get("inicio", 0))
                self.spin_fim.setValue(step.get("fim", 0))
                self.chk_zerar.setChecked(step.get("deslocar_0", False))

            elif cat == "Operações e Atributos":

                if acao == "Aritmética de Colunas":
                    self.secao_aritmetica.toggle_button.setChecked(True)
                    form = self.secao_aritmetica.adicionar_formulario()
                    form.input_nova_var.setText(step.get("variavel_gerada", ""))
                    detalhe = step.get("detalhe", "")
                    if detalhe:
                        partes = detalhe.split()
                        if len(partes) >= 3:
                            form.input_var_a.setText(partes[0])
                            form.combo_op.setCurrentText(partes[1])
                            try:
                                val = float(partes[2])
                                form.combo_tipo_b.setCurrentIndex(1)
                                form.spin_const_b.setValue(val)
                            except ValueError:
                                form.combo_tipo_b.setCurrentIndex(0)
                                form.input_var_b.setText(partes[2])

                elif acao == "Trigonometria":
                    self.secao_trig.toggle_button.setChecked(True)
                    form = self.secao_trig.adicionar_formulario()
                    form.input_nova_var.setText(step.get("variavel_gerada", ""))
                    detalhe = step.get("detalhe", "")
                    if "seno" in detalhe.lower():
                        form.combo_op.setCurrentText("sin")
                    elif "cos" in detalhe.lower():
                        form.combo_op.setCurrentText("cos")
                    elif "tan" in detalhe.lower():
                        form.combo_op.setCurrentText("tan")

                    if "'" in detalhe:
                        var = detalhe.split("'")[1]
                        form.input_var.setText(var)

                elif acao == "Cálculo Escalar":
                    self.secao_escalar.toggle_button.setChecked(True)
                    form = self.secao_escalar.adicionar_formulario()
                    form.input_nova_var.setText(step.get("variavel_gerada", ""))
                    detalhe = step.get("detalhe", "")

                    if "Integral" in detalhe:
                        form.combo_op.setCurrentText("integral")
                    elif "Primeira" in detalhe:
                        form.combo_op.setCurrentText("derivada 1a")
                    elif "Segunda" in detalhe:
                        form.combo_op.setCurrentText("derivada 2a")
                    elif "Módulo" in detalhe:
                        form.combo_op.setCurrentText("modulo")
                    elif "Inverso" in detalhe:
                        form.combo_op.setCurrentText("inverso")
                    elif "Raiz" in detalhe:
                        form.combo_op.setCurrentText("raiz quadrada")

                    if "'" in detalhe:
                        partes = detalhe.split("'")
                        if len(partes) >= 2:
                            form.input_var_principal.setText(partes[1])
                        if len(partes) >= 4:
                            form.input_var_tempo.setText(partes[3])

                elif acao == "Definição de Ângulo":
                    self.secao_angulos.toggle_button.setChecked(True)
                    form = self.secao_angulos.adicionar_formulario()
                    form.input_nova_var.setText(step.get("variavel_gerada", ""))

        if nome_arq in self.estado.guarda_graficos:
            self.secao_graficos.toggle_button.setChecked(True)
            for nome_grafico, config_grafico in self.estado.guarda_graficos[
                nome_arq
            ].items():
                form = self.secao_graficos.adicionar_formulario()
                form.input_nome.setText(nome_grafico)
                form.combo_tipo.setCurrentText(config_grafico.get("tipo", "Linha"))
                form.input_eixo_x.setText(config_grafico.get("eixo_x", "frame"))
                form.input_eixo_y.setText(config_grafico.get("eixo_y", ""))

        QMessageBox.information(
            self,
            "Modelo Carregado",
            f"O pipeline do arquivo '{nome_arq}' foi carregado nas seções expansíveis.",
        )

    def carregar_script_para_edicao(self, nome_script, script_dados):
        """Preenche a janela com os dados de um script existente para edição."""
        self.input_titulo.setText(nome_script)
        self.combo_salvamento.setCurrentIndex(
            1 if script_dados.get("salvar_como_novo") else 0
        )
        self.chk_plotar.setChecked(script_dados.get("plotar_auto", False))

        # Limpar ops atuais
        self.chk_habilitar_recorte.setChecked(False)
        self.secao_angulos.limpar()
        self.secao_aritmetica.limpar()
        self.secao_trig.limpar()
        self.secao_escalar.limpar()

        acoes = script_dados.get("acoes", {})

        if "recorte_temporal" in acoes:
            recorte = acoes["recorte_temporal"]
            self.secao_recorte.toggle_button.setChecked(True)
            self.chk_habilitar_recorte.setChecked(True)
            self.combo_base.setCurrentText(
                "Frames" if recorte.get("modo") == "frames" else "Tempo (s)"
            )
            self.spin_inicio.setValue(recorte.get("inicio", 0))
            self.spin_fim.setValue(recorte.get("fim", 0))
            self.chk_zerar.setChecked(recorte.get("deslocar_0", False))

        if "operacoes" in acoes:
            for op in acoes["operacoes"]:
                tipo = op.get("tipo")
                if tipo == "Aritmética Básica":
                    self.secao_aritmetica.toggle_button.setChecked(True)
                    form = self.secao_aritmetica.adicionar_formulario()
                    form.input_nova_var.setText(op.get("nome_nova", ""))
                    form.combo_op.setCurrentText(op.get("operador", "+"))
                    form.input_var_a.setText(op.get("var_a", ""))
                    if op.get("is_const_b"):
                        form.combo_tipo_b.setCurrentIndex(1)
                        form.spin_const_b.setValue(op.get("val_b", 0.0))
                    else:
                        form.combo_tipo_b.setCurrentIndex(0)
                        form.input_var_b.setText(op.get("var_b", ""))

                elif tipo == "Trigonometria":
                    self.secao_trig.toggle_button.setChecked(True)
                    form = self.secao_trig.adicionar_formulario()
                    form.input_nova_var.setText(op.get("nome_nova", ""))
                    form.combo_op.setCurrentText(op.get("operador", "sin"))
                    form.input_var.setText(op.get("var", ""))

                elif tipo == "Cálculo e Funções Escalares":
                    self.secao_escalar.toggle_button.setChecked(True)
                    form = self.secao_escalar.adicionar_formulario()
                    form.input_nova_var.setText(op.get("nome_nova", ""))
                    form.combo_op.setCurrentText(op.get("operador", "integral"))
                    form.input_var_principal.setText(op.get("var_principal", ""))
                    form.input_var_tempo.setText(op.get("var_tempo", ""))

                elif tipo == "Definir Ângulos":
                    self.secao_angulos.toggle_button.setChecked(True)
                    form = self.secao_angulos.adicionar_formulario()
                    form.input_nova_var.setText(op.get("nome_nova", ""))
                    form.combo_unidade.setCurrentText(op.get("unidade", "graus"))
                    form.combo_modo.setCurrentText(
                        "Ângulo entre Vetores (4 pontos)"
                        if op.get("modo") == "vetores"
                        else "Ângulo Relativo (3 pontos)"
                    )
                    form.input_p1.setText(op.get("p1", ""))
                    form.input_p2.setText(op.get("p2", ""))
                    form.input_p3.setText(op.get("p3", ""))
                    if op.get("modo") == "vetores":
                        form.input_p4.setText(op.get("p4", ""))

        if "graficos" in acoes:
            self.secao_graficos.toggle_button.setChecked(True)
            for op in acoes["graficos"]:
                form = self.secao_graficos.adicionar_formulario()
                form.input_nome.setText(op.get("nome_grafico", ""))
                form.combo_tipo.setCurrentText(op.get("tipo_grafico", "Linha"))
                form.input_eixo_x.setText(op.get("eixo_x", "frame"))
                form.input_eixo_y.setText(op.get("eixo_y", ""))

    def salvar_script(self):
        titulo = self.input_titulo.text().strip()
        if not titulo:
            i = 1
            while f"script_a{i}" in self.estado.guarda_scripts:
                i += 1
            titulo = f"script_a{i}"
            self.input_titulo.setText(titulo)

        if titulo in self.estado.guarda_scripts:
            res = QMessageBox.question(
                self,
                "Sobrescrever?",
                f"Já existe um script chamado '{titulo}'. Deseja sobrescrevê-lo?",
            )
            if res != QMessageBox.StandardButton.Yes:
                return

        script_dados = {
            "titulo": titulo,
            "salvar_como_novo": self.combo_salvamento.currentIndex() == 1,
            "plotar_auto": self.chk_plotar.isChecked(),
            "acoes": {},
        }

        if self.chk_habilitar_recorte.isChecked():
            script_dados["acoes"]["recorte_temporal"] = {
                "modo": (
                    "frames" if self.combo_base.currentText() == "Frames" else "tempo"
                ),
                "inicio": self.spin_inicio.value(),
                "fim": self.spin_fim.value(),
                "deslocar_0": self.chk_zerar.isChecked(),
            }

        ops = []

        # Validar e coletar de todas as seções
        secoes = [
            self.secao_angulos,
            self.secao_aritmetica,
            self.secao_trig,
            self.secao_escalar,
            self.secao_graficos,
        ]
        for secao in secoes:
            for form in secao.obter_dados():
                if not form.validar_dados():
                    secao.toggle_button.setChecked(True)
                    QMessageBox.warning(
                        self,
                        "Aviso",
                        f"O formulário '{secao.toggle_button.text()[2:]}' possui campos obrigatórios em branco.\nPreencha todas as variáveis necessárias ou clique em 'Excluir' na operação vazia.",
                    )
                    return
                if secao != self.secao_graficos:
                    ops.append(form.obter_dados())

        if ops:
            script_dados["acoes"]["operacoes"] = ops

        graficos_ops = [
            form.obter_dados()
            for form in self.secao_graficos.obter_dados()
            if form.validar_dados()
        ]
        if graficos_ops:
            contador_grafico = 1
            for g in graficos_ops:
                if not g.get("nome_grafico"):
                    g["nome_grafico"] = f"grafico{contador_grafico}"
                    contador_grafico += 1
            script_dados["acoes"]["graficos"] = graficos_ops

        if not self.chk_habilitar_recorte.isChecked() and not ops and not graficos_ops:
            QMessageBox.warning(
                self,
                "Aviso",
                "O script deve ter pelo menos uma ação configurada (recorte ou operações).",
            )
            return

        self.estado.guarda_scripts[titulo] = script_dados
        self.accept()


class JanelaScriptsSalvos(PadraoDialog):
    def __init__(self, estado, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.parent_window = parent
        self.setWindowTitle("Scripts Salvos")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)

        self.lista = QComboBox()
        self.lista.addItem("--- Arquivos ---")
        self.lista.model().item(0).setEnabled(False)

        # Por enquanto consideramos todos como arquivos
        for s in self.estado.guarda_scripts.keys():
            self.lista.addItem(s)

        self.lista.insertSeparator(self.lista.count())
        self.lista.addItem("--- Gráficos ---")
        self.lista.model().item(self.lista.count() - 1).setEnabled(False)
        self.lista.insertSeparator(self.lista.count())

        if hasattr(self.estado, "guarda_scripts_graficos"):
            for s in self.estado.guarda_scripts_graficos.keys():
                self.lista.addItem(s)

        self.lista.setCurrentIndex(-1)

        layout.addWidget(QLabel("Seus scripts:"))
        layout.addWidget(self.lista)

        btn_aplicar = QPushButton("Aplicar Script")
        btn_aplicar.clicked.connect(self.aplicar_script)
        layout.addWidget(btn_aplicar)

        btn_editar = QPushButton("Editar Script Selecionado")
        btn_editar.clicked.connect(self.editar_script)
        layout.addWidget(btn_editar)

        btn_excluir = QPushButton("Excluir Script Selecionado")
        btn_excluir.setStyleSheet("color: red;")
        btn_excluir.clicked.connect(self.excluir_script)
        layout.addWidget(btn_excluir)

        layout.addStretch()

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.reject)
        layout.addWidget(btn_fechar)

    def editar_script(self):
        nome = self.lista.currentText()
        if not nome or "---" in nome:
            QMessageBox.warning(
                self, "Aviso", "Selecione um script válido para editar."
            )
            return

        if nome in self.estado.guarda_scripts:
            # Fechar a lista e abrir o editor
            self.accept()
            janela = JanelaCriarScript(self.estado, self.parent_window)
            janela.carregar_script_para_edicao(nome, self.estado.guarda_scripts[nome])
            if janela.exec() == QDialog.DialogCode.Accepted:
                QMessageBox.information(
                    self.parent_window, "Sucesso", "Script editado e salvo com sucesso."
                )
        elif (
            hasattr(self.estado, "guarda_scripts_graficos")
            and nome in self.estado.guarda_scripts_graficos
        ):
            self.accept()
            janela = JanelaCriarScriptGrafico(
                self.estado, self.parent_window, edit_script_name=nome
            )
            if janela.exec() == QDialog.DialogCode.Accepted:
                QMessageBox.information(
                    self.parent_window,
                    "Sucesso",
                    "Script de gráfico editado e salvo com sucesso.",
                )

    def excluir_script(self):
        nome = self.lista.currentText()
        if not nome or "---" in nome:
            return

        if nome in self.estado.guarda_scripts:
            del self.estado.guarda_scripts[nome]
            self.lista.removeItem(self.lista.currentIndex())
            QMessageBox.information(self, "Sucesso", f"Script '{nome}' excluído.")
        elif (
            hasattr(self.estado, "guarda_scripts_graficos")
            and nome in self.estado.guarda_scripts_graficos
        ):
            del self.estado.guarda_scripts_graficos[nome]
            self.lista.removeItem(self.lista.currentIndex())
            QMessageBox.information(
                self, "Sucesso", f"Script de gráfico '{nome}' excluído."
            )

    def aplicar_script(self):
        nome = self.lista.currentText()
        if not nome or "---" in nome:
            QMessageBox.warning(
                self, "Aviso", "Selecione um script válido para aplicar."
            )
            return

        is_arquivo = nome in self.estado.guarda_scripts
        is_grafico = (
            hasattr(self.estado, "guarda_scripts_graficos")
            and nome in self.estado.guarda_scripts_graficos
        )

        if is_arquivo:
            opcoes = list(self.estado.guarda_arquivos.keys())
            if not opcoes:
                QMessageBox.warning(
                    self, "Aviso", "Nenhum arquivo disponível para aplicar o script."
                )
                return
            dialog = JanelaSelecaoAlvosScript(
                opcoes, f"Aplicar script '{nome}' nos arquivos:"
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selecionados = dialog.get_selecionados()
                from processamento.executador_scripts import executar_script

                sucessos = 0
                for arq in selecionados:
                    try:
                        executar_script(
                            self.estado, self.parent_window, nome, arq, silencioso=True
                        )
                        sucessos += 1
                    except Exception as e:
                        QMessageBox.critical(self, "Erro", f"{arq} : {str(e)}")
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"Script aplicado com sucesso em {sucessos} arquivo(s).",
                )

        elif is_grafico:
            opcoes = []
            for arq, grafs in self.estado.guarda_graficos.items():
                for graf, config in grafs.items():
                    if isinstance(config, dict) and config.get("tipo") != "Sobreposto":
                        opcoes.append(f"{arq} | {graf}")

            if not opcoes:
                QMessageBox.warning(
                    self, "Aviso", "Nenhum gráfico disponível para aplicar o script."
                )
                return
            dialog = JanelaSelecaoAlvosScript(
                opcoes, f"Aplicar script '{nome}' nos gráficos:"
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selecionados = dialog.get_selecionados()
                from processamento.executador_scripts_graficos import (
                    executar_script_grafico,
                )

                sucessos = 0
                for item in selecionados:
                    arq, graf = item.split(" | ")
                    try:
                        executar_script_grafico(
                            self.estado,
                            self.parent_window,
                            nome,
                            arq,
                            graf,
                            silencioso=True,
                        )
                        sucessos += 1
                    except Exception as e:
                        QMessageBox.critical(self, "Erro", f"{arq} | {graf} : {str(e)}")
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"Script aplicado com sucesso em {sucessos} gráfico(s).",
                )


class FormFiltroScript(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 10)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout = QVBoxLayout(self.frame)

        h_header = QHBoxLayout()
        lbl_titulo = QLabel("<b>Filtro</b>")
        btn_remover = QPushButton("Remover")
        btn_remover.clicked.connect(self.deleteLater)
        h_header.addWidget(lbl_titulo)
        h_header.addStretch()
        h_header.addWidget(btn_remover)
        self.frame_layout.addLayout(h_header)

        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.frame_layout.addLayout(self.form_layout)
        self.layout_principal.addWidget(self.frame)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Passa-Baixa", "Passa-Alta"])

        self.combo_fc = QComboBox()
        self.combo_fc.addItems(["Definir Manualmente", "Calcular Frequência Ótima"])

        self.spin_fc = QDoubleSpinBox()
        self.spin_fc.setRange(0.1, 1000.0)
        self.spin_fc.setValue(10.0)

        self.spin_ordem = QSpinBox()
        self.spin_ordem.setRange(1, 10)
        self.spin_ordem.setValue(4)

        self.chk_retificar = QCheckBox("Retificar sinal antes de filtrar")

        self.form_layout.addRow("Tipo de Filtro:", self.combo_tipo)
        self.form_layout.addRow("Frequência de Corte (Hz):", self.combo_fc)
        self.form_layout.addRow("Valor FC:", self.spin_fc)
        self.form_layout.addRow("Ordem:", self.spin_ordem)
        self.form_layout.addRow("", self.chk_retificar)

        self.combo_fc.currentIndexChanged.connect(self._toggle_fc)
        self.combo_tipo.currentIndexChanged.connect(self._toggle_retificar)

    def _toggle_fc(self):
        is_manual = self.combo_fc.currentIndex() == 0
        self.spin_fc.setVisible(is_manual)
        self.form_layout.labelForField(self.spin_fc).setVisible(is_manual)

    def _toggle_retificar(self):
        is_baixa = self.combo_tipo.currentText() == "Passa-Baixa"
        self.chk_retificar.setVisible(is_baixa)

        # Desabilitar FC ótima se for passa-alta
        if not is_baixa:
            self.combo_fc.setCurrentIndex(0)
            if self.combo_fc.count() > 1:
                self.combo_fc.model().item(1).setEnabled(False)
        else:
            if self.combo_fc.count() > 1:
                self.combo_fc.model().item(1).setEnabled(True)

    def validar_dados(self):
        return True

    def obter_dados(self):
        return {
            "tipo": (
                "passa_baixa"
                if self.combo_tipo.currentText() == "Passa-Baixa"
                else "passa_alta"
            ),
            "fc_manual": self.combo_fc.currentIndex() == 0,
            "fc": self.spin_fc.value(),
            "ordem": self.spin_ordem.value(),
            "retificar": (
                self.chk_retificar.isChecked()
                if self.combo_tipo.currentText() == "Passa-Baixa"
                else False
            ),
        }

    def carregar_dados(self, dados):
        tipo_idx = 0 if dados.get("tipo", "passa_baixa") == "passa_baixa" else 1
        self.combo_tipo.setCurrentIndex(tipo_idx)

        fc_idx = 0 if dados.get("fc_manual", True) else 1
        self.combo_fc.setCurrentIndex(fc_idx)

        self.spin_fc.setValue(dados.get("fc", 10.0))
        self.spin_ordem.setValue(dados.get("ordem", 4))
        self.chk_retificar.setChecked(dados.get("retificar", False))

        self._toggle_fc()
        self._toggle_retificar()


class FormInterpolacaoScript(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 10)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout = QVBoxLayout(self.frame)

        h_header = QHBoxLayout()
        lbl_titulo = QLabel("<b>Interpolação</b>")
        btn_remover = QPushButton("Remover")
        btn_remover.clicked.connect(self.deleteLater)
        h_header.addWidget(lbl_titulo)
        h_header.addStretch()
        h_header.addWidget(btn_remover)
        self.frame_layout.addLayout(h_header)

        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.frame_layout.addLayout(self.form_layout)
        self.layout_principal.addWidget(self.frame)

        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Linear", "Spline", "Média"])

        self.form_layout.addRow("Método:", self.combo_tipo)

    def validar_dados(self):
        return True

    def obter_dados(self):
        return {"metodo": self.combo_tipo.currentText().lower()}

    def carregar_dados(self, dados):
        metodo = dados.get("metodo", "linear").lower()
        idx = (
            ["linear", "spline", "média"].index(metodo)
            if metodo in ["linear", "spline", "média"]
            else 0
        )
        self.combo_tipo.setCurrentIndex(idx)


class FormOffsetScript(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 10)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout = QVBoxLayout(self.frame)

        h_header = QHBoxLayout()
        lbl_titulo = QLabel("<b>Offset</b>")
        btn_remover = QPushButton("Remover")
        btn_remover.clicked.connect(self.deleteLater)
        h_header.addWidget(lbl_titulo)
        h_header.addStretch()
        h_header.addWidget(btn_remover)
        self.frame_layout.addLayout(h_header)

        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.frame_layout.addLayout(self.form_layout)
        self.layout_principal.addWidget(self.frame)

        self.spin_valor = QDoubleSpinBox()
        self.spin_valor.setRange(-999999.0, 999999.0)
        self.spin_valor.setDecimals(4)
        self.spin_valor.setValue(0.0)

        self.combo_base = QComboBox()
        self.combo_base.addItems(["Tempo", "Frames"])

        self.chk_nova_var = QCheckBox(
            "Salvar como Nova Variável no DataFrame (ao invés de modificar apenas o gráfico)"
        )
        self.input_nova_var = QLineEdit()
        self.input_nova_var.setPlaceholderText("Nome da nova variável")
        self.input_nova_var.setVisible(False)
        self.chk_nova_var.toggled.connect(self.input_nova_var.setVisible)

        self.form_layout.addRow("Valor:", self.spin_valor)
        self.form_layout.addRow("Base:", self.combo_base)
        self.form_layout.addRow("", self.chk_nova_var)
        self.form_layout.addRow("Nome da nova var:", self.input_nova_var)
        self.form_layout.labelForField(self.input_nova_var).setVisible(False)
        self.chk_nova_var.toggled.connect(
            self.form_layout.labelForField(self.input_nova_var).setVisible
        )

    def validar_dados(self):
        if self.chk_nova_var.isChecked() and not self.input_nova_var.text().strip():
            QMessageBox.warning(
                self, "Aviso", "Preencha o nome da nova variável para o offset."
            )
            return False
        return True

    def obter_dados(self):
        return {
            "valor": self.spin_valor.value(),
            "base": self.combo_base.currentText().lower(),
            "nova_var": self.chk_nova_var.isChecked(),
            "nome_nova_var": self.input_nova_var.text().strip(),
        }

    def carregar_dados(self, dados):
        self.spin_valor.setValue(dados.get("valor", 0.0))
        base = dados.get("base", "tempo")
        self.combo_base.setCurrentIndex(0 if base == "tempo" else 1)
        self.chk_nova_var.setChecked(dados.get("nova_var", False))
        self.input_nova_var.setText(dados.get("nome_nova_var", ""))


class FormPolinomioScript(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 10)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout = QVBoxLayout(self.frame)

        h_header = QHBoxLayout()
        lbl_titulo = QLabel("<b>Polinômio de Referência</b>")
        btn_remover = QPushButton("Remover")
        btn_remover.clicked.connect(self.deleteLater)
        h_header.addWidget(lbl_titulo)
        h_header.addStretch()
        h_header.addWidget(btn_remover)
        self.frame_layout.addLayout(h_header)

        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.frame_layout.addLayout(self.form_layout)
        self.layout_principal.addWidget(self.frame)

        self.input_titulo = QLineEdit()
        self.input_titulo.setPlaceholderText("(Opcional)")

        self.spin_termos = QSpinBox()
        self.spin_termos.setRange(1, 10)
        self.spin_termos.setValue(2)

        self.form_layout.addRow("Título:", self.input_titulo)
        self.form_layout.addRow("Qtd Termos (Grau + 1):", self.spin_termos)

        self.widget_coefs = QWidget()
        self.layout_coefs = QVBoxLayout(self.widget_coefs)
        self.layout_coefs.setContentsMargins(0, 0, 0, 0)
        self.form_layout.addRow("Coeficientes:", self.widget_coefs)

        self.entradas_coef = []
        self.spin_termos.valueChanged.connect(self._atualizar_coefs)
        self._atualizar_coefs()

    def _atualizar_coefs(self):
        qtd = self.spin_termos.value()

        while self.layout_coefs.count():
            item = self.layout_coefs.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.entradas_coef.clear()

        for i in range(qtd):
            row = QHBoxLayout()
            lbl = QLabel(f"Coef {i} (x^{i}):")
            lbl.setMinimumWidth(80)
            spin = QDoubleSpinBox()
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(6)
            row.addWidget(lbl)
            row.addWidget(spin)

            w = QWidget()
            w.setLayout(row)
            self.layout_coefs.addWidget(w)
            self.entradas_coef.append(spin)

    def validar_dados(self):
        return True

    def obter_dados(self):
        coefs = [spin.value() for spin in self.entradas_coef]
        return {
            "titulo": self.input_titulo.text().strip(),
            "termos": self.spin_termos.value(),
            "coeficientes": coefs,
        }

    def carregar_dados(self, dados):
        self.input_titulo.setText(dados.get("titulo", ""))
        termos = dados.get("termos", 2)
        self.spin_termos.setValue(termos)
        self._atualizar_coefs()

        coefs = dados.get("coeficientes", [])
        for i, val in enumerate(coefs):
            if i < len(self.entradas_coef):
                self.entradas_coef[i].setValue(val)


class JanelaCriarScriptGrafico(PadraoDialog):
    def __init__(self, estado, parent=None, edit_script_name=None):
        super().__init__(parent)
        self.estado = estado
        self.edit_script_name = edit_script_name
        self.setWindowTitle(
            "Criar Script de Gráfico"
            if not edit_script_name
            else f"Editar Script de Gráfico: {edit_script_name}"
        )
        self.resize(600, 700)

        self.layout_principal = QVBoxLayout(self)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.widget_conteudo = QWidget()
        self.layout_conteudo = QVBoxLayout(self.widget_conteudo)

        # 1. Informações Gerais
        grp_info = QGroupBox("Informações Gerais")
        layout_info = QFormLayout(grp_info)
        layout_info.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        layout_info.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Opcional")
        layout_info.addRow("Nome do Script:", self.input_nome)

        self.combo_modelo = QComboBox()
        self.combo_modelo.addItem("Nenhum")
        self.graficos_existentes = []
        for arq, grafs in self.estado.guarda_graficos.items():
            for graf in grafs.keys():
                self.graficos_existentes.append((arq, graf))
                self.combo_modelo.addItem(f"{arq} -> {graf}")
        layout_info.addRow("Usar Gráfico Modelo:", self.combo_modelo)
        self.combo_modelo.currentIndexChanged.connect(self._carregar_modelo)

        self.layout_conteudo.addWidget(grp_info)

        # Secoes Expansíveis
        self.secao_filtros = SecaoExpansivel("Filtros", FormFiltroScript)
        self.layout_conteudo.addWidget(self.secao_filtros)

        self.secao_interpolacoes = SecaoExpansivel(
            "Interpolações", FormInterpolacaoScript
        )
        self.layout_conteudo.addWidget(self.secao_interpolacoes)

        self.secao_offsets = SecaoExpansivel("Offset", FormOffsetScript)
        self.layout_conteudo.addWidget(self.secao_offsets)

        self.secao_polinomios = SecaoExpansivel(
            "Adicionar Polinômio de Referência", FormPolinomioScript
        )
        self.layout_conteudo.addWidget(self.secao_polinomios)

        self.layout_conteudo.addStretch()
        self.scroll.setWidget(self.widget_conteudo)
        self.layout_principal.addWidget(self.scroll)

        # Botoes
        botoes = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_salvar = QPushButton("Salvar Script")
        btn_salvar.clicked.connect(self.salvar_script)
        botoes.addStretch()
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        self.layout_principal.addLayout(botoes)

        if self.edit_script_name:
            self._carregar_para_edicao()

    def _carregar_modelo(self):
        idx = self.combo_modelo.currentIndex()
        if idx == 0:
            return

        arq, graf = self.graficos_existentes[idx - 1]
        config = self.estado.guarda_graficos[arq][graf]

        self.secao_filtros.limpar()
        self.secao_interpolacoes.limpar()
        self.secao_offsets.limpar()
        self.secao_polinomios.limpar()

        # Tenta carregar pipeline armazenado no grafico
        pipeline = config.get("pipeline_grafico", [])

        # Se o gráfico foi criado manualmente, ele pode não ter pipeline_grafico. Buscamos pelo eixo y
        if not pipeline and "pipeline_colunas" in self.estado.guarda_arquivos.get(
            arq, {}
        ):
            eixo_y = config.get("eixo_y")
            if eixo_y:
                pipeline = self.estado.guarda_arquivos[arq]["pipeline_colunas"].get(
                    eixo_y, []
                )
                import copy

                pipeline = copy.deepcopy(pipeline)

        print(f"[DEBUG] Carregando modelo do gráfico '{graf}' (Arquivo: '{arq}')")
        print(f"[DEBUG] Config do gráfico: {config}")
        print(f"[DEBUG] Pipeline encontrado: {pipeline}")

        for op in pipeline:
            tipo = op.get("tipo_operacao")
            print(f"[DEBUG] Processando operacao do tipo: {tipo}")
            if tipo == "filtro":
                form = self.secao_filtros.adicionar_formulario()
                try:
                    form.carregar_dados(op)
                except Exception as e:
                    print(f"[DEBUG] Erro ao carregar Filtro: {e}")
                self.secao_filtros.toggle_button.setChecked(True)
            elif tipo == "interpolacao":
                form = self.secao_interpolacoes.adicionar_formulario()
                try:
                    form.carregar_dados(op)
                except Exception as e:
                    print(f"[DEBUG] Erro ao carregar Interpolação: {e}")
                self.secao_interpolacoes.toggle_button.setChecked(True)
            elif tipo == "offset":
                form = self.secao_offsets.adicionar_formulario()
                try:
                    form.carregar_dados(op)
                except Exception as e:
                    print(f"[DEBUG] Erro ao carregar Offset: {e}")
                self.secao_offsets.toggle_button.setChecked(True)

        for ref in config.get("linhas_referencia", []):
            form = self.secao_polinomios.adicionar_formulario()
            form.carregar_dados(
                {
                    "titulo": ref.get("titulo", ""),
                    "termos": len(ref.get("coeficientes", [])),
                    "coeficientes": ref.get("coeficientes", []),
                }
            )
            self.secao_polinomios.toggle_button.setChecked(True)

        QMessageBox.information(
            self, "Sucesso", "Dados do modelo importados com sucesso!"
        )

    def _carregar_para_edicao(self):
        script = self.estado.guarda_scripts_graficos[self.edit_script_name]
        self.input_nome.setText(self.edit_script_name)

        acoes = script.get("acoes", {})
        for f_data in acoes.get("filtros", []):
            form = self.secao_filtros.adicionar_formulario()
            form.carregar_dados(f_data)
            self.secao_filtros.toggle_button.setChecked(True)

        for i_data in acoes.get("interpolacoes", []):
            form = self.secao_interpolacoes.adicionar_formulario()
            form.carregar_dados(i_data)
            self.secao_interpolacoes.toggle_button.setChecked(True)

        for o_data in acoes.get("offsets", []):
            form = self.secao_offsets.adicionar_formulario()
            form.carregar_dados(o_data)
            self.secao_offsets.toggle_button.setChecked(True)

        for p_data in acoes.get("polinomios", []):
            form = self.secao_polinomios.adicionar_formulario()
            form.carregar_dados(p_data)
            self.secao_polinomios.toggle_button.setChecked(True)

    def salvar_script(self):
        nome_script = self.input_nome.text().strip()

        if not hasattr(self.estado, "guarda_scripts_graficos"):
            self.estado.guarda_scripts_graficos = {}

        if not nome_script:
            contador = 1
            while f"script_g{contador}" in self.estado.guarda_scripts_graficos:
                contador += 1
            nome_script = f"script_g{contador}"

        if not self.edit_script_name or self.edit_script_name != nome_script:
            if nome_script in self.estado.guarda_scripts_graficos:
                res = QMessageBox.warning(
                    self,
                    "Aviso",
                    f"O script '{nome_script}' já existe. Deseja sobrescrever?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if res == QMessageBox.StandardButton.No:
                    return

        # Validacoes
        for s in [
            self.secao_filtros,
            self.secao_interpolacoes,
            self.secao_offsets,
            self.secao_polinomios,
        ]:
            for w in s.obter_dados():
                if not w.validar_dados():
                    s.toggle_button.setChecked(True)
                    return

        script_dados = {
            "acoes": {
                "filtros": [w.obter_dados() for w in self.secao_filtros.obter_dados()],
                "interpolacoes": [
                    w.obter_dados() for w in self.secao_interpolacoes.obter_dados()
                ],
                "offsets": [w.obter_dados() for w in self.secao_offsets.obter_dados()],
                "polinomios": [
                    w.obter_dados() for w in self.secao_polinomios.obter_dados()
                ],
            }
        }

        if self.edit_script_name and self.edit_script_name != nome_script:
            del self.estado.guarda_scripts_graficos[self.edit_script_name]

        self.estado.guarda_scripts_graficos[nome_script] = script_dados
        QMessageBox.information(self, "Sucesso", "Script salvo com sucesso!")
        self.accept()


class JanelaSelecaoAlvosScript(PadraoDialog):
    def __init__(self, itens, texto_descricao, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aplicar Script")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(texto_descricao))

        self.btn_selecionar_todos = QPushButton("Selecionar todos")
        self.btn_selecionar_todos.clicked.connect(self._selecionar_todos)
        layout.addWidget(self.btn_selecionar_todos)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)

        self.checkboxes = {}
        for nome in itens:
            cb = QCheckBox(nome)
            cb.setChecked(False)  # Desmarcados por padrão
            self.checkboxes[nome] = cb
            container_layout.addWidget(cb)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_ok = QPushButton("Aplicar")
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addLayout(botoes)

    def _selecionar_todos(self):
        todos_marcados = all(cb.isChecked() for cb in self.checkboxes.values())
        novo_estado = not todos_marcados
        for cb in self.checkboxes.values():
            cb.setChecked(novo_estado)

        if novo_estado:
            self.btn_selecionar_todos.setText("Desmarcar todos")
        else:
            self.btn_selecionar_todos.setText("Selecionar todos")

    def get_selecionados(self):
        return [nome for nome, cb in self.checkboxes.items() if cb.isChecked()]
