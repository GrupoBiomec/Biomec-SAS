from ui.utils import PadraoDialog

# Janelas de diálogo para processamento de dados.
# (Preenchimento de Lacunas, Ajustes de Exibição)

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QWidget,
    QCheckBox,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import pandas as pd
from processamento.operacoes import (
    interpolacao_linear,
    interpolacao_spline,
    interpolacao_media,
)

# Constante compartilhada de cores para diálogos de edição
CORES_MAP = {
    "r": "Vermelho",
    "g": "Verde",
    "b": "Azul",
    "c": "Ciano",
    "m": "Magenta",
    "y": "Amarelo",
    "k": "Preto",
    "darkgreen": "Verde Escuro",
    "darkorange": "Laranja",
    "purple": "Roxo",
    "brown": "Marrom",
}
CORES_NOMES = list(CORES_MAP.values())
CORES_SIGLAS = list(CORES_MAP.keys())


class JanelaPreencherLacunas(PadraoDialog):
    def __init__(self, estado, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self.checkboxes = {}

        self.setWindowTitle("Preencher Lacunas")
        self.setMinimumSize(450, 450)

        layout = QVBoxLayout(self)

        titulo = QLabel("Selecione arquivos e dados com lacunas para interporlar:")
        titulo.setStyleSheet("font-weight: bold;")
        layout.addWidget(titulo)

        layout.addWidget(QLabel("Método de Interpolação:"))
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(["Linear", "Spline", "Média"])
        layout.addWidget(self.combo_metodo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)

        arquivos_com_lacunas = 0
        for nome_arq, dados_arq in self.guarda_arquivos.items():
            df = dados_arq["dataframe"]
            try:
                cols_nan = []
                for col in df.columns:
                    primeiro_valido = df[col].first_valid_index()
                    ultimo_valido = df[col].last_valid_index()
                    if primeiro_valido is not None and ultimo_valido is not None:
                        if df.loc[primeiro_valido:ultimo_valido, col].isna().any():
                            cols_nan.append(col)
            except Exception:
                continue
            if not cols_nan:
                continue

            arquivos_com_lacunas += 1
            lbl_arq = QLabel(f"<b>{nome_arq}</b>")
            self.scroll_layout.addWidget(lbl_arq)

            self.checkboxes[nome_arq] = {}

            cb_todos = QCheckBox("  [Selecionar Todos]")
            self.checkboxes[nome_arq]["_all_"] = cb_todos
            self.scroll_layout.addWidget(cb_todos)

            for col in cols_nan:
                cb = QCheckBox(f"    {col}")
                self.checkboxes[nome_arq][col] = cb
                self.scroll_layout.addWidget(cb)

            self._conectar_selecionar_todos(nome_arq, cb_todos, cols_nan)

        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        if arquivos_com_lacunas == 0:
            lbl_vazio = QLabel("Nenhum dado com lacunas (NaN) encontrado.")
            lbl_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_vazio)
            self.combo_metodo.setEnabled(False)

        # Checkbox de plotagem
        self.chk_plotar_auto = QCheckBox("Plotar variáveis alteradas automaticamente")
        self.chk_plotar_auto.setChecked(True)
        layout.addWidget(self.chk_plotar_auto)

        # Removido radio buttons de salvar como novo / alterar original (agora é padrão gerar novo)

        botoes = QHBoxLayout()
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(self._abrir_preview)
        btn_ok = QPushButton("Aplicar")
        btn_ok.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        if arquivos_com_lacunas == 0:
            btn_ok.setEnabled(False)
            self.btn_preview.setEnabled(False)

        botoes.addWidget(self.btn_preview)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addLayout(botoes)

    def _abrir_preview(self):
        selecoes, metodo = self.get_selecoes()
        if not selecoes:
            QMessageBox.warning(
                self, "Aviso", "Nenhuma coluna selecionada para interpolação."
            )
            return

        if len(selecoes) > 1:
            QMessageBox.warning(
                self,
                "Aviso",
                "A Preview só pode ser exibida para variáveis de um único arquivo simultaneamente. Por favor, selecione variáveis de apenas um arquivo.",
            )
            return

        nome_arq = list(selecoes.keys())[0]
        cols_sel = selecoes[nome_arq]

        dados_arq = self.guarda_arquivos[nome_arq]

        preview = JanelaPreviewInterpolacao(nome_arq, cols_sel, dados_arq, metodo, self)
        if preview.exec():
            self.metodo_por_variavel_preview = preview.metodo_por_variavel
            # pontos manuais inseridos no wywiwyg
            self.pontos_manuais_preview = preview.pontos_manuais
            self.accept()

    def _conectar_selecionar_todos(self, nome_arq, cb_todos, cols):
        def on_todos_changed(state):
            is_checked = state == Qt.CheckState.Checked.value or state == 2
            for col in cols:
                self.checkboxes[nome_arq][col].setChecked(is_checked)

        cb_todos.stateChanged.connect(on_todos_changed)

    def get_selecoes(self):
        selecoes = {}
        for nome_arq, cbs in self.checkboxes.items():
            selecionadas = []
            for col, cb in cbs.items():
                if col != "_all_" and cb.isChecked():
                    selecionadas.append(col)
            if selecionadas:
                selecoes[nome_arq] = selecionadas
        return selecoes, self.combo_metodo.currentText()


class JanelaSelecionarGraficosInterpolados(PadraoDialog):
    """Após interpolação, mostra gráficos que usam as colunas interpoladas
    para o usuário escolher quais recriar com a nova coluna."""

    def __init__(self, graficos_afetados, parent=None):
        """
        graficos_afetados: lista de dicts com:
            - 'arquivo': nome do arquivo
            - 'grafico': nome do gráfico
            - 'coluna_original': coluna Y original
            - 'coluna_nova': coluna Y interpolada
            - 'eixo_x': coluna X
        """
        super().__init__(parent)
        self.setWindowTitle("Gráficos com Variáveis Interpoladas")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        self.graficos_afetados = graficos_afetados
        self.checkboxes = []

        layout = QVBoxLayout(self)

        titulo = QLabel(
            "As colunas interpoladas foram criadas com sucesso.\n"
            "Selecione os gráficos que deseja recriar com as novas variáveis:"
        )
        titulo.setStyleSheet("font-weight: bold;")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        arquivo_atual = None
        for info in graficos_afetados:
            # Agrupa por arquivo
            if info["arquivo"] != arquivo_atual:
                arquivo_atual = info["arquivo"]
                lbl_arq = QLabel(f"<b>{arquivo_atual}</b>")
                scroll_layout.addWidget(lbl_arq)

            texto = f"  {info['grafico']}  →  {info['coluna_nova']} x {info['eixo_x']}"
            cb = QCheckBox(texto)
            cb.setChecked(True)
            self.checkboxes.append((cb, info))
            scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        botoes = QHBoxLayout()
        btn_ok = QPushButton("Recriar Gráficos Selecionados")
        btn_ok.clicked.connect(self.accept)
        btn_pular = QPushButton("Pular (não recriar gráficos)")
        btn_pular.clicked.connect(self.reject)
        botoes.addStretch()
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_pular)
        layout.addLayout(botoes)

    def get_selecionados(self):
        """Retorna lista de dicts dos gráficos selecionados."""
        return [info for cb, info in self.checkboxes if cb.isChecked()]


class JanelaAjustesExibicao(PadraoDialog):
    def __init__(
        self, lista_configs, nome_grafico_atual="", parent=None, configs_originais=None
    ):
        """
        Recebe uma lista de dicionários (configs dos traços) para edição das legendas e cores.
        Para gráficos normais, haverá apenas 1 item. Para sobrepostos, 2 ou mais.
        configs_originais: lista de configs reais dos gráficos (para encontrar linhas_referencia).
        Para gráficos normais, é igual a lista_configs. Para sobrepostos, resolve os configs originais.
        """
        super().__init__(parent)
        self.setWindowTitle("Ajustes de Exibição")
        self.setMinimumWidth(400)

        self.lista_configs = lista_configs
        self.configs_originais = configs_originais or lista_configs
        self.widgets_edicao = []  # guardará tuplas (dict_ref, input_nome, combo_cor)
        self.widgets_referencia = (
            []
        )  # guardará tuplas (dict_ref_linha, input_titulo, combo_cor)

        layout = QVBoxLayout(self)

        # Campo de edição do Nome do Gráfico (Global para a janela)
        h_titulo = QHBoxLayout()
        h_titulo.addWidget(QLabel("Nome do Gráfico:"))
        self.input_titulo = QLineEdit(nome_grafico_atual)
        h_titulo.addWidget(self.input_titulo)
        layout.addLayout(h_titulo)

        self.cores_nomes = CORES_NOMES
        self.cores_siglas = CORES_SIGLAS

        if len(self.lista_configs) == 1:
            # Gráfico normal (1 traço) -> Edita os rótulos de eixo X e Y, além da cor principal
            ref_grafico = self.lista_configs[0]
            layout.addWidget(QLabel("Edite os rótulos dos eixos e a cor principal:"))

            group = QWidget()
            v_layout = QVBoxLayout(group)

            # Eixo X
            valor_x = ref_grafico.get("label_x", ref_grafico.get("eixo_x", "Eixo X"))
            h_x = QHBoxLayout()
            h_x.addWidget(QLabel("Rótulo Eixo X:"))
            self.input_eixo_x = QLineEdit(valor_x)
            h_x.addWidget(self.input_eixo_x)
            v_layout.addLayout(h_x)

            # Eixo Y
            if "dados_y_calc" in ref_grafico:
                valor_y_def = ref_grafico.get("titulo", "Y")
            else:
                valor_y_def = ref_grafico.get("eixo_y", "Y")
            valor_y = ref_grafico.get("label_y", valor_y_def)
            h_y = QHBoxLayout()
            h_y.addWidget(QLabel("Rótulo Eixo Y:"))
            self.input_eixo_y = QLineEdit(valor_y)
            h_y.addWidget(self.input_eixo_y)
            v_layout.addLayout(h_y)

            # Cor
            cor_atual = ref_grafico.get("cor", "b")
            self.combo_cor_simples = QComboBox()
            self.combo_cor_simples.addItems(self.cores_nomes)
            if cor_atual in self.cores_siglas:
                self.combo_cor_simples.setCurrentIndex(
                    self.cores_siglas.index(cor_atual)
                )
            h_cor = QHBoxLayout()
            h_cor.addWidget(QLabel("Cor da Linha:"))
            h_cor.addWidget(self.combo_cor_simples)
            v_layout.addLayout(h_cor)

            layout.addWidget(group)

        else:
            # Sobreposição -> Edita lgenda das linhas + cor de cada uma

            for i, ref_grafico in enumerate(self.lista_configs):
                group = QWidget()
                h_layout = QHBoxLayout(group)

                arquivo = ref_grafico.get("arquivo", "")
                grafico = ref_grafico.get("grafico", f"Traço {i+1}")
                nome_default = ref_grafico.get(
                    "nome_legenda", f"{arquivo} - {grafico}" if arquivo else grafico
                )
                input_nome = QLineEdit(nome_default)

                cor_atual = ref_grafico.get(
                    "cor", self.cores_siglas[i % len(self.cores_siglas)]
                )
                combo_cor = QComboBox()
                combo_cor.addItems(self.cores_nomes)
                if cor_atual in self.cores_siglas:
                    idx = self.cores_siglas.index(cor_atual)
                    combo_cor.setCurrentIndex(idx)

                h_layout.addWidget(QLabel("Legenda:"))
                h_layout.addWidget(input_nome)
                h_layout.addWidget(QLabel("Cor:"))
                h_layout.addWidget(combo_cor)

                self.widgets_edicao.append((ref_grafico, input_nome, combo_cor))
                layout.addWidget(group)

        # Linhas de Referência (polinômios)
        todas_refs = self._coletar_referencias()
        if todas_refs:
            layout.addSpacing(10)
            lbl_refs = QLabel("Linhas de Referência (Polinômios):")
            lbl_refs.setStyleSheet("font-weight: bold;")
            layout.addWidget(lbl_refs)

            for ref_dict in todas_refs:
                group_ref = QWidget()
                h_ref = QHBoxLayout(group_ref)
                h_ref.setContentsMargins(10, 2, 10, 2)

                input_titulo_ref = QLineEdit(ref_dict.get("titulo", "Referência"))

                cor_ref_atual = ref_dict.get("cor", "r")
                combo_cor_ref = QComboBox()
                combo_cor_ref.addItems(self.cores_nomes)
                if cor_ref_atual in self.cores_siglas:
                    combo_cor_ref.setCurrentIndex(
                        self.cores_siglas.index(cor_ref_atual)
                    )

                h_ref.addWidget(QLabel("Título:"))
                h_ref.addWidget(input_titulo_ref)
                h_ref.addWidget(QLabel("Cor:"))
                h_ref.addWidget(combo_cor_ref)

                self.widgets_referencia.append(
                    (ref_dict, input_titulo_ref, combo_cor_ref)
                )
                layout.addWidget(group_ref)

        botoes_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_confirmar = QPushButton("Aplicar Ajustes")
        btn_confirmar.clicked.connect(self.accept)
        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_cancelar)
        botoes_layout.addWidget(btn_confirmar)
        layout.addLayout(botoes_layout)

    def _coletar_referencias(self):
        """Coleta todas as linhas de referência dos configs originais."""
        todas = []
        for cfg in self.configs_originais:
            for ref in cfg.get("linhas_referencia", []):
                todas.append(ref)
        return todas

    def get_novo_nome(self):
        return self.input_titulo.text().strip()

    def aplicar_alteracoes(self):
        """Atualiza a lista de dicionários original fornecida com os valores dos botões"""
        if len(self.lista_configs) == 1:
            ref_grafico = self.lista_configs[0]
            ref_grafico["label_x"] = self.input_eixo_x.text().strip()
            ref_grafico["label_y"] = self.input_eixo_y.text().strip()
            ref_grafico["cor"] = self.cores_siglas[
                self.combo_cor_simples.currentIndex()
            ]
        else:
            for ref_grafico, input_nome, combo_cor in self.widgets_edicao:
                novo_nome = input_nome.text().strip()
                if novo_nome:
                    ref_grafico["nome_legenda"] = novo_nome
                idx_cor = combo_cor.currentIndex()
                ref_grafico["cor"] = self.cores_siglas[idx_cor]

        # Aplica alterações nas linhas de referência
        for ref_dict, input_titulo, combo_cor in self.widgets_referencia:
            novo_titulo = input_titulo.text().strip()
            if novo_titulo:
                ref_dict["titulo"] = novo_titulo
            ref_dict["cor"] = self.cores_siglas[combo_cor.currentIndex()]


class JanelaEditarExibicaoSimultanea(PadraoDialog):
    # Janela do modo editar da exibição simultânea.
    # Permite renomear a composição e customizar título e cor de cada gráfico dentro do layout.

    def __init__(self, nome_atual, config_simultanea, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Exibição Simultânea")
        self.setMinimumWidth(450)

        self.config = config_simultanea
        self.widgets_graficos = []  # [(ref_dict, input_titulo, combo_cor)]

        self.cores_nomes = CORES_NOMES
        self.cores_siglas = CORES_SIGLAS

        layout = QVBoxLayout(self)

        # Nome da composição
        h_nome = QHBoxLayout()
        h_nome.addWidget(QLabel("Nome da Composição:"))
        self.input_nome = QLineEdit(nome_atual)
        h_nome.addWidget(self.input_nome)
        layout.addLayout(h_nome)

        layout.addSpacing(10)

        # Gráficos individuais
        lbl_graficos = QLabel("Gráficos na composição:")
        lbl_graficos.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_graficos)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        rows = self.config.get("layout", [])
        for row in rows:
            for ref in row:
                if ref is None:
                    continue

                group = QWidget()
                group.setStyleSheet(
                    "QWidget { border: 1px solid #ddd; border-radius: 4px; padding: 4px; }"
                )
                v_group = QVBoxLayout(group)
                v_group.setContentsMargins(8, 6, 8, 6)

                # Info de origem (não editável)
                lbl_origem = QLabel(
                    f"Origem: {ref.get('label', ref.get('grafico', ''))}"
                )
                lbl_origem.setStyleSheet("color: #888; font-size: 11px; border: none;")
                v_group.addWidget(lbl_origem)

                h_campos = QHBoxLayout()

                # Título customizado
                titulo_atual = ref.get("titulo_custom", ref.get("grafico", ""))
                lbl_titulo = QLabel("Título:")
                lbl_titulo.setStyleSheet("border: none;")
                input_titulo = QLineEdit(titulo_atual)
                input_titulo.setStyleSheet(
                    "border: 1px solid #999; border-radius: 3px; padding: 3px;"
                )
                h_campos.addWidget(lbl_titulo)
                h_campos.addWidget(input_titulo)

                # Cor customizada
                cor_atual = ref.get("cor_custom", "b")
                lbl_cor = QLabel("Cor:")
                lbl_cor.setStyleSheet("border: none;")
                combo_cor = QComboBox()
                combo_cor.addItems(self.cores_nomes)
                if cor_atual in self.cores_siglas:
                    combo_cor.setCurrentIndex(self.cores_siglas.index(cor_atual))
                h_campos.addWidget(lbl_cor)
                h_campos.addWidget(combo_cor)

                v_group.addLayout(h_campos)

                self.widgets_graficos.append((ref, input_titulo, combo_cor))
                scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        #  Botões
        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(self._validar_e_aceitar)
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_aplicar)
        layout.addLayout(botoes)

    def _validar_e_aceitar(self):
        if not self.input_nome.text().strip():
            QMessageBox.warning(
                self, "Nome Obrigatório", "Digite um nome para a composição."
            )
            return
        self.accept()

    def get_novo_nome(self):
        return self.input_nome.text().strip()

    def aplicar_alteracoes(self):
        """Salva os títulos e cores customizados nos dicts de referência do layout."""
        for ref, input_titulo, combo_cor in self.widgets_graficos:
            titulo = input_titulo.text().strip()
            if titulo:
                ref["titulo_custom"] = titulo
            ref["cor_custom"] = self.cores_siglas[combo_cor.currentIndex()]


class JanelaSelecionarGraficoFiltro(PadraoDialog):
    def __init__(
        self, tipo_filtro, guarda_graficos, arquivo_ativo, grafico_ativo, parent=None
    ):
        super().__init__(parent)
        nome_filtro_str = (
            "Passa-Baixa" if tipo_filtro == "passa_baixa" else "Passa-Alta"
        )
        self.setWindowTitle(f"Filtro {nome_filtro_str} — Selecionar Gráfico")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecione o gráfico para aplicar o filtro:"))

        self.combo_grafico = QComboBox()
        idx_pre_selecionado = -1
        item_idx = 0
        arquivo_anterior = None

        for nome_arq, dict_grafs in guarda_graficos.items():
            for nome_graf, dados in dict_grafs.items():
                if dados.get("tipo") == "Sobreposto":
                    continue

                if arquivo_anterior != nome_arq:
                    if arquivo_anterior is not None:
                        self.combo_grafico.insertSeparator(item_idx)
                        item_idx += 1
                    arquivo_anterior = nome_arq

                    self.combo_grafico.addItem(nome_arq)
                    self.combo_grafico.setItemData(item_idx, None)
                    model = self.combo_grafico.model()
                    item_model = model.item(item_idx)
                    item_model.setEnabled(False)
                    item_idx += 1

                texto_display = f"      {nome_graf}"
                self.combo_grafico.addItem(
                    texto_display, userData=(nome_arq, nome_graf)
                )

                if arquivo_ativo == nome_arq and grafico_ativo == nome_graf:
                    idx_pre_selecionado = item_idx

                item_idx += 1

        if idx_pre_selecionado != -1:
            self.combo_grafico.setCurrentIndex(idx_pre_selecionado)
        else:
            self.combo_grafico.setCurrentIndex(-1)

        layout.addWidget(self.combo_grafico)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Continuar")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_selecao(self):
        return self.combo_grafico.currentData()


class JanelaMultiplasCurvas(PadraoDialog):
    def __init__(self, colunas, unidades_colunas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visualizar Múltiplas Curvas")
        self.setMinimumWidth(400)

        # Classifica colunas em categorias
        self.categorias_map = {
            "Posição/Distância": ["m", "cm", "mm"],
            "Força": ["n", "N"],
            "Torque": ["nm", "n.m", "N.m", "Nm"],
            "EMG": ["v", "mv", "uv", "V", "mV", "uV"],
            "Ângulo": ["graus", "deg", "rad", "º", "radianos"],
            "Velocidade": ["m/s", "cm/s", "mm/s", "rad/s", "deg/s"],
        }

        self.colunas_por_categoria = {k: [] for k in self.categorias_map.keys()}
        self.colunas_por_categoria["Outros"] = []

        for col in colunas:
            unit = unidades_colunas.get(col, "").strip()
            if not unit:
                self.colunas_por_categoria["Outros"].append(col)
                continue

            encontrou = False
            for cat, un_list in self.categorias_map.items():
                if unit in un_list or unit.lower() in [u.lower() for u in un_list]:
                    self.colunas_por_categoria[cat].append(col)
                    encontrou = True
                    break
            if not encontrou:
                self.colunas_por_categoria["Outros"].append(col)

        # Filtrar apenas categorias com itens
        self.categorias_ativas = {
            k: v for k, v in self.colunas_por_categoria.items() if v
        }

        layout = QVBoxLayout(self)

        if not self.categorias_ativas:
            layout.addWidget(
                QLabel("Nenhuma coluna válida encontrada para agrupamento.")
            )
            btn_cancel = QPushButton("Fechar")
            btn_cancel.clicked.connect(self.reject)
            layout.addWidget(btn_cancel)
            return

        # Eixo X
        layout.addWidget(QLabel("Selecione o Eixo X:"))
        self.combo_x = QComboBox()
        self.combo_x.addItems(colunas)
        # Tenta selecionar 'time' ou 'frame' ou 'Tempo'
        x_col = None
        for c in colunas:
            if c.lower() in ["time", "tempo", "item"]:
                x_col = c
                break
        if not x_col:
            for c in colunas:
                if c.lower() in ["frame", "frames"]:
                    x_col = c
                    break
        if x_col:
            self.combo_x.setCurrentText(x_col)
        layout.addWidget(self.combo_x)

        # Nome da Composição
        layout.addWidget(QLabel("Nome da Composição:"))
        self.input_nome = QLineEdit()
        layout.addWidget(self.input_nome)

        # Categoria
        layout.addWidget(QLabel("Categoria de Dados (Eixo Y):"))

        h_cat = QHBoxLayout()
        self.combo_categoria = QComboBox()
        self.combo_categoria.addItems(list(self.categorias_ativas.keys()))
        self.combo_categoria.currentTextChanged.connect(self._atualizar_lista)
        h_cat.addWidget(self.combo_categoria)

        self.btn_selecionar_todos = QPushButton("Selecionar todos")
        self.btn_selecionar_todos.clicked.connect(self._selecionar_todos)
        h_cat.addWidget(self.btn_selecionar_todos)

        layout.addLayout(h_cat)

        # Scroll Area para Checkboxes
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll)

        self.checkboxes = {}

        # Botoes
        botoes = QHBoxLayout()
        btn_ok = QPushButton("Plotar Múltiplas Curvas")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addLayout(botoes)

        if self.categorias_ativas:
            self._atualizar_lista(list(self.categorias_ativas.keys())[0])

    def _atualizar_lista(self, categoria):
        # Limpar layout atual
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.checkboxes.clear()

        if categoria not in self.categorias_ativas:
            return

        # Sugerir nome
        self.input_nome.setText(f"Múltiplas Curvas - {categoria}")

        for col in self.categorias_ativas[categoria]:
            cb = QCheckBox(col)
            cb.setChecked(False)
            self.scroll_layout.addWidget(cb)
            self.checkboxes[col] = cb

        self.scroll_layout.addStretch()
        self.btn_selecionar_todos.setText("Selecionar todos")

    def _selecionar_todos(self):
        todos_marcados = all(cb.isChecked() for cb in self.checkboxes.values())
        novo_estado = not todos_marcados
        for cb in self.checkboxes.values():
            cb.setChecked(novo_estado)

            self.btn_selecionar_todos.setText("Selecionar todos")

    def get_selecoes(self):
        selecionados = [col for col, cb in self.checkboxes.items() if cb.isChecked()]
        return {
            "eixo_x": self.combo_x.currentText(),
            "nome": self.input_nome.text() or self.combo_categoria.currentText(),
            "eixo_y_lista": selecionados,
        }


class JanelaPlotarSeparadamente(PadraoDialog):
    def __init__(self, graficos_disponiveis, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plotar Separadamente")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Selecione quais curvas deseja extrair para gráficos individuais:")
        )

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll)

        self.checkboxes = {}
        for graf in graficos_disponiveis:
            cb = QCheckBox(graf)
            cb.setChecked(False)
            self.scroll_layout.addWidget(cb)
            self.checkboxes[graf] = cb

        self.scroll_layout.addStretch()

        botoes = QHBoxLayout()
        btn_ok = QPushButton("Extrair Selecionados")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addLayout(botoes)

    def get_selecionados(self):
        return [g for g, cb in self.checkboxes.items() if cb.isChecked()]


class JanelaSelecionarVariaveisOffset(PadraoDialog):
    def __init__(self, estado, arquivo_atual=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self.setWindowTitle("Definir Offset - Selecionar Variáveis")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("1. Selecione o Arquivo:"))

        self.combo_arquivo = QComboBox()
        self.combo_arquivo.addItems(list(self.guarda_arquivos.keys()))
        if arquivo_atual and arquivo_atual in self.guarda_arquivos:
            self.combo_arquivo.setCurrentText(arquivo_atual)
        self.combo_arquivo.currentTextChanged.connect(self._atualizar_variaveis)
        layout.addWidget(self.combo_arquivo)

        layout.addWidget(
            QLabel("2. Selecione as Variáveis (devem ser da mesma categoria):")
        )

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll)

        self.checkboxes = {}

        botoes = QHBoxLayout()
        btn_ok = QPushButton("Avançar")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.aceitar)
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addLayout(botoes)

        self._atualizar_variaveis(self.combo_arquivo.currentText())

    def _atualizar_variaveis(self, nome_arquivo):
        # Limpa layout atual
        for i in reversed(range(self.scroll_layout.count())):
            widget_to_remove = self.scroll_layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)

        self.checkboxes.clear()

        if not nome_arquivo or nome_arquivo not in self.guarda_arquivos:
            return

        dados_arquivo = self.guarda_arquivos[nome_arquivo]
        df = dados_arquivo["dataframe"]
        colunas = list(df.columns)
        unidades = dados_arquivo.get("unidades_colunas", {})

        # Categorização igual a JanelaMultiplasCurvas
        categorias_map = {
            "Posição/Distância": ["m", "cm", "mm"],
            "Força": ["n", "N"],
            "Torque": ["nm", "n.m", "N.m", "Nm"],
            "EMG": ["v", "mv", "uv", "V", "mV", "uV"],
            "Ângulo": ["graus", "deg", "rad", "º", "radianos"],
            "Velocidade": ["m/s", "cm/s", "mm/s", "rad/s", "deg/s"],
        }

        colunas_por_categoria = {k: [] for k in categorias_map.keys()}
        colunas_por_categoria["Outros"] = []

        for col in colunas:
            if col.lower() in ["time", "tempo", "frame", "frames", "item"]:
                continue
            unit = unidades.get(col, "").strip()
            if not unit:
                colunas_por_categoria["Outros"].append(col)
                continue
            encontrou = False
            for cat, un_list in categorias_map.items():
                if unit in un_list or unit.lower() in [u.lower() for u in un_list]:
                    colunas_por_categoria[cat].append(col)
                    encontrou = True
                    break
            if not encontrou:
                colunas_por_categoria["Outros"].append(col)

        for cat, cols in colunas_por_categoria.items():
            if not cols:
                continue

            lbl = QLabel(f"<b>{cat}</b>")
            self.scroll_layout.addWidget(lbl)

            cb_todos = QCheckBox("  [Selecionar Todos]")
            self.scroll_layout.addWidget(cb_todos)

            cat_cbs = []
            for col in cols:
                cb = QCheckBox(f"    {col}")
                cb.setProperty("categoria", cat)
                self.scroll_layout.addWidget(cb)
                self.checkboxes[col] = cb
                cat_cbs.append(cb)

            self._conectar_todos(cb_todos, cat_cbs)

        self.scroll_layout.addStretch()

    def _conectar_todos(self, cb_todos, cat_cbs):
        def on_change(state):
            is_checked = state == Qt.CheckState.Checked.value or state == 2
            for cb in cat_cbs:
                cb.setChecked(is_checked)

        cb_todos.stateChanged.connect(on_change)

    def aceitar(self):
        selecionados = [col for col, cb in self.checkboxes.items() if cb.isChecked()]
        if not selecionados:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma variável.")
            return

        categorias_selecionadas = set(
            [self.checkboxes[col].property("categoria") for col in selecionados]
        )
        if len(categorias_selecionadas) > 1:
            QMessageBox.warning(
                self,
                "Aviso",
                "Por favor, selecione variáveis de apenas uma categoria para definir o offset.",
            )
            return

        self.accept()

    def get_selecao(self):
        selecionadas = [col for col, cb in self.checkboxes.items() if cb.isChecked()]
        return self.combo_arquivo.currentText(), selecionadas


class JanelaSelecionarCategoriasTrim(PadraoDialog):
    def __init__(self, estado, arquivo_atual=None, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.guarda_arquivos = self.estado.get_arquivos()
        self.setWindowTitle("Recorte Temporal - Selecionar Categorias")
        self.setMinimumSize(350, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("1. Selecione o Arquivo:"))

        self.combo_arquivo = QComboBox()
        self.combo_arquivo.addItems(list(self.guarda_arquivos.keys()))
        if arquivo_atual and arquivo_atual in self.guarda_arquivos:
            self.combo_arquivo.setCurrentText(arquivo_atual)
        self.combo_arquivo.currentTextChanged.connect(self._atualizar_categorias)
        layout.addWidget(self.combo_arquivo)

        layout.addWidget(QLabel("2. Quais categorias deseja visualizar no recorte?"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll)

        self.checkboxes = {}

        botoes = QHBoxLayout()
        btn_ok = QPushButton("Avançar")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.aceitar)
        btn_cancel.clicked.connect(self.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancel)
        layout.addLayout(botoes)

        self._atualizar_categorias(self.combo_arquivo.currentText())

    def _atualizar_categorias(self, nome_arquivo):
        for i in reversed(range(self.scroll_layout.count())):
            widget_to_remove = self.scroll_layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)

        self.checkboxes.clear()

        if not nome_arquivo or nome_arquivo not in self.guarda_arquivos:
            return

        dados_arquivo = self.guarda_arquivos[nome_arquivo]
        df = dados_arquivo["dataframe"]
        colunas = list(df.columns)
        unidades = dados_arquivo.get("unidades_colunas", {})

        categorias_map = {
            "Posição/Distância": ["m", "cm", "mm"],
            "Força": ["n", "N"],
            "Torque": ["nm", "n.m", "N.m", "Nm"],
            "EMG": ["v", "mv", "uv", "V", "mV", "uV"],
            "Ângulo": ["graus", "deg", "rad", "º", "radianos"],
            "Velocidade": ["m/s", "cm/s", "mm/s", "rad/s", "deg/s"],
        }

        categorias_presentes = set()

        for col in colunas:
            if col.lower() in ["time", "tempo", "frame", "frames", "item"]:
                continue
            unit = unidades.get(col, "").strip()
            encontrou = False
            for cat, un_list in categorias_map.items():
                if unit in un_list or unit.lower() in [u.lower() for u in un_list]:
                    categorias_presentes.add(cat)
                    encontrou = True
                    break
            if not encontrou:
                categorias_presentes.add("Outros")

        for cat in sorted(list(categorias_presentes)):
            cb = QCheckBox(cat)
            self.scroll_layout.addWidget(cb)
            self.checkboxes[cat] = cb

        self.scroll_layout.addStretch()

    def aceitar(self):
        selecionados = [cat for cat, cb in self.checkboxes.items() if cb.isChecked()]
        if not selecionados:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma categoria.")
            return
        self.accept()

    def get_selecao(self):
        selecionadas = [cat for cat, cb in self.checkboxes.items() if cb.isChecked()]
        return self.combo_arquivo.currentText(), selecionadas


class JanelaPreviewInterpolacao(QDialog):
    def __init__(
        self, nome_arq, colunas_selecionadas, dados_arq, metodo_inicial, parent=None
    ):
        super().__init__(parent)
        self.nome_arq = nome_arq
        self.colunas_selecionadas = colunas_selecionadas
        self.dados_arq = dados_arq
        self.df = dados_arq["dataframe"].copy()

        self.pontos_manuais = {col: [] for col in colunas_selecionadas}
        self.scatter_item = None
        self.modo_wywiwyg = False

        # Método de interpolação por variável (permite escolha independente)
        self.metodo_por_variavel = {col: metodo_inicial for col in colunas_selecionadas}

        self.col_tempo = None
        # Prioriza 'time'/'tempo'; só usa 'frame'/'frames'/'item' se não houver
        for c in self.df.columns:
            if c.lower() in ["time", "tempo"]:
                self.col_tempo = c
                break
        if not self.col_tempo:
            for c in self.df.columns:
                if c.lower() in ["frame", "frames", "item"]:
                    self.col_tempo = c
                    break

        if self.col_tempo:
            self.x_data = self.df[self.col_tempo].values
        else:
            self.x_data = self.df.index.values

        self.setWindowTitle(f"Preview Interpolação: {nome_arq}")
        self.setMinimumSize(800, 600)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        ctrl_layout = QHBoxLayout()

        ctrl_layout.addWidget(QLabel("Variável Alvo:"))
        self.combo_alvo = QComboBox()
        self.combo_alvo.addItems(colunas_selecionadas)
        self.combo_alvo.currentTextChanged.connect(self._ao_trocar_variavel)
        ctrl_layout.addWidget(self.combo_alvo)

        ctrl_layout.addWidget(QLabel("Método:"))
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(["Linear", "Spline", "Média"])
        self.combo_metodo.setCurrentText(metodo_inicial)
        self.combo_metodo.currentTextChanged.connect(self._ao_trocar_metodo)
        ctrl_layout.addWidget(self.combo_metodo)

        self.btn_wywiwyg = QPushButton("Adicionar ponto (wywiwyg)")
        self.btn_wywiwyg.setCheckable(True)
        self.btn_wywiwyg.clicked.connect(self.toggle_wywiwyg)
        ctrl_layout.addWidget(self.btn_wywiwyg)

        self.btn_apagar = QPushButton("Apagar ponto")
        self.btn_apagar.setCheckable(True)
        self.btn_apagar.clicked.connect(self.toggle_apagar)
        ctrl_layout.addWidget(self.btn_apagar)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        aviso_lbl = QLabel(
            "Dica wywiwyg: Ative um dos botões acima e clique no gráfico para adicionar ou remover pontos manuais."
        )
        aviso_lbl.setStyleSheet("color: gray;")
        layout.addWidget(aviso_lbl)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.getAxis("bottom").setPen(pg.mkPen(color="k"))
        self.plot_widget.getAxis("bottom").setTextPen("k")
        self.plot_widget.getAxis("left").setPen(pg.mkPen(color="k"))
        self.plot_widget.getAxis("left").setTextPen("k")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setLabel(
            "bottom", self.col_tempo if self.col_tempo else "Índice"
        )
        layout.addWidget(self.plot_widget)

        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_clicked)

        btn_layout = QHBoxLayout()
        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(self.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_aplicar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)

        # Plot items para a variável atualmente exibida (criados em _montar_plot)
        self.plot_item_original = None
        self.plot_item_interpolado = None
        self.scatter_item = None

        self.cores = [
            "#e6194B",
            "#3cb44b",
            "#ffe119",
            "#4363d8",
            "#f58231",
            "#911eb4",
            "#42d4f4",
            "#f032e6",
            "#bfef45",
            "#fabed4",
        ]

        # Flag para evitar loops ao sincronizar combo_metodo ↔ variável
        self._sincronizando = False

        self._montar_plot()
        self.atualizar_preview()

    def _cor_variavel(self, col):
        """Retorna a cor associada a uma variável pelo seu índice na lista."""
        idx = (
            self.colunas_selecionadas.index(col)
            if col in self.colunas_selecionadas
            else 0
        )
        return self.cores[idx % len(self.cores)]

    def _montar_plot(self):
        """Cria os itens de plot para a variável atualmente selecionada."""
        # Limpa itens existentes
        self.plot_widget.clear()
        # Re-adiciona a legenda (clear() remove tudo)
        if self.plot_widget.plotItem.legend is not None:
            self.plot_widget.plotItem.legend.clear()

        col = self.combo_alvo.currentText()
        cor = self._cor_variavel(col)

        # Original: Linha cinza com pontos pequenos
        pen_orig = pg.mkPen(color="#808080", width=1.5)
        self.plot_item_original = self.plot_widget.plot(
            pen=pen_orig,
            symbol="o",
            symbolSize=3,
            symbolPen=None,
            symbolBrush="#808080",
            name=f"{col} (original)",
        )

        # Interpolado: Linha colorida mais grossa
        pen_interp = pg.mkPen(color=cor, width=2.5)
        self.plot_item_interpolado = self.plot_widget.plot(
            pen=pen_interp, name=f"{col} (interpolado)"
        )

        # Scatter para pontos wywiwyg
        self.scatter_item = pg.ScatterPlotItem(
            size=12, pen=pg.mkPen(None), brush=pg.mkBrush(cor)
        )
        self.plot_widget.addItem(self.scatter_item)
        self.scatter_item.sigClicked.connect(self.on_scatter_clicked)

    def _ao_trocar_variavel(self, nova_variavel):
        """Ao mudar a variável alvo, atualiza o combo_metodo e reconstrói o gráfico."""
        if self._sincronizando or not nova_variavel:
            return
        self._sincronizando = True
        metodo_var = self.metodo_por_variavel.get(nova_variavel, "Linear")
        self.combo_metodo.setCurrentText(metodo_var)
        self._sincronizando = False

        self._montar_plot()
        self.atualizar_preview()

    def _ao_trocar_metodo(self, novo_metodo):
        """Ao mudar o método, armazena a escolha para a variável ativa e atualiza o gráfico."""
        if self._sincronizando or not novo_metodo:
            return
        col_atual = self.combo_alvo.currentText()
        self.metodo_por_variavel[col_atual] = novo_metodo
        self.atualizar_preview()

    def toggle_wywiwyg(self):
        if self.btn_wywiwyg.isChecked():
            self.btn_apagar.setChecked(False)
            self.btn_wywiwyg.setText("Adicionar (Ativado)")
            self.btn_apagar.setText("Apagar ponto")
            self.plot_widget.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.btn_wywiwyg.setText("Adicionar ponto (wywiwyg)")
            self.plot_widget.setCursor(Qt.CursorShape.ArrowCursor)

    def toggle_apagar(self):
        if self.btn_apagar.isChecked():
            self.btn_wywiwyg.setChecked(False)
            self.btn_apagar.setText("Apagar (Ativado)")
            self.btn_wywiwyg.setText("Adicionar ponto (wywiwyg)")
            self.plot_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.btn_apagar.setText("Apagar ponto")
            self.plot_widget.setCursor(Qt.CursorShape.ArrowCursor)

    def on_scatter_clicked(self, scatter_item, points, ev):
        if not self.btn_apagar.isChecked():
            return

        col_alvo = self.combo_alvo.currentText()

        if col_alvo:
            # Remove os pontos clicados usando a menor distância
            for p in points:
                x_val, y_val = p.pos().x(), p.pos().y()
                if not self.pontos_manuais[col_alvo]:
                    continue
                dist = np.array(
                    [
                        (pdict["x"] - x_val) ** 2 + (pdict["y"] - y_val) ** 2
                        for pdict in self.pontos_manuais[col_alvo]
                    ]
                )
                idx = np.argmin(dist)
                self.pontos_manuais[col_alvo].pop(idx)
            self.atualizar_preview()

    def on_mouse_clicked(self, event):
        if not self.btn_wywiwyg.isChecked():
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.plot_widget.plotItem.vb.mapSceneToView(event.scenePos())
            x_click, y_click = pos.x(), pos.y()

            alvo = self.combo_alvo.currentText()

            idx_closest = (np.abs(self.x_data - x_click)).argmin()
            x_nearest = self.x_data[idx_closest]

            self.pontos_manuais[alvo].append(
                {"idx": idx_closest, "x": x_nearest, "y": y_click}
            )
            self.atualizar_preview()

    def atualizar_preview(self, *args):
        col = self.combo_alvo.currentText()
        if not col:
            return

        metodo = self.metodo_por_variavel.get(col, "Linear")

        y_original = self.df[col].copy().astype("float64")

        # Injeta pontos manuais temporariamente para o cálculo
        for pt in self.pontos_manuais[col]:
            y_original.iloc[pt["idx"]] = pt["y"]

        # Dados originais (com gaps onde há NaN)
        # PyQtGraph lida com NaN cortando a linha ao usar connect='finite'
        self.plot_item_original.setData(
            self.x_data, y_original.values, connect="finite"
        )

        # Calcula interpolação
        try:
            if metodo == "Linear":
                y_interp, _ = interpolacao_linear(pd.Series(self.x_data), y_original)
            elif metodo == "Spline":
                y_interp, _ = interpolacao_spline(
                    pd.Series(self.x_data), y_original, order=3
                )
            elif metodo == "Média":
                y_interp, _ = interpolacao_media(pd.Series(self.x_data), y_original)
            else:
                y_interp = y_original
        except Exception:
            y_interp = y_original

        # Mostramos a linha interpolada apenas onde havia NaN e agora foi preenchido
        # Para mostrar só as partes interpoladas, criamos um array NaN onde o original NÃO era NaN.
        # Incluímos os pontos de borda originais para as linhas conectarem.

        mask_nan_original = y_original.isna()
        if mask_nan_original.any():
            # Expande a máscara para pegar os vizinhos válidos
            mask_plot_interp = mask_nan_original.copy()
            shifted_fwd = mask_plot_interp.shift(1).astype(bool).fillna(False)
            shifted_bwd = mask_plot_interp.shift(-1).astype(bool).fillna(False)
            mask_plot_interp = mask_plot_interp | shifted_fwd | shifted_bwd

            y_plot_interp = y_interp.copy()
            y_plot_interp[~mask_plot_interp] = np.nan
            self.plot_item_interpolado.setData(
                self.x_data, y_plot_interp.values, connect="finite"
            )
        else:
            self.plot_item_interpolado.setData(
                self.x_data, np.full_like(self.x_data, np.nan), connect="finite"
            )

        # Atualiza o ScatterPlot dos pontos manuais
        pontos = self.pontos_manuais[col]
        if pontos:
            x_pts = [p["x"] for p in pontos]
            y_pts = [p["y"] for p in pontos]
            self.scatter_item.setData(x_pts, y_pts)
        else:
            self.scatter_item.clear()
