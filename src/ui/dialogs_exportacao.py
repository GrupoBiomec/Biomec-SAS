from ui.utils import PadraoDialog
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
)
from PyQt6.QtCore import Qt


class JanelaExportarGraficos(PadraoDialog):
    """Janela para selecionar gráficos e formato de exportação."""

    def __init__(self, estado, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.setWindowTitle("Exportar Gráficos")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout(self)

        lbl_desc = QLabel("Selecione os gráficos que deseja exportar:")
        lbl_desc.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_desc)

        # Árvore para seleção
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)

        self._preencher_arvore()

        # Botões de Seleção Rápida
        layout_sel = QHBoxLayout()
        btn_sel_todos = QPushButton("Selecionar Todos")
        btn_sel_todos.clicked.connect(lambda: self._alterar_selecao(True))
        btn_desel_todos = QPushButton("Desmarcar Todos")
        btn_desel_todos.clicked.connect(lambda: self._alterar_selecao(False))
        layout_sel.addWidget(btn_sel_todos)
        layout_sel.addWidget(btn_desel_todos)
        layout.addLayout(layout_sel)

        # Formato de Exportação
        lbl_formato = QLabel("Formato de Exportação:")
        lbl_formato.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_formato)

        self.grupo_formato = QButtonGroup(self)
        self.radio_pdf = QRadioButton("PDF (Imagens dos gráficos)")
        self.radio_txt = QRadioButton(
            "TXT (Metadados e informações estatísticas dos gráficos"
        )
        self.radio_zip = QRadioButton("ZIP (Contém o PDF e o TXT)")

        self.radio_pdf.setChecked(True)

        self.grupo_formato.addButton(self.radio_pdf, 1)
        self.grupo_formato.addButton(self.radio_txt, 2)
        self.grupo_formato.addButton(self.radio_zip, 3)

        layout.addWidget(self.radio_pdf)
        layout.addWidget(self.radio_txt)
        layout.addWidget(self.radio_zip)

        # Botões de ação
        botoes_layout = QHBoxLayout()
        btn_exportar = QPushButton("Exportar")
        btn_exportar.clicked.connect(self._validar_e_aceitar)
        btn_exportar.setDefault(True)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_cancelar)
        botoes_layout.addWidget(btn_exportar)
        layout.addLayout(botoes_layout)

    def _preencher_arvore(self):
        # Adicionar arquivos e seus gráficos normais
        for nome_arquivo, dados in self.estado.guarda_arquivos.items():
            item_arquivo = QTreeWidgetItem(self.tree, [nome_arquivo])
            item_arquivo.setFlags(
                item_arquivo.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item_arquivo.setCheckState(0, Qt.CheckState.Unchecked)
            item_arquivo.setExpanded(True)

            graficos = self.estado.guarda_graficos.get(nome_arquivo, {})
            for nome_grafico, config in graficos.items():
                if not config.get("hidden", False):
                    item_grafico = QTreeWidgetItem(item_arquivo, [nome_grafico])
                    item_grafico.setFlags(
                        item_grafico.flags() | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    item_grafico.setCheckState(0, Qt.CheckState.Unchecked)
                    # Guardamos os dados no item para facilitar a identificação depois
                    item_grafico.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        {
                            "tipo_item": "normal",
                            "arquivo": nome_arquivo,
                            "grafico": nome_grafico,
                        },
                    )

        # Adicionar composições (sobreposições)
        if self.estado.guarda_sobreposicoes:
            item_sobreposicoes = QTreeWidgetItem(self.tree, ["Sobreposições"])
            item_sobreposicoes.setFlags(
                item_sobreposicoes.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item_sobreposicoes.setCheckState(0, Qt.CheckState.Unchecked)
            item_sobreposicoes.setExpanded(True)

            for nome_comp, config in self.estado.guarda_sobreposicoes.items():
                item_comp = QTreeWidgetItem(item_sobreposicoes, [nome_comp])
                item_comp.setFlags(item_comp.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item_comp.setCheckState(0, Qt.CheckState.Unchecked)
                item_comp.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"tipo_item": "sobreposicao", "grafico": nome_comp},
                )

        # Adicionar exibições simultâneas
        if self.estado.guarda_exibicoes_simultaneas:
            item_simultaneas = QTreeWidgetItem(self.tree, ["Exibições Simultâneas"])
            item_simultaneas.setFlags(
                item_simultaneas.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            item_simultaneas.setCheckState(0, Qt.CheckState.Unchecked)
            item_simultaneas.setExpanded(True)

            for nome_comp, config in self.estado.guarda_exibicoes_simultaneas.items():
                item_comp = QTreeWidgetItem(item_simultaneas, [nome_comp])
                item_comp.setFlags(item_comp.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item_comp.setCheckState(0, Qt.CheckState.Unchecked)
                item_comp.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"tipo_item": "simultanea", "grafico": nome_comp},
                )

        # Adiciona comportamento de auto-check (pai/filho) - opcional, mas vamos simplificar deixando independente ou implementando no itemClicked
        self.tree.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item, column):
        self.tree.blockSignals(True)
        # Se alterou um pai, propaga pros filhos
        for i in range(item.childCount()):
            item.child(i).setCheckState(0, item.checkState(0))

        # Se alterou um filho, verifica o pai
        parent = item.parent()
        if parent is not None:
            all_checked = True
            all_unchecked = True
            for i in range(parent.childCount()):
                state = parent.child(i).checkState(0)
                if state == Qt.CheckState.Checked:
                    all_unchecked = False
                elif state == Qt.CheckState.Unchecked:
                    all_checked = False

            if all_checked:
                parent.setCheckState(0, Qt.CheckState.Checked)
            elif all_unchecked:
                parent.setCheckState(0, Qt.CheckState.Unchecked)
            else:
                parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        self.tree.blockSignals(False)

    def _alterar_selecao(self, check: bool):
        state = Qt.CheckState.Checked if check else Qt.CheckState.Unchecked
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, state)
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, state)
        self.tree.blockSignals(False)

    def _validar_e_aceitar(self):
        selecionados = self.get_selecionados()
        if not selecionados:
            QMessageBox.warning(
                self, "Aviso", "Selecione pelo menos um gráfico para exportar."
            )
            return

        # Se escolheu TXT e só selecionou composições, avisa que o TXT não terá nada
        formato = self.get_formato()
        if formato in ["TXT", "ZIP"]:
            tem_normal = any(s["tipo_item"] == "normal" for s in selecionados)
            if not tem_normal:
                if formato == "TXT":
                    QMessageBox.warning(
                        self,
                        "Aviso",
                        "A exportação TXT só inclui gráficos normais. Você selecionou apenas composições, portanto o arquivo ficaria vazio.",
                    )
                    return
                # Se for ZIP ele ainda exporta as composições no PDF, o TXT fica vazio/sem elas.

        self.accept()

    def get_selecionados(self):
        selecionados = []
        # Itera por todos os itens
        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    data = child.data(0, Qt.ItemDataRole.UserRole)
                    if data:
                        selecionados.append(data)
        return selecionados

    def get_formato(self):
        if self.radio_pdf.isChecked():
            return "PDF"
        elif self.radio_txt.isChecked():
            return "TXT"
        return "ZIP"
