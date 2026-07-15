from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QTreeWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QInputDialog,
    QFileDialog,
    QDialog,
    QComboBox,
    QPushButton,
    QMessageBox,
    QCheckBox,
)
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt
from ui.utils import resource_path
import sys
from ui.exibe_graficos import ExibidorGraficos
import time
import pyqtgraph as pg
import numpy as np
from arquivos.parsers.open_emt import *
from arquivos.parsers.open_tdf import *
from processamento.gera_graficos import *
from processamento.operacoes import *
from processamento.limpeza import *
from ui.dialogs_operacoes import (
    JanelaManipularVariaveis,
    JanelaTrigonometria,
    JanelaCalculoEscalar,
    JanelaDefinirAngulos,
)
from ui.dialogs_processamento import (
    JanelaPreencherLacunas,
    JanelaSelecionarGraficosInterpolados,
    JanelaMultiplasCurvas,
)
from controller.gerenciador_estado import GerenciadorEstado
from ui.arvore import GerenciadorArvore
from ui.dialogs_processamento import JanelaSelecionarGraficoFiltro
from ui.dialogs_exportacao import JanelaExportarGraficos
import os


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Layout da tela

        self.setWindowTitle("Biomec SAS")
        self.setWindowIcon(QIcon(resource_path(os.path.join("assets", "logo.ico"))))

        self.resize(1000, 600)

        self.estado = GerenciadorEstado()
        self.arvore = None
        self.zoom_ativo = False
        self.grafico_sendo_exibido = False

        self.area_grafico = pg.PlotWidget()
        self.area_grafico.setMenuEnabled(False)

        self.gerador_graficos = GeradorGraficos(self.area_grafico)
        self.leitorEMT = TratamentoEMT()
        self.leitorTDF = TratamentoTDF()
        self.exibidor_graficos = ExibidorGraficos(self)

        # menu superior:

        menu_principal = self.menuBar()
        menu_arquivo = menu_principal.addMenu("Arquivo")
        menu_processamento = menu_principal.addMenu("Processamento")
        menu_analise = menu_principal.addMenu("Análise")
        menu_operacoes = menu_principal.addMenu("Operações")
        menu_scripts = menu_principal.addMenu("Scripts")
        menu_exportar = menu_principal.addMenu("Exportar")
        menu_ajuda = menu_principal.addMenu("Ajuda")

        # Arquivo
        acao_abrir_projeto = QAction("Abrir Projeto (.sas)", self)
        acao_abrir_projeto.triggered.connect(self._abrir_projeto_sas)
        menu_arquivo.addAction(acao_abrir_projeto)
        menu_arquivo.addSeparator()
        submenu_abrir = QMenu("Abrir Arquivo", self)
        menu_arquivo.addMenu(submenu_abrir)
        abrir_emt = QAction("Arquivo EMT", self)
        abrir_emt.triggered.connect(self.carregar_emt)
        submenu_abrir.addAction(abrir_emt)
        abrir_tdf = QAction("Arquivo TDF", self)
        abrir_tdf.triggered.connect(self.carregar_tdf)
        submenu_abrir.addAction(abrir_tdf)

        # Processamento
        submenu_filtragem = QMenu("Filtrar sinal", self)
        menu_processamento.addMenu(submenu_filtragem)
        acao_passa_baixa = QAction("Passa-Baixa", self)
        acao_passa_baixa.triggered.connect(lambda: self._aplicar_filtro("passa_baixa"))
        submenu_filtragem.addAction(acao_passa_baixa)
        acao_passa_alta = QAction("Passa-Alta", self)
        acao_passa_alta.triggered.connect(lambda: self._aplicar_filtro("passa_alta"))
        submenu_filtragem.addAction(acao_passa_alta)
        submenu_preencher = QAction("Métodos de Interpolação", self)
        menu_processamento.addAction(submenu_preencher)
        submenu_preencher.triggered.connect(self.abrir_preencher_lacunas)
        acao_offset = QAction("Definir Offset", self)
        acao_offset.triggered.connect(self._abrir_janela_offset)
        menu_processamento.addAction(acao_offset)
        acao_trim = QAction("Recorte Temporal", self)
        acao_trim.triggered.connect(self._abrir_janela_trim)
        menu_processamento.addAction(acao_trim)

        # Análise
        acao_sobrepor = QAction("Sobrepor Gráficos", self)
        menu_analise.addAction(acao_sobrepor)
        acao_sobrepor.setShortcut("Ctrl+S")
        acao_sobrepor.triggered.connect(
            self.exibidor_graficos._abrir_janela_sobreposicao
        )
        acao_exibicao_simultanea = QAction("Exibição simultânea", self)
        menu_analise.addAction(acao_exibicao_simultanea)
        acao_exibicao_simultanea.triggered.connect(
            self.exibidor_graficos._abrir_janela_exibicao_simultanea
        )

        # Operações
        acao_aritmetica = QAction("Aritmética Básica", self)
        acao_aritmetica.triggered.connect(self._abrir_aritmetica_basica)
        menu_operacoes.addAction(acao_aritmetica)
        acao_trigonometria = QAction("Trigonometria", self)
        acao_trigonometria.triggered.connect(self._abrir_trigonometria)
        menu_operacoes.addAction(acao_trigonometria)
        acao_calculo_escalar = QAction("Cálculo e Funções Escalares", self)
        acao_calculo_escalar.triggered.connect(self._abrir_calculo_escalar)
        menu_operacoes.addAction(acao_calculo_escalar)
        menu_operacoes.addSeparator()
        acao_definir_angulos = QAction("Definir Ângulos", self)
        acao_definir_angulos.triggered.connect(self._abrir_definir_angulos)
        menu_operacoes.addAction(acao_definir_angulos)
        menu_operacoes.addSeparator()
        acao_desfazer_operacao = QAction(
            "Desfazer Última Operação (Remover Variável)", self
        )
        acao_desfazer_operacao.triggered.connect(self.desfazer_ultima_operacao)
        menu_operacoes.addAction(acao_desfazer_operacao)

        # Scripts
        acao_scripts_salvos = QAction("Scripts Salvos", self)
        acao_scripts_salvos.triggered.connect(self._abrir_scripts_salvos)
        menu_scripts.addAction(acao_scripts_salvos)
        acao_novo_script = QAction("Criar Novo Script de Arquivo", self)
        acao_novo_script.triggered.connect(self._abrir_criar_script)
        menu_scripts.addAction(acao_novo_script)
        acao_novo_script_graf = QAction("Criar Novo Script de Gráfico", self)
        acao_novo_script_graf.triggered.connect(self._abrir_criar_script_grafico)
        menu_scripts.addAction(acao_novo_script_graf)

        # Exportar
        acao_salvar_projeto = QAction("Salvar Projeto", self)
        acao_salvar_projeto.triggered.connect(self._salvar_projeto_sas)
        menu_exportar.addAction(acao_salvar_projeto)
        acao_exportar_pipeline = QAction("Exportar Histórico de Processamento", self)
        acao_exportar_pipeline.triggered.connect(self.exportar_pipeline)
        menu_exportar.addAction(acao_exportar_pipeline)
        acao_exportar_graficos = QAction("Exportar Gráficos", self)
        acao_exportar_graficos.triggered.connect(self._abrir_janela_exportacao)
        menu_exportar.addAction(acao_exportar_graficos)

        # Ajuda
        acao_sobre = QAction("Sobre", self)
        acao_sobre.triggered.connect(self._mostrar_sobre)
        menu_ajuda.addAction(acao_sobre)

        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        self.h_layout = QHBoxLayout(widget_central)
        painel_esquerdo = QWidget()
        painel_esquerdo.setFixedWidth(int(self.width() * 0.2))
        layout_esquerdo = QVBoxLayout(painel_esquerdo)
        layout_esquerdo.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()

        self.tree.setHeaderLabel("Arquivos carregados")
        layout_esquerdo.addWidget(self.tree, stretch=2)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu_contexto)
        self.tree.currentItemChanged.connect(self._detectar_selecao)
        self.tree_composicoes = QTreeWidget()

        self.tree_composicoes.setHeaderLabel("Composições de Visualização")
        layout_esquerdo.addWidget(self.tree_composicoes, stretch=1)
        self.tree_composicoes.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.tree_composicoes.customContextMenuRequested.connect(
            self._menu_contexto_composicao
        )
        self.tree_composicoes.currentItemChanged.connect(
            self._detectar_selecao_composicao
        )

        self.arvore = GerenciadorArvore(self, self.tree, self.tree_composicoes)
        self.h_layout.addWidget(painel_esquerdo)
        self.container_grafico = QWidget()
        layout_grafico = QVBoxLayout(self.container_grafico)
        layout_grafico.setContentsMargins(0, 0, 0, 0)
        painel_topo = QWidget()
        layout_topo = QHBoxLayout(painel_topo)
        layout_topo.setContentsMargins(0, 5, 0, 5)

        self.check_comparar = QCheckBox(
            "Comparar Variável Y com Original (antes da Interpolação)"
        )
        self.check_comparar.hide()
        self.check_comparar.stateChanged.connect(
            lambda: self.exibidor_graficos._exibir_grafico_selecionado()
        )
        layout_topo.addWidget(self.check_comparar)
        layout_topo.addStretch()

        self.btn_desativar_zoom = QPushButton("Desativar Zoom")
        self.btn_desativar_zoom.hide()
        self.btn_desativar_zoom.clicked.connect(
            lambda: self.exibidor_graficos._toggle_zoom(False)
        )
        layout_topo.addWidget(self.btn_desativar_zoom)
        layout_grafico.addWidget(painel_topo)
        self.area_grafico.setBackground("w")
        self.area_grafico.showGrid(x=True, y=True)
        layout_grafico.addWidget(self.area_grafico)
        self.area_simultanea = pg.GraphicsLayoutWidget()
        self.area_simultanea.setBackground("w")
        self.area_simultanea.hide()
        layout_grafico.addWidget(self.area_simultanea)
        self.h_layout.addWidget(self.container_grafico)
        self.container_grafico.setMinimumWidth(int(self.width() * 0.8))

        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        self.placeholder_label = QLabel("Nenhum arquivo aberto")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.placeholder_label)
        self.h_layout.addWidget(self.placeholder_widget)
        self.container_grafico.hide()
        self.placeholder_widget.show()

    def carregar_emt(self):
        caminhos_arquivos, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir Arquivo(s) EMT",
            "",
            "Arquivos EMT (*.emt);;Todos os arquivos (*)",
        )
        if caminhos_arquivos:
            sucessos = []
            erros = []
            for caminho in caminhos_arquivos:
                try:
                    nome_arquivo = self.estado.processar_carregamento_emt(caminho)
                    self.arvore.add_arvore(nome_arquivo)
                    sucessos.append(nome_arquivo)
                except ValueError as e:
                    import os

                    nome_base = os.path.basename(caminho)
                    erros.append(f"{nome_base}: {str(e)}")
                except Exception as e:
                    import os

                    nome_base = os.path.basename(caminho)
                    erros.append(f"{nome_base}: Erro inesperado - {e}")

            if sucessos:
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"{len(sucessos)} arquivo(s) carregado(s) com sucesso!",
                )
            if erros:
                msg_erro = "\n".join(erros)
                QMessageBox.warning(
                    self,
                    "Avisos/Erros",
                    f"Os seguintes problemas ocorreram:\n\n{msg_erro}",
                )

    def _salvar_projeto_sas(self):
        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self, "Salvar Projeto", "", "Projeto SAS (*.sas)"
        )
        if caminho_arquivo:
            try:
                self.estado.salvar_projeto(caminho_arquivo)
                QMessageBox.information(self, "Sucesso", "Projeto salvo com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar projeto:\n{e}")

    def _abrir_projeto_sas(self):
        caminho_arquivo, _ = QFileDialog.getOpenFileName(
            self, "Abrir Projeto", "", "Projeto SAS (*.sas)"
        )
        if caminho_arquivo:
            try:
                nomes_carregados = self.estado.abrir_projeto(caminho_arquivo)
                for nome in nomes_carregados:
                    self.arvore.add_arvore(nome)

                    if nome in self.estado.get_graficos():
                        for nome_grafico in self.estado.get_graficos()[nome]:
                            config = self.estado.get_config_grafico(nome, nome_grafico)
                            if not config.get("hidden", False):
                                self.arvore._adicionar_grafico_na_arvore_de_arquivo(
                                    nome, nome_grafico
                                )

                self.arvore._atualizar_arvore_composicoes()
                self._resetar_interface()
                QMessageBox.information(
                    self, "Sucesso", "Projeto carregado com sucesso!"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao abrir projeto:\n{e}")

    def carregar_tdf(self):
        caminhos_arquivos, _ = QFileDialog.getOpenFileNames(
            self,
            "Abrir Arquivo(s) TDF",
            "",
            "Arquivos TDF (*.tdf);;Todos os arquivos (*)",
        )
        if caminhos_arquivos:
            sucessos = []
            erros = []
            for caminho in caminhos_arquivos:
                try:
                    nome_arquivo = self.estado.processar_carregamento_tdf(caminho)
                    self.arvore.add_arvore(nome_arquivo)
                    sucessos.append(nome_arquivo)
                except ValueError as e:
                    import os

                    nome_base = os.path.basename(caminho)
                    erros.append(f"{nome_base}: {str(e)}")
                except Exception as e:
                    import os

                    nome_base = os.path.basename(caminho)
                    erros.append(f"{nome_base}: Erro inesperado - {e}")

            if sucessos:
                self._resetar_interface()
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"{len(sucessos)} arquivo(s) carregado(s) com sucesso!",
                )
            if erros:
                msg_erro = "\n".join(erros)
                QMessageBox.warning(
                    self,
                    "Avisos/Erros",
                    f"Os seguintes problemas ocorreram:\n\n{msg_erro}",
                )

    def _detectar_selecao(self, item_atual):
        self.exibidor_graficos._desativar_zoom()
        self.tree_composicoes.setCurrentItem(None)
        self.tree_composicoes.clearSelection()

        if item_atual is None:
            self._limpar_selecao()
            return

        if item_atual.parent() is None:
            self.estado.arquivo_ativo = item_atual.text(0)
            self.estado.grafico_ativo = None
            self._resetar_interface()
            return

        nome_grafico = item_atual.text(0)
        item_nivel_0 = item_atual

        while item_nivel_0.parent() is not None:
            item_nivel_0 = item_nivel_0.parent()

        nome_arquivo_pai = item_nivel_0.text(0)
        self.estado.grafico_ativo = nome_grafico
        self.estado.arquivo_ativo = nome_arquivo_pai
        self.exibidor_graficos._exibir_grafico_selecionado()

    def _detectar_selecao_composicao(self, item_atual):
        self.exibidor_graficos._desativar_zoom()
        self.tree.setCurrentItem(None)
        self.tree.clearSelection()

        if item_atual is None:
            self._limpar_selecao()
            return

        nome_composicao = item_atual.text(0)
        self.estado.arquivo_ativo = None
        self.estado.grafico_ativo = nome_composicao
        self.exibidor_graficos._exibir_grafico_selecionado()

    def _limpar_selecao(self):
        self.exibidor_graficos._desativar_zoom()
        self.estado.arquivo_ativo = None
        self.estado.grafico_ativo = None
        self.zoom_ativo = False
        self.zoom_ativo = False
        self.gerador_graficos.limpar()
        self.area_simultanea.clear()
        self._resetar_interface()

    def _abrir_multiplas_curvas(self, nome_arquivo):
        if nome_arquivo not in self.estado.get_arquivos():
            return

        dados_arquivo = self.estado.get_arquivos()[nome_arquivo]
        df = dados_arquivo["dataframe"]
        unidades_colunas = dados_arquivo.get("unidades_colunas", {})
        janela = JanelaMultiplasCurvas(list(df.columns), unidades_colunas, self)

        if janela.exec() == QDialog.DialogCode.Accepted:
            selecao = janela.get_selecoes()
            var_x = selecao["eixo_x"]
            vars_y = selecao["eixo_y_lista"]
            nome_composicao = selecao["nome"]

            if not vars_y:
                QMessageBox.warning(
                    self, "Aviso", "Nenhuma variável selecionada para plotar."
                )
                return

            graficos_gerados = []

            if nome_arquivo not in self.estado.get_graficos():
                pass  # Already handled by adicionar_config_grafico
            for y in vars_y:
                nome_graf = y
                contador = 1
                while nome_graf in self.estado.get_graficos(nome_arquivo):
                    nome_graf = f"{y}_{contador}"
                    contador += 1

                config = {
                    "tipo": "Linha",
                    "eixo_x": var_x,
                    "eixo_y": y,
                    "cor": "b",
                    "unidade_x": unidades_colunas.get(var_x, ""),
                    "unidade_y": unidades_colunas.get(y, ""),
                    "filtros_aplicados": [],
                    "linhas_referencia": [],
                    "hidden": True,
                }
                self.estado.adicionar_config_grafico(nome_arquivo, nome_graf, config)
                graficos_gerados.append(
                    {"arquivo": nome_arquivo, "grafico": nome_graf, "nome_legenda": y}
                )

            nome_final_composicao = nome_composicao
            i = 1

            while (
                nome_final_composicao in self.estado.get_sobreposicoes()
                or nome_final_composicao in self.estado.get_exibicoes_simultaneas()
            ):
                nome_final_composicao = f"{nome_composicao}_{i}"
                i += 1

            self.estado.get_sobreposicoes()[nome_final_composicao] = {
                "graficos_fonte": graficos_gerados,
                "tipo_composicao": "multiplas_curvas",
                "titulo": nome_final_composicao,
            }
            self.arvore._atualizar_arvore_composicoes()
            self.estado.arquivo_ativo = None
            self.estado.grafico_ativo = nome_final_composicao
            self.arvore._selecionar_item_composicao(nome_final_composicao)
            self.exibidor_graficos._exibir_grafico_selecionado()

    def _menu_contexto(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        if item.parent() is None:
            self._menu_arquivo(item, pos)
            return
        if item.parent() is not None:
            self.exibidor_graficos._menu_grafico(item, pos)
            return

    def _menu_contexto_composicao(self, pos):
        item = self.tree_composicoes.itemAt(pos)

        if item is None:
            return

        menu = QMenu(self)
        try:
            tipo = item.data(0, Qt.ItemDataRole.UserRole)
        except AttributeError:
            tipo = item.data(0, Qt.UserRole)

        if tipo == "Sobreposicao" or tipo == "sobreposicao":
            acao_editar = QAction("Editar", self)
            acao_editar.triggered.connect(
                lambda: self.exibidor_graficos._abrir_janela_ajustes(item)
            )
            menu.addAction(acao_editar)
            nome_composicao = item.text(0)
            config = self.estado.get_sobreposicoes().get(nome_composicao, {})
            tem_ocultos = False

            for ref in config.get("graficos_fonte", []):
                arq = ref.get("arquivo")
                graf = ref.get("grafico")

                if (
                    self.estado.get_graficos()
                    .get(arq, {})
                    .get(graf, {})
                    .get("hidden", False)
                ):
                    tem_ocultos = True
                    break
            if tem_ocultos:
                menu.addSeparator()
                acao_plotar_sep = QAction("Plotar separadamente", self)
                acao_plotar_sep.triggered.connect(
                    lambda: self.exibidor_graficos._plotar_separadamente(
                        nome_composicao
                    )
                )
                menu.addAction(acao_plotar_sep)

            menu.addAction(acao_editar)

        elif tipo == "simultanea":
            acao_editar = QAction("Editar", self)
            acao_editar.triggered.connect(
                lambda: self.exibidor_graficos._abrir_editar_exibicao_simultanea(item)
            )
            menu.addAction(acao_editar)

        delete_action = QAction("Excluir composição", self)
        delete_action.triggered.connect(
            lambda: self._remover_composicao(item.text(0), tipo)
        )
        menu.addAction(delete_action)

        if tipo != "simultanea":
            menu.addSeparator()
            acao_zoom = QAction("Ativar Zoom", self)
            acao_zoom.setCheckable(True)
            acao_zoom.setChecked(self.zoom_ativo)
            acao_zoom.triggered.connect(self.exibidor_graficos._toggle_zoom)
            menu.addAction(acao_zoom)
        menu.exec(self.tree_composicoes.mapToGlobal(pos))

    def _get_arquivo_nome(self, item):
        """Sobe na hierarquia da árvore até encontrar o item raiz (arquivo) e retorna seu nome."""
        atual = item
        while atual.parent() is not None:
            atual = atual.parent()
        return atual.text(0)

    def _menu_arquivo(self, item, pos):
        self.estado.arquivo_ativo = item.text(0)
        self.tree.setCurrentItem(item)
        self.estado.grafico_ativo = None

        menu = QMenu(self)
        renomear_action = QAction("Renomear", self)
        renomear_action.triggered.connect(lambda: self._renomear_item(item))

        grafico_action = QAction("Adicionar novo gráfico", self)
        grafico_action.triggered.connect(lambda: self.exibidor_graficos.criar_grafico())

        multiplas_curvas_action = QAction("Visualizar múltiplas curvas", self)
        multiplas_curvas_action.triggered.connect(
            lambda: self._abrir_multiplas_curvas(item.text(0))
        )

        menu.addAction(renomear_action)
        menu.addAction(grafico_action)
        menu.addAction(multiplas_curvas_action)
        menu.addSeparator()

        if self.estado.guarda_scripts:
            menu_scripts = menu.addMenu("Aplicar Script")
            for nome_script in self.estado.guarda_scripts.keys():
                acao_script = QAction(nome_script, self)
                acao_script.triggered.connect(
                    lambda checked, s=nome_script, arq=item.text(
                        0
                    ): self._aplicar_script_em_arquivo(s, arq)
                )
                menu_scripts.addAction(acao_script)
            menu.addSeparator()

        remover_action = QAction("Remover Arquivo", self)
        remover_action.triggered.connect(lambda: self._remover_arquivo(item.text(0)))
        menu.addAction(remover_action)
        menu.exec(self.tree.mapToGlobal(pos))

    def _remover_composicao(self, nome_composicao, tipo):
        resposta = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir a composição '{nome_composicao}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            try:
                self.estado._remover_composicao(nome_composicao, tipo)
                self.arvore._atualizar_arvore_composicoes()
                if self.estado.grafico_ativo == nome_composicao:
                    self._limpar_selecao()
                self.exibidor_graficos._exibir_grafico_selecionado()
            except ValueError as e:
                QMessageBox.warning(self, "Aviso", str(e))

    def _remover_arquivo(self, nome_arquivo):
        resposta = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o arquivo '{nome_arquivo}' e todos os seus gráficos e composições vinculadas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            try:
                comp_removidas = self.estado._remover_arquivo(nome_arquivo)
                self.arvore._remover_item_arvore(nome_arquivo)

                # Remove também as composições da árvore
                self.arvore._atualizar_arvore_composicoes()

                graficos_ativos = [c[1] for c in comp_removidas]
                if (
                    self.estado.arquivo_ativo == nome_arquivo
                    or self.estado.grafico_ativo in graficos_ativos
                ):
                    self._limpar_selecao()
                    self.exibidor_graficos._exibir_grafico_selecionado()
            except ValueError as e:
                QMessageBox.warning(self, "Aviso", str(e))

    def _renomear_item(self, item):
        nome_antigo = item.text(0)

        dialogo = QInputDialog(self)
        dialogo.setWindowTitle("")
        dialogo.setLabelText("Digite o novo nome:")
        dialogo.setTextValue(nome_antigo)
        dialogo.setWindowFlags(
            dialogo.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        pos_item = self.tree.viewport().mapToGlobal(
            self.tree.visualItemRect(item).topLeft()
        )
        dialogo.move(pos_item + QPoint(20, 0))

        if dialogo.exec():
            novo_nome = dialogo.textValue().strip()
            if not novo_nome or novo_nome == nome_antigo:
                return

            nome_arquivo = (
                None if item.parent() is None else self._get_arquivo_nome(item)
            )

            try:
                sucesso = self.estado._executar_renomeacao(
                    nome_antigo, novo_nome, nome_arquivo
                )
                if sucesso:
                    item.setText(0, novo_nome)
            except ValueError as e:
                QMessageBox.warning(self, "Aviso", str(e))

    def _resetar_interface(self):
        self.grafico_sendo_exibido = False
        self.container_grafico.hide()
        self.placeholder_label.setText("Nenhum gráfico selecionado")
        self.placeholder_widget.show()

    def criar_grafico(self):
        if not self.estado.arquivo_ativo:
            return

        df = self.estado.get_dataframe(self.estado.arquivo_ativo)
        cabecalho = self.estado.get_cabecalho(self.estado.arquivo_ativo)
        unidades_colunas = self.estado.get_unidades_colunas(self.estado.arquivo_ativo)
        janela = JanelaConfig(
            df,
            self,
            unidade_y_default=cabecalho.get("measure_unit", ""),
            unidades_colunas=unidades_colunas,
        )

        if janela.exec() == QDialog.DialogCode.Accepted:
            config = janela.get_configuracoes()
            unidade_y = config.get("unidade_y", "")
            unidade_x = config.get("unidade_x", "")
            nome_grafico = (
                config["titulo"]
                or f"Gráfico {len(self.estado.get_graficos().get(self.estado.arquivo_ativo, {})) + 1}"
            )
            dados_grafico = {
                "tipo": config["tipo"],
                "titulo": nome_grafico,
                "eixo_x": config["eixo_x"],
                "eixo_y": config["eixo_y"],
                "unidade_x": unidade_x,
                "unidade_y": unidade_y,
            }

            if self.estado.get_pipeline_colunas(self.estado.arquivo_ativo):
                historico_col = self.estado.get_pipeline_colunas(
                    self.estado.arquivo_ativo
                ).get(config["eixo_y"])
                if historico_col:
                    import copy

                    dados_grafico["pipeline_grafico"] = copy.deepcopy(historico_col)

            if self.estado.nome_existe(self.estado.arquivo_ativo, nome_grafico):
                QMessageBox.warning(
                    self,
                    "Nome Duplicado",
                    f"Já existe um gráfico chamado '{nome_grafico}' neste arquivo.\nPor favor, escolha outro nome.",
                )
                return

            if self.estado.arquivo_ativo not in self.estado.get_graficos():
                pass  # Already handled by adicionar_config_grafico
            self.estado.adicionar_config_grafico(
                self.estado.arquivo_ativo, nome_grafico, dados_grafico
            )
            self._adicionar_grafico_na_arvore(nome_grafico)
            self.estado.grafico_ativo = nome_grafico
            self.arvore._selecionar_item_na_arvore(
                self.estado.arquivo_ativo, nome_grafico
            )
            self.exibidor_graficos._exibir_grafico_selecionado()

    def _abrir_janela_offset(self):
        if not self.estado.get_arquivos():
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        from ui.dialogs_processamento import JanelaSelecionarVariaveisOffset

        dlg_sel = JanelaSelecionarVariaveisOffset(
            self.estado, self.estado.arquivo_ativo, self
        )

        if dlg_sel.exec() != QDialog.DialogCode.Accepted:
            return

        nome_arquivo, colunas_selecionadas = dlg_sel.get_selecao()
        df = self.estado.get_dataframe(nome_arquivo)
        colunas = list(df.columns)

        col_tempo = next((c for c in colunas if c.lower() in ["time", "tempo"]), None)

        if not col_tempo:
            col_tempo = next(
                (c for c in colunas if c.lower() in ["frame", "frames", "item"]), None
            )

        from processamento.gera_graficos import JanelaOffset

        dlg_offset = JanelaOffset(df, colunas_selecionadas, col_tempo, self)

        if dlg_offset.exec() != QDialog.DialogCode.Accepted:
            return

        resultados = dlg_offset.get_resultados()
        offset_val = resultados["offset"]
        sobrescrever = resultados["sobrescrever"]
        unidades = self.estado.get_unidades_colunas(nome_arquivo)
        criar_graficos = resultados.get("criar_graficos", False)

        # O estado cuidará da inicialização
        if not self.estado.get_pipeline_colunas(nome_arquivo):
            pass
        for col in colunas_selecionadas:
            if sobrescrever:
                df[col] = df[col] - offset_val

                # Grava no pipeline do arquivo
                historico_col = self.estado.get_pipeline_colunas(nome_arquivo).get(
                    col, []
                )
                historico_col.append(
                    {
                        "tipo_operacao": "offset",
                        "valor": offset_val,
                        "base": "tempo",
                        "nova_var": False,
                        "nome_nova_var": "",
                    }
                )
                self.estado.atualizar_pipeline_colunas(nome_arquivo, col, historico_col)

                if nome_arquivo in self.estado.get_graficos():
                    for g_nome, g_conf in self.estado.get_graficos()[
                        nome_arquivo
                    ].items():
                        if g_conf.get("eixo_y") == col:
                            historico = g_conf.get("pipeline_grafico", [])
                            historico.append(
                                {
                                    "tipo_operacao": "offset",
                                    "valor": offset_val,
                                    "base": "tempo",
                                    "nova_var": False,
                                    "nome_nova_var": "",
                                }
                            )
                            g_conf["pipeline_grafico"] = historico
            else:
                nova_col = f"{col}_offset"
                contador = 1
                while nova_col in df.columns:
                    nova_col = f"{col}_offset_{contador}"
                    contador += 1
                df[nova_col] = df[col] - offset_val
                unidades[nova_col] = unidades.get(col, "")

                # Grava no pipeline do arquivo
                historico_col = (
                    self.estado.get_pipeline_colunas(nome_arquivo).get(col, []).copy()
                )
                historico_col.append(
                    {
                        "tipo_operacao": "offset",
                        "valor": offset_val,
                        "base": "tempo",
                        "nova_var": True,
                        "nome_nova_var": nova_col,
                    }
                )
                self.estado.atualizar_pipeline_colunas(
                    nome_arquivo, nova_col, historico_col
                )

                if criar_graficos:
                    if nome_arquivo not in self.estado.get_graficos():
                        pass  # Already handled by adicionar_config_grafico

                    graf_orig = None
                    for g_nome, g_conf in self.estado.get_graficos()[
                        nome_arquivo
                    ].items():
                        if g_conf.get("eixo_y") == col:
                            graf_orig = g_conf
                            break

                    config = {
                        "tipo": "Linha",
                        "eixo_x": col_tempo if col_tempo else df.columns[0],
                        "eixo_y": nova_col,
                        "cor": "b",
                        "unidade_x": unidades.get(col_tempo, ""),
                        "unidade_y": unidades.get(nova_col, ""),
                        "hidden": False,
                    }
                    historico = (
                        graf_orig.get("pipeline_grafico", []).copy()
                        if graf_orig
                        else []
                    )
                    historico.append(
                        {
                            "tipo_operacao": "offset",
                            "valor": offset_val,
                            "base": "tempo",
                            "nova_var": not sobrescrever,
                            "nome_nova_var": nova_col if not sobrescrever else "",
                        }
                    )
                    config["pipeline_grafico"] = historico

                    self.estado.adicionar_config_grafico(nome_arquivo, nova_col, config)
                    self.arvore._adicionar_grafico_na_arvore_de_arquivo(
                        nome_arquivo, nova_col
                    )

        QMessageBox.information(self, "Sucesso", "Offset aplicado com sucesso!")
        if self.estado.arquivo_ativo == nome_arquivo:
            self.exibidor_graficos._exibir_grafico_selecionado()

    def _abrir_janela_trim(self):
        if not self.estado.get_arquivos():
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        from ui.dialogs_processamento import JanelaSelecionarCategoriasTrim

        dlg_sel = JanelaSelecionarCategoriasTrim(
            self.estado, self.estado.arquivo_ativo, self
        )
        from PyQt6.QtWidgets import QDialog

        if dlg_sel.exec() != QDialog.DialogCode.Accepted:
            return

        nome_arquivo, categorias_selecionadas = dlg_sel.get_selecao()
        dados_arquivo = self.estado.get_arquivos()[nome_arquivo]
        df = dados_arquivo["dataframe"]
        unidades = dados_arquivo.get("unidades_colunas", {})
        categorias_map = {
            "Posição/Distância": ["m", "cm", "mm"],
            "Força": ["n", "N"],
            "Torque": ["nm", "n.m", "N.m", "Nm"],
            "EMG": ["v", "mv", "uv", "V", "mV", "uV"],
            "Ângulo": ["graus", "deg", "rad", "º", "radianos"],
            "Velocidade": ["m/s", "cm/s", "mm/s", "rad/s", "deg/s"],
        }
        colunas_por_cat = {cat: [] for cat in categorias_selecionadas}
        col_tempo = None

        for col in df.columns:
            if col.lower() in ["time", "tempo", "frame", "frames", "item"]:
                if not col_tempo:
                    col_tempo = col
                continue
            unit = unidades.get(col, "").strip()
            encontrou = False

            for cat in categorias_selecionadas:
                if cat == "Outros":
                    continue
                un_list = categorias_map.get(cat, [])
                if unit in un_list or unit.lower() in [u.lower() for u in un_list]:
                    colunas_por_cat[cat].append(col)
                    encontrou = True
                    break
            if not encontrou and "Outros" in categorias_selecionadas:
                colunas_por_cat["Outros"].append(col)

        from processamento.gera_graficos import JanelaRecorteTemporal

        dlg_trim = JanelaRecorteTemporal(
            df, categorias_selecionadas, colunas_por_cat, col_tempo, self
        )

        if dlg_trim.exec() != QDialog.DialogCode.Accepted:
            return

        resultados = dlg_trim.get_resultados()
        t_ini = resultados["t_ini"]
        t_fim = resultados["t_fim"]
        tipo_x = resultados["tipo_x"]
        deslocar_0 = resultados["deslocar_0"]
        sobrescrever = resultados["sobrescrever"]

        import numpy as np

        indices_mantidos = None

        if tipo_x == "Tempo" and col_tempo:
            mask = (df[col_tempo] >= t_ini) & (df[col_tempo] <= t_fim)
            df_cortado = df[mask].copy()
            indices_mantidos = df.index[mask]
            df_cortado.reset_index(drop=True, inplace=True)

            if deslocar_0:
                for c in df_cortado.columns:
                    if c.lower() in ["time", "tempo", "frame", "frames", "item"]:
                        df_cortado[c] = df_cortado[c] - df_cortado[c].iloc[0]
        else:
            idx_ini = max(0, int(t_ini))
            idx_fim = min(len(df) - 1, int(t_fim))
            df_cortado = df.iloc[idx_ini : idx_fim + 1].copy()
            indices_mantidos = df.index[idx_ini : idx_fim + 1]
            df_cortado.reset_index(drop=True, inplace=True)

            if deslocar_0 and len(df_cortado) > 0:
                for c in df_cortado.columns:
                    if c.lower() in ["time", "tempo", "frame", "frames", "item"]:
                        df_cortado[c] = df_cortado[c] - df_cortado[c].iloc[0]

        df_orig_cortado = None
        df_orig = self.estado.get_dataframe_original(nome_arquivo)

        if df_orig is not None:
            if len(df_orig) == len(df):
                if tipo_x == "Tempo" and col_tempo:
                    df_orig_cortado = df_orig[mask].copy()
                    df_orig_cortado.reset_index(drop=True, inplace=True)
                else:
                    df_orig_cortado = df_orig.iloc[idx_ini : idx_fim + 1].copy()
                    df_orig_cortado.reset_index(drop=True, inplace=True)

        from PyQt6.QtWidgets import QMessageBox

        if sobrescrever:
            self.estado.set_dataframe(nome_arquivo, df_cortado)
            if df_orig is not None:
                self.estado.set_dataframe_original(nome_arquivo, df_orig_cortado)
            self.estado.adicionar_evento_pipeline_arquivo(
                nome_arquivo,
                {
                    "categoria": "Tratamento de Dados",
                    "acao": "Recorte Temporal",
                    "modo": tipo_x.lower(),
                    "inicio": t_ini,
                    "fim": t_fim,
                    "deslocar_0": deslocar_0,
                },
            )

            if nome_arquivo in self.estado.get_graficos():
                for graf, config in self.estado.get_graficos()[nome_arquivo].items():
                    if "dados_y_calc" in config:
                        arr = np.array(config["dados_y_calc"])
                        if len(arr) == len(df):
                            arr_cortado = arr[indices_mantidos]
                            config["dados_y_calc"] = arr_cortado.tolist()

            QMessageBox.information(
                self, "Sucesso", "Arquivo sobrescrito com o recorte temporal."
            )

        else:
            novo_nome = f"{nome_arquivo}_cortado"
            contador = 1
            while novo_nome in self.estado.get_arquivos():
                novo_nome = f"{nome_arquivo}_cortado_{contador}"
                contador += 1

            import copy

            # Remove a referência 'arvore' (QTreeWidgetItem) temporariamente pois ela não pode ser copiada com deepcopy
            item_arvore_temporario = self.estado.get_arquivos()[nome_arquivo].pop(
                "arvore", None
            )

            try:
                novo_arq = copy.deepcopy(self.estado.get_arquivos()[nome_arquivo])
            finally:
                # Restaura a chave 'arvore' no arquivo original
                if item_arvore_temporario is not None:
                    # Repor item na árvore na cópia
                    novo_arq["arvore"] = item_arvore_temporario
                    # Repor no original também, caso precise (usando Getter para pegar a ref do dict)
                    arq_ref = self.estado.get_arquivo(nome_arquivo)
                    if arq_ref:
                        arq_ref["arvore"] = item_arvore_temporario

            novo_arq["dataframe"] = df_cortado

            if df_orig_cortado is not None:
                novo_arq["dataframe_original"] = df_orig_cortado

            elif "dataframe_original" in novo_arq:
                novo_arq["dataframe_original"] = df_cortado.copy()
            novo_arq["unidades_colunas"] = unidades.copy()

            if "pipeline" not in novo_arq:
                novo_arq["pipeline"] = []
            novo_arq["pipeline"].append(
                {
                    "categoria": "Tratamento de Dados",
                    "acao": "Recorte Temporal",
                    "modo": tipo_x.lower(),
                    "inicio": t_ini,
                    "fim": t_fim,
                    "deslocar_0": deslocar_0,
                }
            )
            self.estado.get_arquivos()[novo_nome] = novo_arq
            self.arvore.add_arvore(novo_nome)

            if nome_arquivo in self.estado.get_graficos():
                import copy

                pass  # Already handled by adicionar_config_grafico
                # Forca pegar os gráficos para copiar
                graficos_antigos = self.estado.get_graficos(nome_arquivo)
                for graf, config in graficos_antigos.items():
                    nova_config = {}
                    for k, v in config.items():
                        if k != "arvore":
                            if isinstance(v, (list, dict)):
                                nova_config[k] = copy.deepcopy(v)
                            else:
                                nova_config[k] = v

                    if "dados_y_calc" in nova_config:
                        arr = np.array(nova_config["dados_y_calc"])
                        if len(arr) == len(df):
                            arr_cortado = arr[indices_mantidos]
                            nova_config["dados_y_calc"] = arr_cortado.tolist()

                    self.estado.adicionar_config_grafico(novo_nome, graf, nova_config)

                for graf in self.estado.get_graficos(novo_nome):
                    self.arvore._adicionar_grafico_na_arvore_de_arquivo(novo_nome, graf)
            QMessageBox.information(
                self, "Sucesso", f"Recorte salvo como novo arquivo: {novo_nome}"
            )
        if self.estado.arquivo_ativo == nome_arquivo:
            self.exibidor_graficos._exibir_grafico_selecionado()

    def _aplicar_filtro(self, tipo_filtro):
        """Abre a janela de prévia do filtro e registra o filtro no histórico do gráfico."""

        if not any(self.estado.get_graficos().values()):
            QMessageBox.warning(
                self, "Aviso", "Nenhum gráfico disponível para aplicar filtro."
            )
            return
        dlg_sel = JanelaSelecionarGraficoFiltro(
            tipo_filtro,
            self.estado.get_graficos(),
            self.estado.arquivo_ativo,
            self.estado.grafico_ativo,
            self,
        )

        if dlg_sel.exec() != QDialog.DialogCode.Accepted:
            return
        dados_selecionados = dlg_sel.get_selecao()

        if dados_selecionados is None:
            QMessageBox.warning(
                self, "Aviso", "Selecione um gráfico válido (não um título de arquivo)."
            )
            return

        nome_arquivo, nome_grafico = dados_selecionados
        df_completo = self.estado.get_dataframe(nome_arquivo)
        config_grafico = self.estado.get_config_grafico(nome_arquivo, nome_grafico)

        if "dados_y_calc" in config_grafico:
            dados_y = pd.Series(config_grafico["dados_y_calc"], index=df_completo.index)
            dados_y.name = config_grafico.get("titulo", nome_grafico)
        else:
            dados_y = df_completo[config_grafico["eixo_y"]]
        dados_x = df_completo[config_grafico["eixo_x"]]
        precisa_perguntar_fs = True
        fs_calculado = 0.0
        unidade_x = config_grafico.get("unidade_x", "").lower().strip()
        unidades_segundos = ["s", "seg", "segundos", "second", "seconds"]

        if unidade_x in unidades_segundos:
            fs_calculado = calcular_fs(dados_x.values)
            if fs_calculado > 0:
                precisa_perguntar_fs = False
        fs_final = fs_calculado

        if precisa_perguntar_fs or fs_calculado <= 0:
            QMessageBox.information(
                self,
                "Aviso de Frequência",
                "A Frequência de Amostragem (fs) não pôde ser calculada automaticamente.\n\nPois o eixo X parece não estar em segundos.\n\nPor favor, informe a seguir a Frequência de Amostragem real dos dados.",
            )
            fs_input, ok = QInputDialog.getDouble(
                self,
                "Frequência de Amostragem",
                "Informe a Frequência de Amostragem em Hz (Ex: 100):",
                value=100.0,
                decimals=2,
                min=0.1,
            )

            if not ok or fs_input <= 0:
                return

            fs_final = fs_input
        arquivo_ativo_salvo = self.estado.arquivo_ativo
        grafico_ativo_salvo = self.estado.grafico_ativo
        janela = JanelaFiltro(
            tipo_filtro=tipo_filtro,
            dados_x=dados_x,
            dados_y=dados_y,
            fs=fs_final,
            unidade_x=config_grafico.get("unidade_x", ""),
            unidade_y=config_grafico.get("unidade_y", ""),
            titulo_grafico=nome_grafico,
            parent=self,
        )
        resultado_dialog = janela.exec()
        self.estado.arquivo_ativo = arquivo_ativo_salvo
        self.estado.grafico_ativo = grafico_ativo_salvo

        if resultado_dialog == QDialog.DialogCode.Accepted:
            resultado = janela.get_resultado()
            if resultado["dados_filtrados"] is None:
                return
            try:
                if tipo_filtro == "passa_baixa":
                    sufixo = f"PB {resultado['fc']:.1f}Hz"
                else:
                    sufixo = f"PA {resultado['fc']:.1f}Hz"
                if resultado.get("retificar", False):
                    sufixo += " ret"
                nome_base = nome_grafico
                nome_novo = f"{nome_base} [{sufixo}]"
                contador = 2

                while nome_novo in self.estado.get_graficos().get(nome_arquivo, {}):
                    nome_novo = f"{nome_base} [{sufixo}] ({contador})"
                    contador += 1
                config_novo = {
                    "tipo": config_grafico.get("tipo", "Linha"),
                    "titulo": nome_novo,
                    "eixo_x": config_grafico["eixo_x"],
                    "eixo_y": config_grafico.get("eixo_y", nome_grafico),
                    "unidade_x": config_grafico.get("unidade_x", ""),
                    "unidade_y": config_grafico.get("unidade_y", ""),
                    "cor": config_grafico.get("cor", "b"),
                    "dados_y_calc": (
                        resultado["dados_filtrados"].values
                        if hasattr(resultado["dados_filtrados"], "values")
                        else np.array(resultado["dados_filtrados"])
                    ),
                }
                historico = config_grafico.get("pipeline_grafico", [])

                if (
                    not historico
                    and "pipeline_colunas"
                    in self.estado.get_arquivos().get(nome_arquivo, {})
                ):
                    eixo_y_graf = config_grafico.get("eixo_y")
                    if eixo_y_graf:
                        historico = self.estado.get_pipeline_colunas(nome_arquivo).get(
                            eixo_y_graf, []
                        )
                historico = historico.copy()
                historico.append(
                    {
                        "tipo_operacao": "filtro",
                        "tipo": tipo_filtro,
                        "fc": resultado["fc"],
                        "ordem": resultado["ordem"],
                        "retificar": resultado.get("retificar", False),
                        "fc_manual": not resultado.get("fc_otima", False),
                    }
                )
                config_novo["pipeline_grafico"] = historico

                if nome_arquivo not in self.estado.get_graficos():
                    pass
                self.estado.adicionar_config_grafico(
                    nome_arquivo, nome_novo, config_novo
                )
                self.arvore._adicionar_grafico_na_arvore_de_arquivo(
                    nome_arquivo, nome_novo
                )
                self.estado.grafico_ativo = nome_novo
                self.estado.arquivo_ativo = nome_arquivo
                self.arvore._selecionar_item_na_arvore(nome_arquivo, nome_novo)
                self.exibidor_graficos._exibir_grafico_selecionado()

            except Exception as e:
                QMessageBox.critical(
                    self, "Erro no Filtro", f"Falha ao aplicar o filtro: {e}"
                )

    def abrir_preencher_lacunas(self):
        janela = JanelaPreencherLacunas(self.estado, self)
        if janela.exec() == QDialog.DialogCode.Accepted:
            selecoes, metodo = janela.get_selecoes()
            plotar_auto = janela.chk_plotar_auto.isChecked()
            salvar_como_novo = True  # Padrão fixo: sempre salva como nova variável
            pontos_manuais = getattr(janela, "pontos_manuais_preview", {})
            metodo_por_variavel = getattr(janela, "metodo_por_variavel_preview", {})

            if not selecoes:
                return
            try:
                batch_id = time.time()
                sufixos = {
                    "Linear": "interp_lin",
                    "Spline": "interp_spl",
                    "Média": "interp_med",
                }
                mapa_colunas_criadas = {}
                for nome_arq, colunas in selecoes.items():
                    df = self.estado.get_dataframe(nome_arq)
                    df_orig = self.estado.get_dataframe_original(nome_arq)
                    pipeline = self.estado.get_pipeline(nome_arq)
                    mapa_colunas_criadas[nome_arq] = {}

                    for col in colunas:
                        # Usa o método específico da variável (definido na preview) ou o global
                        metodo_col = metodo_por_variavel.get(col, metodo)
                        sufixo = sufixos.get(metodo_col, "interp")

                        dados_temporarios = df[col].copy().astype("float64")
                        if col in pontos_manuais:
                            for pt in pontos_manuais[col]:
                                dados_temporarios.iloc[pt["idx"]] = pt["y"]

                        if metodo_col == "Linear":
                            resultado, _ = interpolacao_linear(
                                df[col], dados_temporarios
                            )
                        elif metodo_col == "Spline":
                            resultado, _ = interpolacao_spline(
                                df[col], dados_temporarios
                            )
                        elif metodo_col == "Média":
                            resultado, _ = interpolacao_media(
                                df[col], dados_temporarios
                            )
                        else:
                            resultado = dados_temporarios

                        if salvar_como_novo:
                            nome_nova_col = f"{col}[{sufixo}]"
                        else:
                            nome_nova_col = col

                        df[nome_nova_col] = resultado
                        df_orig[nome_nova_col] = resultado.copy()
                        mapa_colunas_criadas[nome_arq][col] = nome_nova_col
                        unidades = self.estado.get_unidades_colunas(nome_arq)
                        if col in unidades:
                            unidades[nome_nova_col] = unidades[col]

                        historico_col = (
                            self.estado.get_pipeline_colunas(nome_arq)
                            .get(col, [])
                            .copy()
                        )
                        historico_col.append(
                            {
                                "acao": f"Preencher Lacunas ({metodo_col})",
                                "timestamp": time.time(),
                            }
                        )
                        self.estado.atualizar_pipeline_colunas(
                            nome_arq, col, historico_col
                        )
                        self.estado.atualizar_pipeline_colunas(
                            nome_arq, nome_nova_col, historico_col
                        )

                    pipeline.append(
                        {
                            "categoria": "Tratamento de Dados",
                            "acao": "Interpolação",
                            "metodo": metodo,
                            "metodo_por_variavel": {
                                col: metodo_por_variavel.get(col, metodo)
                                for col in colunas
                            },
                            "colunas": colunas,
                            "colunas_criadas": mapa_colunas_criadas[nome_arq],
                            "batch_id": batch_id,
                        }
                    )
                graficos_afetados = []

                for nome_arq, mapa_cols in mapa_colunas_criadas.items():

                    if nome_arq not in self.estado.get_graficos():
                        continue

                    for nome_graf, config_graf in self.estado.get_graficos()[
                        nome_arq
                    ].items():
                        if "dados_y_calc" in config_graf:
                            continue
                        col_y = config_graf.get("eixo_y", "")
                        col_x = config_graf.get("eixo_x", "")

                        if col_y in mapa_cols:
                            graficos_afetados.append(
                                {
                                    "arquivo": nome_arq,
                                    "grafico": nome_graf,
                                    "coluna_original": col_y,
                                    "coluna_nova": mapa_cols[col_y],
                                    "eixo_x": col_x,
                                }
                            )

                        elif col_x in mapa_cols:
                            graficos_afetados.append(
                                {
                                    "arquivo": nome_arq,
                                    "grafico": nome_graf,
                                    "coluna_original": col_x,
                                    "coluna_nova": mapa_cols[col_x],
                                    "eixo_x": col_x,
                                }
                            )

                graficos_novos_criados = []

                if plotar_auto:
                    for nome_arq, mapa_cols in mapa_colunas_criadas.items():
                        df = self.estado.get_dataframe(nome_arq)
                        col_tempo = None
                        # Prioriza 'time'/'tempo'; só usa 'frame'/'frames'/'item' se não houver
                        for c in df.columns:
                            if c.lower() in ["time", "tempo"]:
                                col_tempo = c
                                break
                        if not col_tempo:
                            for c in df.columns:
                                if c.lower() in ["frame", "frames", "item"]:
                                    col_tempo = c
                                    break
                        if not col_tempo:
                            col_tempo = df.columns[0]
                        for col_orig, col_nova in mapa_cols.items():
                            metodo_col_graf = metodo_por_variavel.get(col_orig, metodo)
                            sufixo_graf = sufixos.get(metodo_col_graf, "interp")
                            nome_novo_graf = f"{col_orig} [{sufixo_graf}]"
                            contador = 2

                            while self.estado.nome_existe(nome_arq, nome_novo_graf):
                                nome_novo_graf = (
                                    f"{col_orig} [{sufixo_graf}] ({contador})"
                                )
                                contador += 1
                            graf_orig = None

                            if nome_arq in self.estado.get_graficos():
                                for g_nome, g_conf in self.estado.get_graficos()[
                                    nome_arq
                                ].items():
                                    if g_conf.get("eixo_y") == col_orig:
                                        graf_orig = g_conf
                                        break

                            config_novo = {
                                "tipo": "Linha",
                                "titulo": nome_novo_graf,
                                "eixo_x": col_tempo,
                                "eixo_y": col_nova,
                                "unidade_x": self.estado.get_unidades_colunas(
                                    nome_arq
                                ).get(col_tempo, ""),
                                "unidade_y": self.estado.get_unidades_colunas(
                                    nome_arq
                                ).get(col_nova, ""),
                                "cor": "b",
                            }
                            historico = (
                                graf_orig.get("pipeline_grafico", []).copy()
                                if graf_orig
                                else []
                            )
                            historico.append(
                                {
                                    "tipo_operacao": "interpolacao",
                                    "metodo": metodo_col_graf.lower(),
                                }
                            )
                            config_novo["pipeline_grafico"] = historico

                            if nome_arq not in self.estado.get_graficos():
                                pass  # Already handled by adicionar_config_grafico

                            self.estado.adicionar_config_grafico(
                                nome_arq, nome_novo_graf, config_novo
                            )
                            self.arvore._adicionar_grafico_na_arvore_de_arquivo(
                                nome_arq, nome_novo_graf
                            )
                            graficos_novos_criados.append(
                                {"arquivo": nome_arq, "grafico": nome_novo_graf}
                            )

                else:
                    if graficos_afetados:
                        janela_sel = JanelaSelecionarGraficosInterpolados(
                            graficos_afetados, self
                        )

                        if janela_sel.exec() == QDialog.DialogCode.Accepted:
                            selecionados = janela_sel.get_selecionados()

                            for info in selecionados:
                                nome_arq = info["arquivo"]
                                nome_graf_orig = info["grafico"]
                                col_nova = info["coluna_nova"]
                                config_orig = self.estado.get_config_grafico(
                                    nome_arq, nome_graf_orig
                                )

                                if config_orig.get("eixo_y") == info["coluna_original"]:
                                    novo_eixo_y = col_nova
                                    novo_eixo_x = config_orig["eixo_x"]
                                else:
                                    novo_eixo_x = col_nova
                                    novo_eixo_y = config_orig["eixo_y"]
                                nome_novo_graf = f"{nome_graf_orig} [{sufixo}]"
                                contador = 2
                                while self.estado.nome_existe(nome_arq, nome_novo_graf):
                                    nome_novo_graf = (
                                        f"{nome_graf_orig} [{sufixo}] ({contador})"
                                    )
                                    contador += 1

                                config_novo = {
                                    "tipo": config_orig.get("tipo", "Linha"),
                                    "titulo": nome_novo_graf,
                                    "eixo_x": novo_eixo_x,
                                    "eixo_y": novo_eixo_y,
                                    "unidade_x": config_orig.get("unidade_x", ""),
                                    "unidade_y": config_orig.get("unidade_y", ""),
                                    "cor": config_orig.get("cor", "b"),
                                }
                                self.estado.adicionar_config_grafico(
                                    nome_arq, nome_novo_graf, config_novo
                                )
                                self.arvore._adicionar_grafico_na_arvore_de_arquivo(
                                    nome_arq, nome_novo_graf
                                )
                                graficos_novos_criados.append(
                                    {"arquivo": nome_arq, "grafico": nome_novo_graf}
                                )

                for nome_arq in mapa_colunas_criadas:
                    pipeline = self.estado.get_pipeline(nome_arq)
                    for step in reversed(pipeline):
                        if step.get("batch_id") == batch_id:
                            step["graficos_criados"] = [
                                g
                                for g in graficos_novos_criados
                                if g["arquivo"] == nome_arq
                            ]
                            break

                if graficos_novos_criados:
                    ultimo = graficos_novos_criados[-1]
                    self.estado.arquivo_ativo = ultimo["arquivo"]
                    self.estado.grafico_ativo = ultimo["grafico"]
                    self.arvore._selecionar_item_na_arvore(
                        ultimo["arquivo"], ultimo["grafico"]
                    )

                self.exibidor_graficos._exibir_grafico_selecionado()
                QMessageBox.information(
                    self, "Sucesso", "Novas variáveis interpoladas criadas com sucesso!"
                )

            except Exception as e:
                import traceback

                traceback.print_exc()
                QMessageBox.critical(
                    self, "Erro", f"Ocorreu um erro ao interpolar: {e}"
                )

    def _selecionar_arquivo_via_combo(self, titulo_janela):
        """Abre um diálogo com combo para selecionar arquivo. Retorna nome_arquivo ou None."""
        nomes_arquivos = list(self.estado.get_arquivos().keys())

        if not nomes_arquivos:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return None

        if len(nomes_arquivos) == 1:
            return nomes_arquivos[0]

        dlg = QDialog(self)
        dlg.setWindowTitle(titulo_janela)
        dlg.setMinimumWidth(350)
        layout_dlg = QVBoxLayout(dlg)
        layout_dlg.addWidget(QLabel("Selecione o arquivo:"))
        combo = QComboBox()
        combo.addItems(nomes_arquivos)

        if (
            self.estado.arquivo_ativo
            and self.estado.arquivo_ativo in self.estado.get_arquivos()
        ):
            combo.setCurrentText(self.estado.arquivo_ativo)

        layout_dlg.addWidget(combo)
        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_ok = QPushButton("Continuar")
        btn_ok.clicked.connect(dlg.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(dlg.reject)
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout_dlg.addLayout(botoes)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            return combo.currentText()
        return None

    def exportar_pipeline(self):

        nomes_arquivos = list(self.estado.get_arquivos().keys())

        if not nomes_arquivos:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        from ui.dialogs_operacoes import JanelaSelecionarVariosArquivos

        janela = JanelaSelecionarVariosArquivos(nomes_arquivos, self)

        if janela.exec() != QDialog.DialogCode.Accepted:
            return

        selecionados = janela.get_selecionados()

        if not selecionados:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo selecionado.")
            return

        pipelines_export = {}
        for nome_arquivo in selecionados:
            pipeline = self.estado.get_pipeline(nome_arquivo)

            if pipeline:
                pipelines_export[nome_arquivo] = pipeline

        if not pipelines_export:
            QMessageBox.information(
                self,
                "Exportar Histórico",
                "Os arquivos selecionados não possuem histórico de processamento.",
            )
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Histórico de Processamento",
            "",
            "Texto (*.txt);;JSON (*.json)",
        )

        if caminho:
            from arquivos.exportadores.historico import salvar_historico_processamento

            sucesso, erro_msg = salvar_historico_processamento(
                caminho, pipelines_export
            )
            if sucesso:
                QMessageBox.information(
                    self, "Exportar", "Histórico exportado com sucesso!"
                )
            else:
                QMessageBox.critical(self, "Erro", erro_msg)

    def _salvar_nova_variavel(self, resultado):
        try:
            nome_nova_var = self.estado._salvar_nova_variavel(resultado)
            nome_arquivo = resultado.get("nome_arquivo")
            QMessageBox.information(
                self,
                "Sucesso",
                f"Variável '{nome_nova_var}' criada com sucesso no arquivo '{nome_arquivo}'.",
            )

            if resultado.get("plotar_auto", False):
                df = self.estado.get_dataframe(nome_arquivo)
                unidades = self.estado.get_unidades_colunas(nome_arquivo)
                col_tempo = None
                for c in df.columns:
                    if c.lower() in ["time", "tempo"]:
                        col_tempo = c
                        break
                if not col_tempo:
                    for c in df.columns:
                        if c.lower() in ["frame", "frames", "item"]:
                            col_tempo = c
                            break
                if not col_tempo:
                    col_tempo = df.columns[0]

                nome_grafico = nome_nova_var
                contador = 2
                while self.estado.nome_existe(nome_arquivo, nome_grafico):
                    nome_grafico = f"{nome_nova_var} ({contador})"
                    contador += 1

                dados_grafico = {
                    "tipo": "Linha",
                    "titulo": nome_grafico,
                    "eixo_x": col_tempo,
                    "eixo_y": nome_nova_var,
                    "unidade_x": unidades.get(col_tempo, ""),
                    "unidade_y": resultado.get("unidade", ""),
                    "cor": "b",
                }
                self.estado.adicionar_config_grafico(
                    nome_arquivo, nome_grafico, dados_grafico
                )
                self.arvore._adicionar_grafico_na_arvore_de_arquivo(
                    nome_arquivo, nome_grafico
                )
                self.estado.arquivo_ativo = nome_arquivo
                self.estado.grafico_ativo = nome_grafico
                self.arvore._selecionar_item_na_arvore(nome_arquivo, nome_grafico)
                self.exibidor_graficos._exibir_grafico_selecionado()

        except ValueError as e:
            QMessageBox.warning(self, "Aviso", str(e))
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Erro inesperado ao salvar variável: {e}"
            )

    def _abrir_aritmetica_basica(self):
        """Abre a janela de aritmética básica (+, -, *, /)."""
        if not self.estado.get_arquivos():
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        janela = JanelaManipularVariaveis(self.estado, self.estado.arquivo_ativo, self)

        if janela.exec() == QDialog.DialogCode.Accepted:
            resultado = janela.get_resultado()

            if resultado:
                self._salvar_nova_variavel(resultado)

    def _abrir_trigonometria(self):
        """Abre a janela de operações trigonométricas."""

        if not self.estado.get_arquivos():
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        janela = JanelaTrigonometria(self.estado, self.estado.arquivo_ativo, self)

        if janela.exec() == QDialog.DialogCode.Accepted:
            resultado = janela.get_resultado()
            if resultado:
                self._salvar_nova_variavel(resultado)

    def _abrir_calculo_escalar(self):
        """Abre a janela de cálculo e funções escalares."""

        if not self.estado.get_arquivos():
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        janela = JanelaCalculoEscalar(self.estado, self.estado.arquivo_ativo, self)

        if janela.exec() == QDialog.DialogCode.Accepted:
            resultado = janela.get_resultado()
            if resultado:
                self._salvar_nova_variavel(resultado)

    def _abrir_definir_angulos(self):
        """Abre a janela de criação de ângulos por 3D points."""

        if not self.estado.get_arquivos():
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo aberto.")
            return

        janela = JanelaDefinirAngulos(self.estado, self.estado.arquivo_ativo, self)

        if janela.exec() == QDialog.DialogCode.Accepted:
            resultado = janela.get_resultado()
            if resultado:
                self._salvar_nova_variavel(resultado)

    def desfazer_ultima_operacao(self):
        nome_arquivo = self._selecionar_arquivo_via_combo("Desfazer Operação")
        if not nome_arquivo:
            return

        try:
            dados_arq = self.estado.get_arquivo(nome_arquivo)
            if not dados_arq:
                return
            pipeline = dados_arq.get("pipeline", [])

            idx_remover = -1
            for i in range(len(pipeline) - 1, -1, -1):
                if pipeline[i].get("is_operation_var"):
                    idx_remover = i
                    break

            if idx_remover == -1:
                QMessageBox.warning(
                    self, "Aviso", "Não há variáveis recém-criadas para desfazer."
                )
                return

            nome_var = pipeline[idx_remover].get("variavel_gerada")

            graficos_com_var = []
            for g_nome, g_config in self.estado.get_graficos(nome_arquivo).items():
                if (
                    g_config.get("eixo_y") == nome_var
                    or g_config.get("eixo_x") == nome_var
                ):
                    graficos_com_var.append(g_nome)

            if graficos_com_var:
                lista_graficos = "\n".join(f"- {g}" for g in graficos_com_var)
                resposta = QMessageBox.question(
                    self,
                    "Confirmar Exclusão",
                    f"A variável '{nome_var}' está sendo utilizada nos seguintes gráficos:\n\n"
                    f"{lista_graficos}\n\n"
                    f"Deseja excluir a variável e esses gráficos mesmo assim?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if resposta != QMessageBox.StandardButton.Yes:
                    return

                for g_nome in graficos_com_var:
                    g_config = self.estado.get_config_grafico(nome_arquivo, g_nome)
                    if g_config:
                        item_arvore = g_config.get("arvore")
                        if item_arvore and item_arvore.parent():
                            item_arvore.parent().removeChild(item_arvore)
                    self.estado.remover_grafico(nome_arquivo, g_nome)
                    if self.estado.grafico_ativo == g_nome:
                        self.estado.grafico_ativo = None

            self.estado.desfazer_ultima_operacao(nome_arquivo)

            if self.estado.arquivo_ativo == nome_arquivo:
                self.exibidor_graficos._exibir_grafico_selecionado()

            QMessageBox.information(
                self, "Sucesso", f"A variável '{nome_var}' foi removida com sucesso."
            )
        except ValueError as e:
            QMessageBox.warning(self, "Aviso", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro inesperado: {e}")

    def _abrir_scripts_salvos(self):
        from ui.dialogs_scripts import JanelaScriptsSalvos

        janela = JanelaScriptsSalvos(self.estado, self)
        janela.exec()

    def _abrir_criar_script(self):
        from ui.dialogs_scripts import JanelaCriarScript

        janela = JanelaCriarScript(self.estado, self)
        if janela.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Sucesso", "Script criado com sucesso.")

    def _abrir_criar_script_grafico(self):
        from ui.dialogs_scripts import JanelaCriarScriptGrafico

        janela = JanelaCriarScriptGrafico(self.estado, self)
        if janela.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self, "Sucesso", "Script de gráfico criado com sucesso."
            )

    def _aplicar_script_em_arquivo(self, nome_script, nome_arquivo):
        from processamento.executador_scripts import executar_script

        executar_script(self.estado, self, nome_script, nome_arquivo)

    def _abrir_janela_exportacao(self):
        janela = JanelaExportarGraficos(self.estado, self)
        if janela.exec() == QDialog.DialogCode.Accepted:
            selecionados = janela.get_selecionados()
            formato = janela.get_formato()
            self._executar_exportacao(selecionados, formato)

    def _executar_exportacao(self, selecionados, formato):
        from arquivos.exportadores.exp_graficos import exportar_graficos

        exportar_graficos(self, selecionados, formato)

    def _mostrar_sobre(self):
        texto = (
            "Software Biomec-SAS\n"
            "Versão: 2.0.0\n"
            "Desenvolvedor(a): Izadora Candotti de Oliveira\n"
            "Propriedade do Grupo de Pesquisa em Biomecânica (UFRGS).\n\n"
            "2026"
        )
        QMessageBox.about(self, "Sobre", texto)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
