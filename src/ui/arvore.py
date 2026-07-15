from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt


class GerenciadorArvore:
    """lógica de manipulação visual das árvores da interface."""

    def __init__(self, main_window, tree_arquivos, tree_composicoes):
        self.main_window = main_window  # Referência para chamar _remover_item_arvore, etc se precisar. Ou a lógica migra.
        self.tree_arquivos = tree_arquivos
        self.tree_composicoes = tree_composicoes

    def _adicionar_arquivo(self, nome_arquivo):
        guarda_arquivos = self.main_window.estado.get_arquivos()
        item = QTreeWidgetItem(self.tree_arquivos)
        item.setText(0, nome_arquivo)
        guarda_arquivos[nome_arquivo]["arvore"] = item
        return item

    def _adicionar_grafico_na_arvore_de_arquivo(self, nome_arquivo, nome_grafico):
        guarda_arquivos = self.main_window.estado.get_arquivos()
        guarda_graficos = self.main_window.estado.get_graficos()
        item_arquivo = guarda_arquivos[nome_arquivo]["arvore"]
        filho = QTreeWidgetItem(item_arquivo)
        filho.setText(0, nome_grafico)
        guarda_graficos[nome_arquivo][nome_grafico]["arvore"] = filho
        item_arquivo.setExpanded(True)
        return filho

    def _remover_grafico_da_arvore(self, nome_arquivo, nome_grafico):
        guarda_arquivos = self.main_window.estado.get_arquivos()
        guarda_graficos = self.main_window.estado.get_graficos()
        if nome_arquivo in guarda_arquivos and nome_grafico in guarda_graficos.get(
            nome_arquivo, {}
        ):
            item_grafico = guarda_graficos[nome_arquivo][nome_grafico].get("arvore")
            item_arquivo = guarda_arquivos[nome_arquivo].get("arvore")
            if item_grafico and item_arquivo:
                item_arquivo.removeChild(item_grafico)

            # A lógica de remover do dicionário vai para o GerenciadorEstado

    def _atualizar_arvore_composicoes(self):
        guarda_sobreposicoes = self.main_window.estado.get_sobreposicoes()
        guarda_exibicoes_simultaneas = (
            self.main_window.estado.get_exibicoes_simultaneas()
        )
        """Re-popula a arvore plana de visualizações mantendo Sobreposições acima das Simultâneas"""
        self.tree_composicoes.clear()

        for nome_comb, dados in guarda_sobreposicoes.items():
            item = QTreeWidgetItem(self.tree_composicoes)
            item.setText(0, nome_comb)
            item.setData(0, Qt.ItemDataRole.UserRole, "sobreposicao")
            dados["arvore"] = item

        for nome_simult, dados in guarda_exibicoes_simultaneas.items():
            item = QTreeWidgetItem(self.tree_composicoes)
            item.setText(0, nome_simult)
            item.setData(0, Qt.ItemDataRole.UserRole, "simultanea")
            dados["arvore"] = item

    def _selecionar_item_na_arvore(self, nome_arquivo=None, nome_grafico=None):
        guarda_arquivos = self.main_window.estado.get_arquivos()
        guarda_graficos = self.main_window.estado.get_graficos()
        """Seleciona visualmente um item na árvore de arquivos e foca nele."""
        self.tree_arquivos.clearSelection()
        self.tree_composicoes.clearSelection()

        if nome_arquivo and nome_grafico:
            item_grafico = (
                guarda_graficos.get(nome_arquivo, {})
                .get(nome_grafico, {})
                .get("arvore")
            )
            if item_grafico:
                self.tree_arquivos.setCurrentItem(item_grafico)
                item_grafico.setSelected(True)
                self.tree_arquivos.scrollToItem(item_grafico)
        elif nome_arquivo:
            item_arquivo = guarda_arquivos.get(nome_arquivo, {}).get("arvore")
            if item_arquivo:
                self.tree_arquivos.setCurrentItem(item_arquivo)
                item_arquivo.setSelected(True)
                self.tree_arquivos.scrollToItem(item_arquivo)

    def _selecionar_item_composicao(self, nome_composicao):
        guarda_sobreposicoes = self.main_window.estado.get_sobreposicoes()
        guarda_exibicoes_simultaneas = (
            self.main_window.estado.get_exibicoes_simultaneas()
        )
        """Seleciona visualmente um item na árvore de composições e foca nele."""
        self.tree_composicoes.clearSelection()
        self.tree_arquivos.clearSelection()

        item_comp = None
        if nome_composicao in guarda_sobreposicoes:
            item_comp = guarda_sobreposicoes[nome_composicao].get("arvore")
        elif nome_composicao in guarda_exibicoes_simultaneas:
            item_comp = guarda_exibicoes_simultaneas[nome_composicao].get("arvore")

        if item_comp:
            self.tree_composicoes.setCurrentItem(item_comp)
            item_comp.setSelected(True)
            self.tree_composicoes.scrollToItem(item_comp)

    def add_arvore(self, nome):
        item = QTreeWidgetItem(self.tree_arquivos)
        item.setText(0, nome)
        self.main_window.estado.get_arquivos()[nome]["arvore"] = item

    def add_filho(self, nome_arqv, nome_grafico, dados_grafico):
        item_pai = None
        for i in range(self.tree_arquivos.topLevelItemCount()):
            item = self.tree_arquivos.topLevelItem(i)
            if item.text(0) == nome_arqv:
                item_pai = item
                break
        if item_pai is not None:
            item_grafico = QTreeWidgetItem(item_pai)
            item_grafico.setText(0, nome_grafico)
            item_pai.setExpanded(True)
            self.main_window.estado.get_graficos()[nome_arqv][
                nome_grafico
            ] = dados_grafico

            # Novo gráfico vira o ativo
            self.main_window.estado.arquivo_ativo = nome_arqv
            self.main_window.estado.grafico_ativo = nome_grafico

            self.tree_arquivos.clearSelection()
            item_grafico.setSelected(True)

    def _adicionar_grafico_na_arvore(self, nome_grafico):
        for i in range(self.tree_arquivos.topLevelItemCount()):
            item = self.tree_arquivos.topLevelItem(i)
            if item.text(0) == self.main_window.estado.arquivo_ativo:
                item_filho = QTreeWidgetItem(item)
                item_filho.setText(0, nome_grafico)
                item.setExpanded(True)
                # Salvar a referencia no estado
                if (
                    self.main_window.estado.arquivo_ativo
                    in self.main_window.estado.get_graficos()
                ):
                    if (
                        nome_grafico
                        in self.main_window.estado.get_graficos()[
                            self.main_window.estado.arquivo_ativo
                        ]
                    ):
                        self.main_window.estado.get_graficos()[
                            self.main_window.estado.arquivo_ativo
                        ][nome_grafico]["arvore"] = item_filho
                break

    def _remover_item_arvore(self, nome_item):
        for i in range(self.tree_arquivos.topLevelItemCount()):
            item = self.tree_arquivos.topLevelItem(i)
            if item.text(0) == nome_item:
                self.tree_arquivos.takeTopLevelItem(i)
                break
