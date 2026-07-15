from ui.utils import PadraoDialog

# Janelas de diálogo para operações sobre variáveis do arquivo.
# (Aritmética Básica, Trigonometria, Cálculo e Funções Escalares)

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QDoubleSpinBox,
    QMessageBox,
    QWidget,
    QCheckBox,
)

from processamento.operacoes import (
    operar_variaveis,
    operar_trigonometria,
    operar_calculo_escalar,
    agrupar_pontos_3d,
    operar_angulo_3d,
)


def _formatar_coluna(nome_coluna, unidades_colunas):
    """Formata nome da coluna com unidade entre colchetes para exibição nos dropdowns."""
    unidade = unidades_colunas.get(nome_coluna)
    if unidade:
        return f"{nome_coluna} [{unidade}]"
    return nome_coluna


def _popular_combo_colunas(combo, colunas, unidades_colunas):
    """Popula um QComboBox com colunas formatadas (display) e dados limpos (data)."""
    combo.clear()
    for col in colunas:
        label = _formatar_coluna(col, unidades_colunas)
        combo.addItem(label, col)


class JanelaManipularVariaveis(PadraoDialog):
    """Janela para criar novas variáveis a partir de operações entre colunas do arquivo."""

    def __init__(self, estado, arquivo_pre_selecionado=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self._resultado = None
        self._nome_arquivo_selecionado = None

        self.setWindowTitle("Manipular Variáveis")
        self.setMinimumWidth(500)
        self.setMinimumHeight(420)

        layout_principal = QVBoxLayout(self)

        # Seleção de Arquivo
        grupo_arquivo = QGroupBox("Arquivo")
        layout_arquivo = QHBoxLayout(grupo_arquivo)
        layout_arquivo.addWidget(QLabel("Arquivo:"))
        self.combo_arquivo = QComboBox()
        self.combo_arquivo.addItems(list(self.guarda_arquivos.keys()))
        if arquivo_pre_selecionado and arquivo_pre_selecionado in self.guarda_arquivos:
            self.combo_arquivo.setCurrentText(arquivo_pre_selecionado)
        layout_arquivo.addWidget(self.combo_arquivo)
        layout_principal.addWidget(grupo_arquivo)

        # Nome da nova variável
        grupo_nome = QGroupBox("Nome da Nova Variável")
        layout_nome = QHBoxLayout(grupo_nome)
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Velocidade_Resultante")
        layout_nome.addWidget(self.input_nome)
        layout_principal.addWidget(grupo_nome)

        # Operação
        grupo_operacao = QGroupBox("Definir Operação")
        layout_operacao = QVBoxLayout(grupo_operacao)

        # Linha 1: Variável A
        h_var_a = QHBoxLayout()
        h_var_a.addWidget(QLabel("Variável A:"))
        self.combo_var_a = QComboBox()
        h_var_a.addWidget(self.combo_var_a)
        layout_operacao.addLayout(h_var_a)

        # Linha 2: Operação
        h_op = QHBoxLayout()
        h_op.addWidget(QLabel("Operação:"))
        self.combo_operacao = QComboBox()
        self.combo_operacao.addItems(
            ["+  (Soma)", "−  (Subtração)", "×  (Multiplicação)", "÷  (Divisão)"]
        )
        h_op.addWidget(self.combo_operacao)
        layout_operacao.addLayout(h_op)

        # Linha 3: Tipo do segundo operando
        h_tipo_b = QHBoxLayout()
        h_tipo_b.addWidget(QLabel("Operando B:"))
        self.radio_variavel = QRadioButton("Variável do arquivo")
        self.radio_constante = QRadioButton("Constante")
        self.radio_variavel.setChecked(True)
        h_tipo_b.addWidget(self.radio_variavel)
        h_tipo_b.addWidget(self.radio_constante)
        layout_operacao.addLayout(h_tipo_b)

        # Linha 4: Seleção do segundo operando (variável ou constante)
        h_var_b = QHBoxLayout()
        h_var_b.addWidget(QLabel("Valor de B:"))

        self.combo_var_b = QComboBox()
        h_var_b.addWidget(self.combo_var_b)

        self.spin_constante = QDoubleSpinBox()
        self.spin_constante.setRange(-1e15, 1e15)
        self.spin_constante.setDecimals(6)
        self.spin_constante.setValue(1.0)
        self.spin_constante.hide()
        h_var_b.addWidget(self.spin_constante)

        layout_operacao.addLayout(h_var_b)

        # Checkbox para estender com zero
        self.checkbox_estender_zero = QCheckBox("Estender curva(s) com constante zero")
        self.checkbox_estender_zero.setChecked(True)
        layout_operacao.addWidget(self.checkbox_estender_zero)

        # Checkbox para plotar automaticamente
        self.checkbox_plotar_auto = QCheckBox(
            "Plotar automaticamente a variável criada"
        )
        self.checkbox_plotar_auto.setChecked(True)
        layout_operacao.addWidget(self.checkbox_plotar_auto)

        layout_principal.addWidget(grupo_operacao)

        # Conecta os radio buttons para alternar entre variável e constante
        self.radio_variavel.toggled.connect(self._alternar_tipo_operando)

        # Pré-visualização da fórmula
        self.label_preview = QLabel("")
        self.label_preview.setStyleSheet(
            "color: #555; font-style: italic; padding: 4px;"
        )
        layout_principal.addWidget(self.label_preview)

        # Conectar sinais para atualizar pré-visualização
        self.combo_var_a.currentTextChanged.connect(self._atualizar_preview)
        self.combo_operacao.currentIndexChanged.connect(self._atualizar_preview)
        self.combo_operacao.currentIndexChanged.connect(
            self._atualizar_visibilidade_checkbox
        )
        self.combo_var_b.currentTextChanged.connect(self._atualizar_preview)
        self.spin_constante.valueChanged.connect(self._atualizar_preview)
        self.radio_variavel.toggled.connect(self._atualizar_preview)
        self.radio_variavel.toggled.connect(self._atualizar_visibilidade_checkbox)
        self.input_nome.textChanged.connect(self._atualizar_preview)

        # Conecta mudança de arquivo para atualizar colunas
        self.combo_arquivo.currentTextChanged.connect(self._atualizar_colunas)

        # Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_criar = QPushButton("Criar Variável")
        btn_criar.clicked.connect(self._validar_e_criar)
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_criar)
        layout_principal.addLayout(layout_botoes)

        # Inicializa colunas e visibilidade
        self._atualizar_colunas()
        self._atualizar_preview()
        self._atualizar_visibilidade_checkbox()

    def _get_df_ativo(self):
        """Retorna o DataFrame do arquivo selecionado no combo."""
        nome = self.combo_arquivo.currentText()
        if nome and nome in self.guarda_arquivos:
            self._nome_arquivo_selecionado = nome
            return self.guarda_arquivos[nome]["dataframe"]
        return None

    def _atualizar_colunas(self):
        """Atualiza os combos de colunas quando o arquivo muda."""
        df = self._get_df_ativo()
        if df is None:
            return
        nome = self.combo_arquivo.currentText()
        unidades = (
            self.guarda_arquivos[nome].get("unidades_colunas", {})
            if nome in self.guarda_arquivos
            else {}
        )
        colunas = list(df.columns)
        self.combo_var_a.blockSignals(True)
        self.combo_var_b.blockSignals(True)
        _popular_combo_colunas(self.combo_var_a, colunas, unidades)
        _popular_combo_colunas(self.combo_var_b, colunas, unidades)
        self.combo_var_a.blockSignals(False)
        self.combo_var_b.blockSignals(False)
        self._atualizar_preview()

    def _alternar_tipo_operando(self, variavel_selecionada):
        """Alterna visibilidade entre combo de variável e spin de constante."""
        if variavel_selecionada:
            self.combo_var_b.show()
            self.spin_constante.hide()
        else:
            self.combo_var_b.hide()
            self.spin_constante.show()

    def _atualizar_visibilidade_checkbox(self):
        """Mostra o checkbox apenas para soma, subtração ou multiplicação entre variáveis."""
        idx_op = self.combo_operacao.currentIndex()
        # idx_op: 0=Soma, 1=Subtração, 2=Multiplicação, 3=Divisão
        if self.radio_variavel.isChecked() and idx_op in [0, 1, 2]:
            self.checkbox_estender_zero.setVisible(True)
        else:
            self.checkbox_estender_zero.setVisible(False)

    def _atualizar_preview(self):
        """Atualiza o label com a pré-visualização da fórmula."""
        nome = self.input_nome.text().strip() or "?"
        var_a = self.combo_var_a.currentData() or ""
        ops = ["+", "−", "×", "÷"]
        op = ops[self.combo_operacao.currentIndex()]
        if self.radio_variavel.isChecked():
            var_b = self.combo_var_b.currentData() or ""
        else:
            var_b = str(self.spin_constante.value())
        self.label_preview.setText(f"Fórmula:  {nome} = {var_a} {op} {var_b}")

    def _validar_e_criar(self):
        """Valida os inputs e calcula a nova variável."""

        df = self._get_df_ativo()
        if df is None:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo disponível.")
            return

        nome = self.input_nome.text().strip()

        # Validação do nome
        if not nome:
            QMessageBox.warning(
                self, "Nome Inválido", "Informe um nome para a nova variável."
            )
            return

        if nome in df.columns:
            QMessageBox.warning(
                self,
                "Nome Duplicado",
                f"A variável '{nome}' já existe neste arquivo.\n" "Escolha outro nome.",
            )
            return

        # Obter operandos
        var_a = self.combo_var_a.currentData()
        valores_a = df[var_a].copy()

        idx_op = self.combo_operacao.currentIndex()

        if self.radio_variavel.isChecked():
            var_b = self.combo_var_b.currentData()
            valores_b = df[var_b].copy()

            # Lógica para estender curva(s) com constante zero
            if idx_op in [0, 1, 2] and self.checkbox_estender_zero.isChecked():
                import numpy as np

                valid_a = valores_a.notna()
                valid_b = valores_b.notna()

                if valid_a.any() and valid_b.any():
                    idx_a = np.where(valid_a)[0]
                    idx_b = np.where(valid_b)[0]

                    if len(idx_a) > 0 and len(idx_b) > 0:
                        min_pos = min(idx_a[0], idx_b[0])
                        max_pos = max(idx_a[-1], idx_b[-1])

                        valores_a.iloc[min_pos : max_pos + 1] = valores_a.iloc[
                            min_pos : max_pos + 1
                        ].fillna(0)
                        valores_b.iloc[min_pos : max_pos + 1] = valores_b.iloc[
                            min_pos : max_pos + 1
                        ].fillna(0)

        else:
            valores_b = self.spin_constante.value()

        # Verificação de zeros na divisão (aviso ao usuário antes de calcular)
        if idx_op == 3 and not isinstance(valores_b, (int, float)):
            if (valores_b == 0).any():
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "A variável selecionada contém valores zero.\n"
                    "Os resultados da divisão por zero serão NaN (indefinidos).",
                )

        # Delegar cálculo para operacoes.py
        try:
            resultado, erro = operar_variaveis(valores_a, valores_b, idx_op)

            if erro:
                QMessageBox.warning(self, "Erro", erro)
                return

            b_texto = (
                var_b
                if self.radio_variavel.isChecked()
                else str(self.spin_constante.value())
            )
            op_texto = self.combo_operacao.currentText()

            # Determina a unidade do resultado conforme a operação
            nome_arq = self._nome_arquivo_selecionado
            unidades = (
                self.guarda_arquivos[nome_arq].get("unidades_colunas", {})
                if nome_arq in self.guarda_arquivos
                else {}
            )
            unidade_a = unidades.get(var_a, "")

            operadores_simbolo = ["+", "−", "×", "÷"]
            op_simbolo = operadores_simbolo[idx_op]

            if self.radio_variavel.isChecked():
                # Operação entre duas variáveis
                unidade_b = unidades.get(var_b, "")
                if idx_op in (0, 1):  # Soma / Subtração
                    if unidade_a == unidade_b:
                        unidade_resultado = unidade_a  # Unidades iguais: mantém
                    elif unidade_a and unidade_b:
                        sep = "+" if idx_op == 0 else "-"
                        unidade_resultado = f"{unidade_a}{sep}{unidade_b}"
                    else:
                        unidade_resultado = unidade_a or unidade_b
                elif idx_op == 2:  # Multiplicação
                    if unidade_a and unidade_b:
                        unidade_resultado = f"{unidade_a}*{unidade_b}"
                    else:
                        unidade_resultado = unidade_a or unidade_b
                elif idx_op == 3:  # Divisão
                    if unidade_a and unidade_b:
                        unidade_resultado = f"{unidade_a}/{unidade_b}"
                    else:
                        unidade_resultado = unidade_a or unidade_b
                else:
                    unidade_resultado = unidade_a
            else:
                # Operação com constante: preserva a unidade de A
                unidade_resultado = unidade_a

            self._resultado = {
                "nome": nome,
                "valores": resultado,
                "unidade": unidade_resultado,
                "nome_arquivo": self._nome_arquivo_selecionado,
                "plotar_auto": self.checkbox_plotar_auto.isChecked(),
                "pipeline_step": {
                    "categoria": "Operações e Atributos",
                    "acao": "Aritmética de Colunas",
                    "variavel_gerada": nome,
                    "detalhe": f"{var_a} {op_texto.split()[0]} {b_texto}",
                },
            }
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self, "Erro de Cálculo", f"Falha ao calcular a nova variável:\n{e}"
            )

    def get_resultado(self):
        """Retorna o resultado da operação ou None."""
        return self._resultado


class JanelaTrigonometria(PadraoDialog):
    """Janela para criar variáveis a partir de operações trigonométricas."""

    # Unidades reconhecidas como angulares
    UNIDADES_ANGULARES = {"deg", "rad", "graus", "radianos", "°"}

    OPERACOES = [
        ("Seno (sin)", "seno"),
        ("Cosseno (cos)", "cosseno"),
        ("Tangente (tan)", "tangente"),
    ]

    # Prefixos curtos para sugestão automática de nome
    PREFIXOS = {
        "seno": "sin",
        "cosseno": "cos",
        "tangente": "tan",
    }

    def __init__(self, estado, arquivo_pre_selecionado=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self._resultado = None
        self._nome_arquivo_selecionado = None
        self._nome_editado_pelo_usuario = (
            False  # Flag para não sobrescrever edição manual
        )

        self.setWindowTitle("Trigonometria")
        self.setMinimumWidth(480)
        self.setMinimumHeight(360)

        layout_principal = QVBoxLayout(self)

        # Seleção de Arquivo
        grupo_arquivo = QGroupBox("Arquivo")
        layout_arquivo = QHBoxLayout(grupo_arquivo)
        layout_arquivo.addWidget(QLabel("Arquivo:"))
        self.combo_arquivo = QComboBox()
        self.combo_arquivo.addItems(list(self.guarda_arquivos.keys()))
        if arquivo_pre_selecionado and arquivo_pre_selecionado in self.guarda_arquivos:
            self.combo_arquivo.setCurrentText(arquivo_pre_selecionado)
        layout_arquivo.addWidget(self.combo_arquivo)
        layout_principal.addWidget(grupo_arquivo)

        #  Aviso dinâmico (só aparece se não houver variáveis angulares)
        self.label_aviso = QLabel(
            "⚠️  Nenhuma variável angular encontrada no arquivo.\n"
            "É possível criar ângulos em: Operações → Definir Ângulos."
        )
        self.label_aviso.setStyleSheet(
            "background-color: #FFF3CD; color: #856404; "
            "border: 1px solid #FFEEBA; border-radius: 4px; "
            "padding: 8px; font-size: 12px;"
        )
        self.label_aviso.setWordWrap(True)
        self.label_aviso.hide()
        layout_principal.addWidget(self.label_aviso)

        # Nome da nova variável
        grupo_nome = QGroupBox("Nome da Nova Variável")
        layout_nome = QHBoxLayout(grupo_nome)
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Sen_Angulo_Joelho")
        layout_nome.addWidget(self.input_nome)
        layout_principal.addWidget(grupo_nome)

        # Operação
        grupo_op = QGroupBox("Definir Operação")
        layout_op = QVBoxLayout(grupo_op)

        h_var = QHBoxLayout()
        h_var.addWidget(QLabel("Variável:"))
        self.combo_variavel = QComboBox()
        h_var.addWidget(self.combo_variavel)
        layout_op.addLayout(h_var)

        h_func = QHBoxLayout()
        h_func.addWidget(QLabel("Função:"))
        self.combo_funcao = QComboBox()
        self.combo_funcao.addItems([op[0] for op in self.OPERACOES])
        h_func.addWidget(self.combo_funcao)
        layout_op.addLayout(h_func)

        layout_principal.addWidget(grupo_op)

        # Pré-visualização
        self.label_preview = QLabel("")
        self.label_preview.setStyleSheet(
            "color: #555; font-style: italic; padding: 4px;"
        )
        layout_principal.addWidget(self.label_preview)

        self.combo_variavel.currentIndexChanged.connect(self._atualizar_nome_sugerido)
        self.combo_variavel.currentTextChanged.connect(self._atualizar_preview)
        self.combo_funcao.currentIndexChanged.connect(self._atualizar_nome_sugerido)
        self.combo_funcao.currentIndexChanged.connect(self._atualizar_preview)
        self.input_nome.textChanged.connect(self._atualizar_preview)
        self.input_nome.textEdited.connect(self._usuario_editou_nome)

        # Conecta mudança de arquivo
        self.combo_arquivo.currentTextChanged.connect(self._atualizar_colunas)

        # Checkbox para plotar automaticamente
        self.checkbox_plotar_auto = QCheckBox(
            "Plotar automaticamente a variável criada"
        )
        self.checkbox_plotar_auto.setChecked(True)
        layout_principal.addWidget(self.checkbox_plotar_auto)

        # Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_criar = QPushButton("Criar Variável")
        self.btn_criar.clicked.connect(self._validar_e_criar)
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(self.btn_criar)
        layout_principal.addLayout(layout_botoes)

        # Inicializa
        self._atualizar_colunas()
        self._atualizar_preview()

    def _get_df_ativo(self):
        nome = self.combo_arquivo.currentText()
        if nome and nome in self.guarda_arquivos:
            self._nome_arquivo_selecionado = nome
            return self.guarda_arquivos[nome]["dataframe"]
        return None

    def _get_unidades(self):
        """Retorna o mapeamento de unidades do arquivo selecionado."""
        nome = self.combo_arquivo.currentText()
        if nome and nome in self.guarda_arquivos:
            return self.guarda_arquivos[nome].get("unidades_colunas", {})
        return {}

    def _atualizar_colunas(self):
        """Filtra e exibe somente variáveis angulares (deg/rad) e tempo no dropdown."""
        df = self._get_df_ativo()
        if df is None:
            return
        unidades = self._get_unidades()

        # Filtra colunas que possuem unidade angular, ou que sejam tempo
        colunas_angulares = [
            col
            for col in df.columns
            if unidades.get(col, "").lower().strip() in self.UNIDADES_ANGULARES
            or str(col).lower() in ["time", "tempo"]
        ]

        self.combo_variavel.blockSignals(True)
        self.combo_variavel.clear()
        for col in colunas_angulares:
            label = _formatar_coluna(col, unidades)
            self.combo_variavel.addItem(label, col)

        # Tenta selecionar tempo/time por padrao
        for i in range(self.combo_variavel.count()):
            col_name = self.combo_variavel.itemData(i)
            if col_name and str(col_name).lower() in ["time", "tempo"]:
                self.combo_variavel.setCurrentIndex(i)
                break

        self.combo_variavel.blockSignals(False)

        # Mostra aviso e desabilita botão se nenhuma variável angular encontrada
        if not colunas_angulares:
            self.label_aviso.show()
            self.btn_criar.setEnabled(False)
        else:
            self.label_aviso.hide()
            self.btn_criar.setEnabled(True)

        self._atualizar_nome_sugerido()
        self._atualizar_preview()

    def _atualizar_nome_sugerido(self):
        """Gera nome automático no formato func(variavel) se o usuário não editou manualmente."""
        if self._nome_editado_pelo_usuario:
            return
        var = self.combo_variavel.currentData() or ""
        operacao = self.OPERACOES[self.combo_funcao.currentIndex()][1]
        prefixo = self.PREFIXOS.get(operacao, operacao)
        nome_sugerido = f"{prefixo}({var})" if var else ""
        self.input_nome.blockSignals(True)
        self.input_nome.setText(nome_sugerido)
        self.input_nome.blockSignals(False)
        self._atualizar_preview()

    def _usuario_editou_nome(self):
        """Marca que o usuário editou o nome manualmente (não sobrescrever mais)."""
        self._nome_editado_pelo_usuario = True

    def _atualizar_preview(self):
        nome = self.input_nome.text().strip() or "?"
        var = self.combo_variavel.currentData() or ""
        func_label = (
            self.OPERACOES[self.combo_funcao.currentIndex()][0].split(" ")[0].lower()
        )
        self.label_preview.setText(f"Fórmula:  {nome} = {func_label}({var})")

    def _validar_e_criar(self):
        df = self._get_df_ativo()
        if df is None:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo disponível.")
            return

        nome = self.input_nome.text().strip()

        if not nome:
            QMessageBox.warning(
                self, "Nome Inválido", "Informe um nome para a nova variável."
            )
            return

        if nome in df.columns:
            QMessageBox.warning(
                self,
                "Nome Duplicado",
                f"A variável '{nome}' já existe neste arquivo.\nEscolha outro nome.",
            )
            return

        var = self.combo_variavel.currentData()
        if not var:
            QMessageBox.warning(self, "Aviso", "Selecione uma variável angular.")
            return

        valores = df[var].copy()
        operacao = self.OPERACOES[self.combo_funcao.currentIndex()][1]

        # Detecta a unidade da variável selecionada para conversão automática
        unidades = self._get_unidades()
        unidade_var = unidades.get(var, "rad")

        try:
            resultado, erro = operar_trigonometria(
                valores, operacao, unidade=unidade_var
            )
            if erro:
                QMessageBox.warning(self, "Erro", erro)
                return

            func_label = self.OPERACOES[self.combo_funcao.currentIndex()][0]
            self._resultado = {
                "nome": nome,
                "valores": resultado,
                "unidade": "",  # Resultado adimensional
                "nome_arquivo": self._nome_arquivo_selecionado,
                "plotar_auto": self.checkbox_plotar_auto.isChecked(),
                "pipeline_step": {
                    "categoria": "Operações e Atributos",
                    "acao": "Trigonometria",
                    "variavel_gerada": nome,
                    "detalhe": f"{func_label} de '{var}'",
                },
            }
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Cálculo", f"Falha ao calcular:\n{e}")

    def get_resultado(self):
        return self._resultado


class JanelaCalculoEscalar(PadraoDialog):
    """Janela para criar variáveis a partir de operações de cálculo e funções escalares."""

    OPERACOES = [
        ("Integral", "integral"),
        ("Derivada Primeira", "derivada_1"),
        ("Derivada Segunda", "derivada_2"),
        ("Módulo (|x|)", "modulo"),
        ("Inverso (1/x)", "inverso"),
        ("Raiz Quadrada (√x)", "raiz_quadrada"),
    ]

    def __init__(self, estado, arquivo_pre_selecionado=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self._resultado = None
        self._nome_arquivo_selecionado = None

        self.setWindowTitle("Cálculo e Funções Escalares")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout_principal = QVBoxLayout(self)

        # Seleção de Arquivo
        grupo_arquivo = QGroupBox("Arquivo")
        layout_arquivo = QHBoxLayout(grupo_arquivo)
        layout_arquivo.addWidget(QLabel("Arquivo:"))
        self.combo_arquivo = QComboBox()
        self.combo_arquivo.addItems(list(self.guarda_arquivos.keys()))
        if arquivo_pre_selecionado and arquivo_pre_selecionado in self.guarda_arquivos:
            self.combo_arquivo.setCurrentText(arquivo_pre_selecionado)
        layout_arquivo.addWidget(self.combo_arquivo)
        layout_principal.addWidget(grupo_arquivo)

        # Nome da nova variável
        grupo_nome = QGroupBox("Nome da Nova Variável")
        layout_nome = QHBoxLayout(grupo_nome)
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Derivada_Forca")
        layout_nome.addWidget(self.input_nome)
        layout_principal.addWidget(grupo_nome)

        # Operação
        grupo_op = QGroupBox("Definir Operação")
        layout_op = QVBoxLayout(grupo_op)

        # Variável alvo
        h_var = QHBoxLayout()
        h_var.addWidget(QLabel("Variável:"))
        self.combo_variavel = QComboBox()
        h_var.addWidget(self.combo_variavel)
        layout_op.addLayout(h_var)

        # Variável X (para integral e derivadas)
        h_var_x = QHBoxLayout()
        h_var_x.addWidget(QLabel("Variável X (referência):"))
        self.combo_variavel_x = QComboBox()
        h_var_x.addWidget(self.combo_variavel_x)
        layout_op.addLayout(h_var_x)

        # Nota sobre variável X
        self.label_nota_x = QLabel(
            "Usada como referência de tempo para Integral e Derivadas."
        )
        self.label_nota_x.setStyleSheet(
            "color: #888; font-size: 11px; padding-left: 4px;"
        )
        layout_op.addWidget(self.label_nota_x)

        # Função
        h_func = QHBoxLayout()
        h_func.addWidget(QLabel("Operação:"))
        self.combo_operacao = QComboBox()
        self.combo_operacao.addItems([op[0] for op in self.OPERACOES])
        h_func.addWidget(self.combo_operacao)
        layout_op.addLayout(h_func)

        layout_principal.addWidget(grupo_op)

        # Conectar para mostrar/ocultar variável X conforme operação
        self.combo_operacao.currentIndexChanged.connect(self._atualizar_visibilidade_x)
        self._atualizar_visibilidade_x()

        # Pré-visualização
        self.label_preview = QLabel("")
        self.label_preview.setStyleSheet(
            "color: #555; font-style: italic; padding: 4px;"
        )
        layout_principal.addWidget(self.label_preview)

        self.combo_variavel.currentTextChanged.connect(self._atualizar_preview)
        self.combo_variavel_x.currentTextChanged.connect(self._atualizar_preview)
        self.combo_operacao.currentIndexChanged.connect(self._atualizar_preview)
        self.input_nome.textChanged.connect(self._atualizar_preview)

        # Conecta mudança de arquivo
        self.combo_arquivo.currentTextChanged.connect(self._atualizar_colunas)

        # Checkbox para plotar automaticamente
        self.checkbox_plotar_auto = QCheckBox(
            "Plotar automaticamente a variável criada"
        )
        self.checkbox_plotar_auto.setChecked(True)
        layout_principal.addWidget(self.checkbox_plotar_auto)

        # Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_criar = QPushButton("Criar Variável")
        btn_criar.clicked.connect(self._validar_e_criar)
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(btn_criar)
        layout_principal.addLayout(layout_botoes)

        # Inicializa
        self._atualizar_colunas()
        self._atualizar_preview()

    def _get_df_ativo(self):
        nome = self.combo_arquivo.currentText()
        if nome and nome in self.guarda_arquivos:
            self._nome_arquivo_selecionado = nome
            return self.guarda_arquivos[nome]["dataframe"]
        return None

    def _atualizar_colunas(self):
        df = self._get_df_ativo()
        if df is None:
            return
        nome = self.combo_arquivo.currentText()
        unidades = (
            self.guarda_arquivos[nome].get("unidades_colunas", {})
            if nome in self.guarda_arquivos
            else {}
        )
        colunas = list(df.columns)
        self.combo_variavel.blockSignals(True)
        self.combo_variavel_x.blockSignals(True)
        _popular_combo_colunas(self.combo_variavel, colunas, unidades)
        _popular_combo_colunas(self.combo_variavel_x, colunas, unidades)

        # Tenta definir a coluna de tempo como padrão no eixo X
        achou_X = False
        for i in range(self.combo_variavel_x.count()):
            col_name = self.combo_variavel_x.itemData(i)
            if col_name and str(col_name).lower() in ["time", "tempo"]:
                self.combo_variavel_x.setCurrentIndex(i)
                achou_X = True
                break

        if not achou_X:
            for i in range(self.combo_variavel_x.count()):
                col_name = self.combo_variavel_x.itemData(i)
                if col_name and str(col_name).lower() in [
                    "frame",
                    "frames",
                    "t",
                    "item",
                ]:
                    self.combo_variavel_x.setCurrentIndex(i)
                    break

        self.combo_variavel.blockSignals(False)
        self.combo_variavel_x.blockSignals(False)
        self._atualizar_preview()

    def _atualizar_visibilidade_x(self):
        """Mostra a seleção de variável X apenas para integral e derivadas."""
        idx = self.combo_operacao.currentIndex()
        operacao = self.OPERACOES[idx][1]
        precisa_x = operacao in ("integral", "derivada_1", "derivada_2")
        self.combo_variavel_x.setVisible(precisa_x)
        self.label_nota_x.setVisible(precisa_x)

    def _atualizar_preview(self):
        nome = self.input_nome.text().strip() or "?"
        var = self.combo_variavel.currentData() or ""
        idx = self.combo_operacao.currentIndex()
        op_label = self.OPERACOES[idx][0]
        operacao = self.OPERACOES[idx][1]

        if operacao in ("integral", "derivada_1", "derivada_2"):
            var_x = self.combo_variavel_x.currentData() or ""
            self.label_preview.setText(
                f"Fórmula:  {nome} = {op_label}({var}) em relação a {var_x}"
            )
        else:
            self.label_preview.setText(f"Fórmula:  {nome} = {op_label}({var})")

    def _validar_e_criar(self):
        df = self._get_df_ativo()
        if df is None:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo disponível.")
            return

        nome = self.input_nome.text().strip()

        if not nome:
            QMessageBox.warning(
                self, "Nome Inválido", "Informe um nome para a nova variável."
            )
            return

        if nome in df.columns:
            QMessageBox.warning(
                self,
                "Nome Duplicado",
                f"A variável '{nome}' já existe neste arquivo.\nEscolha outro nome.",
            )
            return

        var = self.combo_variavel.currentData()
        idx = self.combo_operacao.currentIndex()
        operacao = self.OPERACOES[idx][1]

        dados_y = df[var].copy()
        dados_x = df[self.combo_variavel_x.currentData()].copy()

        # Avisos específicos
        if operacao == "inverso":
            if (dados_y == 0).any():
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "A variável contém valores zero.\n"
                    "Os resultados da divisão por zero serão NaN.",
                )
        elif operacao == "raiz_quadrada":
            if (dados_y < 0).any():
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "A variável contém valores negativos.\n"
                    "A raiz de valores negativos será NaN.",
                )

        try:
            resultado, erro = operar_calculo_escalar(dados_x, dados_y, operacao)
            if erro:
                QMessageBox.warning(self, "Erro", erro)
                return

            op_label = self.OPERACOES[self.combo_operacao.currentIndex()][0]
            if operacao in ("integral", "derivada_1", "derivada_2"):
                var_x = self.combo_variavel_x.currentData()
                detalhe = f"{op_label} de '{var}' (ref: '{var_x}')"
            else:
                detalhe = f"{op_label} de '{var}'"

            # Determina unidade do resultado com base na operação
            nome_arq = self._nome_arquivo_selecionado
            unidades = (
                self.guarda_arquivos[nome_arq].get("unidades_colunas", {})
                if nome_arq in self.guarda_arquivos
                else {}
            )
            unidade_y = unidades.get(var, "")
            unidade_x = (
                unidades.get(self.combo_variavel_x.currentData(), "")
                if operacao in ("integral", "derivada_1", "derivada_2")
                else ""
            )

            if operacao == "integral" and unidade_y and unidade_x:
                unidade_resultado = f"{unidade_y}*{unidade_x}"
            elif operacao == "derivada_1" and unidade_y and unidade_x:
                unidade_resultado = f"{unidade_y}/{unidade_x}"
            elif operacao == "derivada_2" and unidade_y and unidade_x:
                unidade_resultado = f"{unidade_y}/{unidade_x}²"
            elif operacao == "modulo":
                unidade_resultado = unidade_y  # Preserva unidade
            elif operacao == "inverso" and unidade_y:
                unidade_resultado = f"1/{unidade_y}"
            elif operacao == "raiz_quadrada" and unidade_y:
                unidade_resultado = f"√({unidade_y})"
            else:
                unidade_resultado = unidade_y

            self._resultado = {
                "nome": nome,
                "valores": resultado,
                "unidade": unidade_resultado,
                "nome_arquivo": self._nome_arquivo_selecionado,
                "plotar_auto": self.checkbox_plotar_auto.isChecked(),
                "pipeline_step": {
                    "categoria": "Operações e Atributos",
                    "acao": "Cálculo Escalar",
                    "variavel_gerada": nome,
                    "detalhe": detalhe,
                },
            }
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Cálculo", f"Falha ao calcular:\n{e}")

    def get_resultado(self):
        return self._resultado


class JanelaDefinirAngulos(PadraoDialog):
    """Janela para criar ângulos a partir de pontos 3D no dataframe."""

    def __init__(self, estado, arquivo_pre_selecionado=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self._resultado = None
        self._nome_arquivo_selecionado = None

        self.setWindowTitle("Definir Ângulos")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)

        layout_principal = QVBoxLayout(self)

        # Seleção de Arquivo
        grupo_arquivo = QGroupBox("Arquivo")
        layout_arquivo = QHBoxLayout(grupo_arquivo)
        layout_arquivo.addWidget(QLabel("Arquivo:"))
        self.combo_arquivo = QComboBox()
        self.combo_arquivo.addItems(list(self.guarda_arquivos.keys()))
        if arquivo_pre_selecionado and arquivo_pre_selecionado in self.guarda_arquivos:
            self.combo_arquivo.setCurrentText(arquivo_pre_selecionado)
        layout_arquivo.addWidget(self.combo_arquivo)
        layout_principal.addWidget(grupo_arquivo)

        # Nome da Variável e Unidade
        grupo_saida = QGroupBox("Configuração de Saída")
        layout_saida = QVBoxLayout(grupo_saida)

        h_nome = QHBoxLayout()
        h_nome.addWidget(QLabel("Nome do Ângulo:"))
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Angulo_Joelho")
        h_nome.addWidget(self.input_nome)
        layout_saida.addLayout(h_nome)

        h_unid = QHBoxLayout()
        h_unid.addWidget(QLabel("Unidade:"))
        self.radio_graus = QRadioButton("Graus (°)")
        self.radio_radianos = QRadioButton("Radianos (rad)")
        self.radio_graus.setChecked(True)  # Default sugerido pelo usuário
        h_unid.addWidget(self.radio_graus)
        h_unid.addWidget(self.radio_radianos)
        h_unid.addStretch()
        layout_saida.addLayout(h_unid)

        layout_principal.addWidget(grupo_saida)

        # Modo de Cálculo
        grupo_modo = QGroupBox("Modo de Cálculo")
        layout_modo = QHBoxLayout(grupo_modo)

        self.radio_relativo = QRadioButton("Ângulo Relativo\n(3 pontos)")
        self.radio_vetores = QRadioButton("Ângulo entre Vetores\n(4 pontos)")

        self.radio_relativo.setChecked(True)

        layout_modo.addWidget(self.radio_relativo)
        layout_modo.addWidget(self.radio_vetores)
        layout_principal.addWidget(grupo_modo)

        # Definição dos Pontos
        self.grupo_pontos = QGroupBox("Definição dos Pontos")
        self.layout_pontos = QVBoxLayout(self.grupo_pontos)

        # Label de aviso quando não há pontos 3D
        self.label_sem_pontos = QLabel(
            "Nenhum dado com formato de Posição 3D (ex: M_x, M_y, M_z) foi encontrado neste arquivo."
        )
        self.label_sem_pontos.setWordWrap(True)
        self.label_sem_pontos.hide()
        self.layout_pontos.addWidget(self.label_sem_pontos)

        # Modo Relativo
        self.widget_relativo = QWidget()
        layout_relativo = QVBoxLayout(self.widget_relativo)

        h_p1 = QHBoxLayout()
        h_p1.addWidget(QLabel("Ponto 1:"))
        self.combo_rel_p1 = QComboBox()
        h_p1.addWidget(self.combo_rel_p1)
        layout_relativo.addLayout(h_p1)

        h_vertice = QHBoxLayout()
        h_vertice.addWidget(QLabel("Vértice (Meio):"))
        self.combo_rel_vertice = QComboBox()
        h_vertice.addWidget(self.combo_rel_vertice)
        layout_relativo.addLayout(h_vertice)

        h_p3 = QHBoxLayout()
        h_p3.addWidget(QLabel("Ponto 3:"))
        self.combo_rel_p3 = QComboBox()
        h_p3.addWidget(self.combo_rel_p3)
        layout_relativo.addLayout(h_p3)

        self.layout_pontos.addWidget(self.widget_relativo)

        # Modo Vetores
        self.widget_vetores = QWidget()
        layout_vetores = QVBoxLayout(self.widget_vetores)

        h_v1 = QHBoxLayout()
        h_v1.addWidget(QLabel("Vetor 1  - Origem:"))
        self.combo_vet_p1_ini = QComboBox()
        h_v1.addWidget(self.combo_vet_p1_ini)
        h_v1.addWidget(QLabel("    Destino:"))
        self.combo_vet_p1_fim = QComboBox()
        h_v1.addWidget(self.combo_vet_p1_fim)
        layout_vetores.addLayout(h_v1)

        h_v2 = QHBoxLayout()
        h_v2.addWidget(QLabel("Vetor 2  - Origem:"))
        self.combo_vet_p2_ini = QComboBox()
        h_v2.addWidget(self.combo_vet_p2_ini)
        h_v2.addWidget(QLabel("    Destino:"))
        self.combo_vet_p2_fim = QComboBox()
        h_v2.addWidget(self.combo_vet_p2_fim)
        layout_vetores.addLayout(h_v2)

        self.widget_vetores.hide()
        self.layout_pontos.addWidget(self.widget_vetores)

        layout_principal.addWidget(self.grupo_pontos)

        # Connect radios
        self.radio_relativo.toggled.connect(self._atualizar_visibilidade_modos)
        self.radio_vetores.toggled.connect(self._atualizar_visibilidade_modos)

        # Conecta mudança de arquivo
        self.combo_arquivo.currentTextChanged.connect(self._atualizar_pontos_3d)

        # Checkbox para plotar automaticamente
        self.checkbox_plotar_auto = QCheckBox("Plotar automaticamente o ângulo criado")
        self.checkbox_plotar_auto.setChecked(True)
        layout_principal.addWidget(self.checkbox_plotar_auto)

        # Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_criar = QPushButton("Criar Ângulo")
        self.btn_criar.clicked.connect(self._validar_e_criar)
        layout_botoes.addWidget(btn_cancelar)
        layout_botoes.addWidget(self.btn_criar)
        layout_principal.addLayout(layout_botoes)

        # Inicializa pontos 3D
        self.pontos_3d = {}
        self._atualizar_pontos_3d()

    def _get_df_ativo(self):
        nome = self.combo_arquivo.currentText()
        if nome and nome in self.guarda_arquivos:
            self._nome_arquivo_selecionado = nome
            return self.guarda_arquivos[nome]["dataframe"]
        return None

    def _atualizar_pontos_3d(self):
        """Atualiza os combos de pontos 3D quando o arquivo muda."""
        df = self._get_df_ativo()
        if df is None:
            self.pontos_3d = {}
            self.label_sem_pontos.show()
            self.widget_relativo.hide()
            self.widget_vetores.hide()
            self.btn_criar.setEnabled(False)
            return

        self.pontos_3d = agrupar_pontos_3d(list(df.columns))
        nomes_pontos = list(self.pontos_3d.keys())

        if not nomes_pontos:
            self.label_sem_pontos.show()
            self.widget_relativo.hide()
            self.widget_vetores.hide()
            self.btn_criar.setEnabled(False)
            return

        self.label_sem_pontos.hide()
        self.btn_criar.setEnabled(True)
        self._atualizar_visibilidade_modos()

        # Atualiza todos os combos de pontos
        for combo in [
            self.combo_rel_p1,
            self.combo_rel_vertice,
            self.combo_rel_p3,
            self.combo_vet_p1_ini,
            self.combo_vet_p1_fim,
            self.combo_vet_p2_ini,
            self.combo_vet_p2_fim,
        ]:
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(nomes_pontos)
            combo.blockSignals(False)

    def _atualizar_visibilidade_modos(self):
        if self.radio_relativo.isChecked():
            self.widget_relativo.show()
            self.widget_vetores.hide()
        elif self.radio_vetores.isChecked():
            self.widget_relativo.hide()
            self.widget_vetores.show()

    def _validar_e_criar(self):
        df = self._get_df_ativo()
        if df is None:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo disponível.")
            return

        nome = self.input_nome.text().strip()

        if not nome:
            QMessageBox.warning(
                self, "Nome Inválido", "Informe um nome para o novo ângulo."
            )
            return

        unidade = "graus" if self.radio_graus.isChecked() else "radianos"
        unidade_str = "deg" if unidade == "graus" else "rad"

        if nome in df.columns:
            QMessageBox.warning(
                self,
                "Nome Duplicado",
                f"A variável '{nome}' já existe neste arquivo.\nEscolha outro nome.",
            )
            return

        if self.radio_relativo.isChecked():
            modo = "relativo"
            p1_nome = self.combo_rel_p1.currentText()
            vert_nome = self.combo_rel_vertice.currentText()
            p3_nome = self.combo_rel_p3.currentText()

            if p1_nome == vert_nome or p3_nome == vert_nome or p1_nome == p3_nome:
                QMessageBox.warning(
                    self,
                    "Pontos Inválidos",
                    "Os pontos que formam o ângulo devem ser distintos.",
                )
                return

            dict_pontos = {
                "p1": self.pontos_3d[p1_nome],
                "vertice": self.pontos_3d[vert_nome],
                "p3": self.pontos_3d[p3_nome],
            }
        else:
            modo = "vetores"
            p1_ini = self.combo_vet_p1_ini.currentText()
            p1_fim = self.combo_vet_p1_fim.currentText()
            p2_ini = self.combo_vet_p2_ini.currentText()
            p2_fim = self.combo_vet_p2_fim.currentText()

            if p1_ini == p1_fim or p2_ini == p2_fim:
                QMessageBox.warning(
                    self,
                    "Vetores Inválidos",
                    "Os pontos de início e fim de um vetor devem ser diferentes.",
                )
                return

            dict_pontos = {
                "p1_ini": self.pontos_3d[p1_ini],
                "p1_fim": self.pontos_3d[p1_fim],
                "p2_ini": self.pontos_3d[p2_ini],
                "p2_fim": self.pontos_3d[p2_fim],
            }

        try:
            resultado, erro = operar_angulo_3d(df, modo, dict_pontos, unidade)
            if erro:
                QMessageBox.warning(self, "Erro", erro)
                return

            if modo == "relativo":
                detalhe = f"Origem: {p1_nome}, Vértice: {vert_nome}, Destino: {p3_nome}"
                acao = "Ângulo Relativo (3 Pontos)"
            else:
                detalhe = f"Vetor A (de {p1_ini} para {p1_fim}), Vetor B (de {p2_ini} para {p2_fim})"
                acao = "Ângulo Inter-Vetorial (4 Pontos)"

            self._resultado = {
                "nome": nome,
                "valores": resultado,
                "unidade": unidade_str,
                "nome_arquivo": self._nome_arquivo_selecionado,
                "plotar_auto": self.checkbox_plotar_auto.isChecked(),
                "pipeline_step": {
                    "categoria": "Operações e Atributos",
                    "acao": acao,
                    "variavel_gerada": nome,
                    "detalhe": detalhe,
                },
            }
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Erro de Cálculo", f"Falha ao calcular o ângulo:\n{e}"
            )

    def get_resultado(self):
        return self._resultado


class JanelaExcluirReferencias(PadraoDialog):
    def __init__(self, linhas_referencia, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excluir Linhas de Referência")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecione as linhas para excluir:"))

        self.checkboxes = []
        for lr in linhas_referencia:
            cb = QCheckBox(lr.get("titulo", "Referência"))
            self.checkboxes.append(cb)
            layout.addWidget(cb)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Excluir")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_indices_remover(self):
        return [i for i, cb in enumerate(self.checkboxes) if cb.isChecked()]


class JanelaSelecionarVariosArquivos(PadraoDialog):
    def __init__(self, nomes_arquivos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar Histórico")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecione os arquivos para exportar o histórico:"))

        self.btn_selecionar_todos = QPushButton("Desmarcar todos")
        self.btn_selecionar_todos.clicked.connect(self._selecionar_todos)
        layout.addWidget(self.btn_selecionar_todos)

        from PyQt6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)

        self.checkboxes = {}
        for nome in nomes_arquivos:
            cb = QCheckBox(nome)
            cb.setChecked(True)
            self.checkboxes[nome] = cb
            container_layout.addWidget(cb)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_ok = QPushButton("Continuar")
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
