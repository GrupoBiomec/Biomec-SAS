from processamento.gera_graficos import JanelaLinhaReferencia

from ui.dialogs_processamento import (
    JanelaAjustesExibicao,
    JanelaEditarExibicaoSimultanea,
)
from ui.dialogs_operacoes import JanelaExcluirReferencias
from processamento.gera_graficos import JanelaConfig
from processamento.gera_graficos import JanelaSobreporGraficos, JanelaExibicaoSimultanea
from processamento.limpeza import recomputar_dados_com_filtros
from PyQt6.QtWidgets import QMenu, QMessageBox, QDialog
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import pandas as pd
import numpy as np
from processamento.informacoes_curvas import AnaliseCurva
from ui.dialogs_processamento import JanelaPlotarSeparadamente

from ui.dialogs_infos_curvas import JanelaInformacoesCurva


class ExibidorGraficos:
    def __init__(self, main_window):
        self.mw = main_window

    def _desativar_zoom(self):
        if hasattr(self.mw, "zoom_ativo") and self.mw.zoom_ativo:
            self.mw.zoom_ativo = False
            if hasattr(self.mw, "gerador_graficos") and self.mw.gerador_graficos:
                self.mw.gerador_graficos.set_zoom_mode(False)
        if hasattr(self.mw, "btn_desativar_zoom"):
            self.mw.btn_desativar_zoom.hide()

    def _toggle_zoom(self, checked):
        self.mw.zoom_ativo = checked
        if hasattr(self.mw, "btn_desativar_zoom"):
            self.mw.btn_desativar_zoom.setVisible(checked)
        if hasattr(self.mw, "gerador_graficos") and self.mw.gerador_graficos:
            self.mw.gerador_graficos.set_zoom_mode(checked)

    def _plotar_separadamente(self, nome_composicao):
        config = self.mw.estado.get_sobreposicoes().get(nome_composicao, {})
        if not config:
            return

        graficos_ocultos = []
        mapeamento = {}
        for ref in config.get("graficos_fonte", []):
            arq = ref.get("arquivo")
            graf = ref.get("grafico")
            if (
                self.mw.estado.get_graficos()
                .get(arq, {})
                .get(graf, {})
                .get("hidden", False)
            ):
                label = f"{arq} → {graf}"
                graficos_ocultos.append(label)
                mapeamento[label] = (arq, graf)

        if not graficos_ocultos:
            QMessageBox.information(
                self.mw,
                "Info",
                "Todos os gráficos desta composição já estão plotados separadamente.",
            )
            return

        janela = JanelaPlotarSeparadamente(graficos_ocultos, self.mw)
        if janela.exec() == QDialog.DialogCode.Accepted:
            selecionados = janela.get_selecionados()
            if not selecionados:
                return

            for label in selecionados:
                arq, graf = mapeamento[label]
                self.mw.estado.get_graficos()[arq][graf]["hidden"] = False
                self.mw.arvore._adicionar_grafico_na_arvore_de_arquivo(arq, graf)

            QMessageBox.information(
                self.mw,
                "Sucesso",
                f"{len(selecionados)} gráfico(s) extraído(s) para a árvore principal!",
            )

    def _exibir_grafico_selecionado(self):
        # COORDENA: Pega dados salvos → Chama gerador → Atualiza interface

        if not self.mw.estado.grafico_ativo:
            self.mw._resetar_interface()
            return

        self.mw.gerador_graficos.limpar()
        self.mw.placeholder_widget.hide()
        self.mw.container_grafico.show()

        if self.mw.estado.grafico_ativo in self.mw.estado.get_sobreposicoes():
            self.mw.area_simultanea.hide()
            self.mw.area_grafico.show()
            config_grafico = self.mw.estado.get_sobreposicoes()[
                self.mw.estado.grafico_ativo
            ]
            self._exibir_grafico_sobreposto(config_grafico)

        elif self.mw.estado.grafico_ativo in self.mw.estado.get_exibicoes_simultaneas():
            self.mw.area_grafico.hide()
            self.mw.area_simultanea.show()
            config_grafico = self.mw.estado.get_exibicoes_simultaneas()[
                self.mw.estado.grafico_ativo
            ]
            self._exibir_grafico_simultaneo(config_grafico)

        elif (
            self.mw.estado.arquivo_ativo
            and self.mw.estado.arquivo_ativo in self.mw.estado.get_graficos()
        ):
            self.mw.area_simultanea.hide()
            self.mw.area_grafico.show()
            if (
                self.mw.estado.grafico_ativo
                in self.mw.estado.get_graficos()[self.mw.estado.arquivo_ativo]
            ):
                config_grafico = self.mw.estado.get_graficos()[
                    self.mw.estado.arquivo_ativo
                ][self.mw.estado.grafico_ativo]

                # Se o gráfico tem dados calculados (é uma operação)
                if "dados_y_calc" in config_grafico:
                    df = self.mw.estado.get_arquivos()[self.mw.estado.arquivo_ativo][
                        "dataframe"
                    ]
                else:
                    # É um gráfico original, precisa df completo para buscar colunas.
                    df = self.mw.estado.get_arquivos()[self.mw.estado.arquivo_ativo][
                        "dataframe"
                    ]

                self._exibir_grafico_normal(config_grafico, df)
            else:
                self.mw._resetar_interface()
                return
        else:
            self.mw._resetar_interface()
            return

        self.mw.grafico_sendo_exibido = True

    def _exibir_grafico_normal(self, config_grafico, df):
        # Exibe gráfico normal (não sobreposto)
        tipo = config_grafico["tipo"]
        col_y_origem = config_grafico.get("eixo_y", "")
        colunas_modificadas = self.mw.estado.get_arquivos()[
            self.mw.estado.arquivo_ativo
        ].get("colunas_modificadas", set())

        # Descobrir qual método foi usado para o preenchimento olhando no pipeline
        metodo_usado = "Desconhecida"
        pipeline = self.mw.estado.get_arquivos()[self.mw.estado.arquivo_ativo].get(
            "pipeline", []
        )
        for step in reversed(pipeline):
            if step.get("acao") == "preencher_lacunas" and col_y_origem in step.get(
                "colunas", []
            ):
                metodo_usado = step.get("metodo", "Desconhecida")
                break

        # Gerencia visibilidade do checkbox Comparar Original
        tem_modificacao = (
            "dados_y_calc" not in config_grafico and col_y_origem in colunas_modificadas
        )

        # Desconecta e reconecta para não dar loops, ou só atualiza a visibilidade (estado é preservado)
        self.mw.check_comparar.setVisible(tem_modificacao)
        if tem_modificacao:
            self.mw.check_comparar.setText(f"Destacar Preenchimento ({metodo_usado})")

        if "dados_y_calc" in config_grafico:
            dados_y_plot = config_grafico["dados_y_calc"]
            label_y_plot = config_grafico.get("titulo", self.mw.estado.grafico_ativo)
        else:
            dados_y_plot = df[config_grafico["eixo_y"]]
            label_y_plot = config_grafico["eixo_y"]

        dados_x_plot = df[config_grafico["eixo_x"]]

        # Formata labels com unidades entre colchetes
        label_x_base = config_grafico.get("label_x", config_grafico["eixo_x"])
        unidade_x = config_grafico.get("unidade_x", "")
        if unidade_x:
            label_x_str = f"{label_x_base} [{unidade_x}]"
        else:
            label_x_str = label_x_base

        label_y_base = config_grafico.get("label_y", label_y_plot)
        unidade_y = config_grafico.get("unidade_y", "")
        if unidade_y:
            label_y_str = f"{label_y_base} [{unidade_y}]"
        else:
            label_y_str = label_y_base

        config_plot = {
            "titulo": config_grafico.get("titulo", self.mw.estado.grafico_ativo),
            "label_x": label_x_str,
            "label_y": label_y_str,
            "cor": config_grafico.get("cor", "b"),
            "linhas_referencia": config_grafico.get("linhas_referencia", []),
        }

        # Plota linha processada principal primeiro
        if tipo == "Linha":
            self.mw.gerador_graficos.plotar_linha(
                dados_x_plot, dados_y_plot, config_plot
            )

            # Plota somente as lacunas interpoladas por cima
            if tem_modificacao and self.mw.check_comparar.isChecked():
                df_orig = self.mw.estado.get_arquivos()[self.mw.estado.arquivo_ativo][
                    "dataframe_original"
                ]
                mask_lacunas = df_orig[config_grafico["eixo_y"]].isna().values

                if mask_lacunas.any():
                    # Expande a máscara para engatar com os pontos validos vizinhos
                    mask_expandida = mask_lacunas.copy()
                    mask_expandida[:-1] |= mask_lacunas[1:]
                    mask_expandida[1:] |= mask_lacunas[:-1]

                    dados_destaque_y = dados_y_plot.copy()
                    if isinstance(dados_destaque_y, pd.Series):
                        dados_destaque_y = dados_destaque_y.values.copy()

                    # Converte para float para evitar erro ao atribuir np.nan caso os dados sejam inteiros
                    dados_destaque_y = dados_destaque_y.astype(float)

                    # Tudo que NÃO é lacuna vira NaN, assim o pyqtgraph não desenha
                    dados_destaque_y[~mask_expandida] = np.nan

                    cor_base = config_plot.get("cor", "b")
                    cor_destaque = (
                        "m" if cor_base == "b" else "b"
                    )  # magenta se for azul, senão azul

                    self.mw.gerador_graficos.plotar_linha(
                        dados_x_plot,
                        dados_destaque_y,
                        {
                            "titulo": config_grafico["titulo"],
                            "label_x": config_grafico["eixo_x"],
                            "label_y": label_y_plot,
                            "cor": cor_destaque,
                            "espessura": 4,
                            "nome_legenda": f"Preenchimento ({metodo_usado})",
                            "connect": "finite",
                        },
                    )
        elif tipo == "Dispersão":
            self.mw.gerador_graficos.plotar_scatter(
                dados_x_plot, dados_y_plot, config_plot
            )

    def _menu_grafico(self, item, pos):
        # Menu de contexto para gráficos normais
        menu = QMenu(self.mw)

        nome_arquivo_l = self.mw._get_arquivo_nome(item)
        nome_grafico_l = item.text(0)
        try:
            config_atual = self.mw.estado.get_graficos()[nome_arquivo_l][nome_grafico_l]
        except KeyError:
            config_atual = {}

        menu.addSeparator()

        # Linhas de Referência (polinômios)
        linhas_ref = config_atual.get("linhas_referencia", [])

        if linhas_ref:
            submenu_refs = QMenu("Linhas de Referência", self.mw)
            for idx, lr in enumerate(linhas_ref):
                titulo_lr = lr.get("titulo", f"Referência {idx+1}")
                ativo = lr.get("ativo", True)
                texto_item = f"{'✓' if ativo else '✗'} {titulo_lr}"
                acao_toggle = QAction(texto_item, self.mw)
                acao_toggle.triggered.connect(
                    lambda checked, i=idx: self._toggle_referencia(item, i)
                )
                submenu_refs.addAction(acao_toggle)

            submenu_refs.addSeparator()
            acao_excluir_refs = QAction("Excluir Linhas...", self.mw)
            acao_excluir_refs.triggered.connect(lambda: self._excluir_referencias(item))
            submenu_refs.addAction(acao_excluir_refs)
            menu.addMenu(submenu_refs)

        if len(linhas_ref) < 5:
            acao_add_ref = QAction("Adicionar Linha de Referência", self.mw)
            acao_add_ref.triggered.connect(
                lambda: self._adicionar_linha_referencia(item)
            )
            menu.addAction(acao_add_ref)

        menu.addSeparator()

        # Informações da Curva
        acao_info = QAction("Informações da Curva", self.mw)
        acao_info.triggered.connect(lambda: self._mostrar_informacoes_curva(item))
        menu.addAction(acao_info)

        menu.addSeparator()

        # Scripts de Gráficos
        if (
            hasattr(self.mw.estado, "guarda_scripts_graficos")
            and self.mw.estado.guarda_scripts_graficos
        ):
            submenu_scripts = QMenu("Aplicar Script", self.mw)
            for nome_script in self.mw.estado.guarda_scripts_graficos.keys():
                acao_script = QAction(nome_script, self.mw)
                acao_script.triggered.connect(
                    lambda checked, s=nome_script: self.mw._aplicar_script_em_grafico(
                        s, nome_arquivo_l, nome_grafico_l
                    )
                )
                submenu_scripts.addAction(acao_script)
            menu.addMenu(submenu_scripts)
            menu.addSeparator()

        # Modo Zoom
        acao_zoom = QAction("Ativar Zoom", self.mw)
        acao_zoom.setCheckable(True)
        acao_zoom.setChecked(self.mw.zoom_ativo)
        acao_zoom.triggered.connect(self._toggle_zoom)
        menu.addAction(acao_zoom)

        # Editar:
        acao_editar = QAction("Editar Gráfico", self.mw)
        acao_editar.triggered.connect(lambda: self._abrir_janela_ajustes(item))
        menu.addAction(acao_editar)

        # Excluir:
        acao_excluir = QAction("Excluir Gráfico", self.mw)
        acao_excluir.triggered.connect(lambda: self._remover_grafico(item))
        menu.addAction(acao_excluir)

        # Mostra o menu
        menu.exec(self.mw.tree.mapToGlobal(pos))

    def _mostrar_informacoes_curva(self, item):
        """Calcula e exibe informações estatísticas da curva do gráfico selecionado."""
        nome_arquivo = self.mw._get_arquivo_nome(item)
        nome_grafico = item.text(0)

        if (
            nome_arquivo not in self.mw.estado.get_graficos()
            or nome_grafico not in self.mw.estado.get_graficos()[nome_arquivo]
        ):
            QMessageBox.warning(self.mw, "Aviso", "Gráfico não encontrado.")
            return

        config = self.mw.estado.get_graficos()[nome_arquivo][nome_grafico]
        df = self.mw.estado.get_arquivos()[nome_arquivo]["dataframe"]

        dados_x = df[config["eixo_x"]]

        if "dados_y_calc" in config:
            dados_y = config["dados_y_calc"]
        else:
            dados_y = df[config["eixo_y"]]

        filtros = config.get("filtros_ativos", [])
        filtros_ativos = [f for f in filtros if f.get("ativo", True)]
        if filtros_ativos:
            dados_y = recomputar_dados_com_filtros(dados_x, dados_y, filtros_ativos)

        analise = AnaliseCurva(dados_x, dados_y)
        info = analise.resumo()

        # Monta labels com unidades para exibição
        unidades_colunas = self.mw.estado.get_arquivos()[nome_arquivo].get(
            "unidades_colunas", {}
        )
        var_x = config.get("eixo_x", "")
        var_y = config.get("eixo_y", "")

        unidade_x = config.get("unidade_x", "") or unidades_colunas.get(var_x, "")
        unidade_y = config.get("unidade_y", "") or unidades_colunas.get(var_y, "")

        label_x = f"{var_x} [{unidade_x}]" if unidade_x else var_x
        label_y = f"{var_y} [{unidade_y}]" if unidade_y else var_y

        janela = JanelaInformacoesCurva(
            nome_grafico,
            info,
            label_x,
            label_y,
            var_x,
            var_y,
            unidade_x=unidade_x,
            unidade_y=unidade_y,
            parent=self.mw,
        )
        janela.exec()

    def _remover_grafico(self, item):
        nome_arquivo = self.mw._get_arquivo_nome(item)
        nome_grafico = item.text(0)

        # Coleta nomes recursivamente (gráfico + derivados)
        nomes_para_remover = [nome_grafico]

        def coletar_filhos(node):
            for i in range(node.childCount()):
                child = node.child(i)
                nomes_para_remover.append(child.text(0))
                coletar_filhos(child)

        coletar_filhos(item)

        # Busca composições que dependem dos gráficos a serem removidos
        composicoes_afetadas = self.mw.estado._buscar_composicoes_que_usam_grafico(
            nome_arquivo, set(nomes_para_remover)
        )

        # Monta mensagem de confirmação
        msg = QMessageBox(self.mw)
        msg.setWindowTitle("Remover Gráfico")

        if composicoes_afetadas:
            msg.setText(
                f'Remover o gráfico "{nome_grafico}"?\n\n'
                f"Esta ação também excluirá todas as composições de visualização "
                f"que utilizam esse gráfico."
            )
        elif item.childCount() > 0:
            msg.setText(
                f"Remover o gráfico '{nome_grafico}' e todos os seus derivados?"
            )
        else:
            msg.setText(f"Remover o gráfico '{nome_grafico}'?")

        try:
            btn_sim = msg.addButton("Sim", QMessageBox.ButtonRole.AcceptRole)
            btn_nao = msg.addButton("Não", QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(btn_nao)
        except Exception:
            btn_sim = msg.addButton("Sim", QMessageBox.AcceptRole)
            btn_nao = msg.addButton("Não", QMessageBox.RejectRole)
            msg.setDefaultButton(btn_nao)

        if hasattr(msg, "exec_"):
            msg.exec_()
        else:
            msg.exec()

        if msg.clickedButton() == btn_sim:
            # 1. Remover composições que dependem deste gráfico
            for tipo, nome_comp in composicoes_afetadas:
                self.mw.estado._remover_composicao(nome_comp, tipo)

            if composicoes_afetadas:
                self.mw.arvore._atualizar_arvore_composicoes()

            # 2. Remover da árvore
            pai = item.parent()
            if pai:
                pai.removeChild(item)

            # 3. Remover dos dados
            if nome_arquivo in self.mw.estado.get_graficos():
                for nome in nomes_para_remover:
                    if nome in self.mw.estado.get_graficos()[nome_arquivo]:
                        del self.mw.estado.get_graficos()[nome_arquivo][nome]

            # 4. Atualizar interface se necessário
            if (
                self.mw.estado.arquivo_ativo == nome_arquivo
                and self.mw.estado.grafico_ativo in nomes_para_remover
            ):
                self.mw._limpar_selecao()
            elif self.mw.estado.grafico_ativo and self.mw.estado.grafico_ativo in [
                c[1] for c in composicoes_afetadas
            ]:
                self.mw._limpar_selecao()

    def _exibir_grafico_simultaneo(self, config_grafico):
        self.mw.area_simultanea.clear()

        rows = config_grafico.get("layout", [])
        for r_idx, row in enumerate(rows):
            for c_idx, ref in enumerate(row):
                if ref is None:
                    continue

                arquivo = ref["arquivo"]
                grafico = ref["grafico"]

                if grafico not in self.mw.estado.get_graficos().get(arquivo, {}):
                    continue

                config_original = self.mw.estado.get_graficos()[arquivo][grafico]
                df = self.mw.estado.get_arquivos()[arquivo]["dataframe"]

                if config_original["eixo_x"] not in df.columns:
                    print(
                        f"Aviso: Coluna X '{config_original['eixo_x']}' não encontrada no arquivo '{arquivo}'"
                    )
                    continue
                dados_x_plot = df[config_original["eixo_x"]]

                if "dados_y_calc" in config_original:
                    dados_y_plot = config_original["dados_y_calc"]
                else:
                    if config_original["eixo_y"] not in df.columns:
                        print(
                            f"Aviso: Coluna Y '{config_original['eixo_y']}' não encontrada no arquivo '{arquivo}'"
                        )
                        continue
                    dados_y_plot = df[config_original["eixo_y"]]

                filtros = config_original.get("filtros_ativos", [])
                filtros_ativos = [f for f in filtros if f.get("ativo", True)]
                if filtros_ativos:
                    dados_y_plot = recomputar_dados_com_filtros(
                        dados_x_plot, dados_y_plot, filtros_ativos
                    )

                # Título customizado ou nome original do gráfico
                titulo_plot = ref.get("titulo_custom", grafico)

                # Criando plot na grade
                colspan = ref.get("colspan", 1)
                rowspan = ref.get("rowspan", 1)
                plot_item = self.mw.area_simultanea.addPlot(
                    row=r_idx,
                    col=c_idx,
                    rowspan=rowspan,
                    colspan=colspan,
                    title=titulo_plot,
                )
                plot_item.showGrid(x=True, y=True)
                plot_item.setMenuEnabled(False)

                u_x = config_original.get("unidade_x", "")
                u_y = config_original.get("unidade_y", "")

                lbl_x_base = config_original.get(
                    "label_x", config_original.get("eixo_x", "X")
                )
                lbl_y_base = config_original.get(
                    "label_y", config_original.get("eixo_y", "Y")
                )

                import re

                lbl_x = re.sub(r"\s*\[.*?\]$", "", str(lbl_x_base))
                lbl_y = re.sub(r"\s*\[.*?\]$", "", str(lbl_y_base))

                if u_x:
                    lbl_x += f" ({u_x})"
                if u_y:
                    lbl_y += f" ({u_y})"

                plot_item.setLabel("bottom", lbl_x)
                plot_item.setLabel("left", lbl_y)

                # Plotando (usa cor customizada se disponível)
                tipo = config_original.get("tipo", "Linha")
                cor = ref.get("cor_custom", config_original.get("cor", "b"))

                x_vals = self.mw.gerador_graficos._converter_para_array(dados_x_plot)
                y_vals = self.mw.gerador_graficos._converter_para_array(dados_y_plot)

                if tipo == "Dispersão":
                    scatter = pg.ScatterPlotItem(x=x_vals, y=y_vals, size=10, brush=cor)
                    plot_item.addItem(scatter)
                else:
                    pen = pg.mkPen(color=cor, width=2)
                    connect_type = config_original.get("connect", "all")
                    plot_item.plot(x=x_vals, y=y_vals, pen=pen, connect=connect_type)

                # Plotar linhas de referência do gráfico original
                linhas_ref = config_original.get("linhas_referencia", [])
                linhas_ativas = [lr for lr in linhas_ref if lr.get("ativo", True)]
                if linhas_ativas:
                    # Captura range Y dos dados originais
                    y_limpo = y_vals[np.isfinite(y_vals)]
                    if len(y_limpo) > 0:
                        y_min_o, y_max_o = float(y_limpo.min()), float(y_limpo.max())
                        margem_o = (
                            (y_max_o - y_min_o) * 0.05 if y_max_o != y_min_o else 1.0
                        )
                    else:
                        y_min_o, y_max_o, margem_o = 0, 1, 0.05

                    plot_item.addLegend()
                    for lr in linhas_ativas:
                        y_ref = self.mw.gerador_graficos._converter_para_array(
                            lr["dados_y"]
                        )
                        cor_ref = lr.get("cor", "r")
                        pen_ref = pg.mkPen(
                            color=cor_ref, style=Qt.PenStyle.DashLine, width=2
                        )
                        nome_ref = lr.get("titulo", "Referência")
                        plot_item.plot(x=x_vals, y=y_ref, pen=pen_ref, name=nome_ref)

                    plot_item.setYRange(
                        y_min_o - margem_o, y_max_o + margem_o, padding=0
                    )

    def _exibir_grafico_sobreposto(self, config_combinado):

        if "graficos_fonte" not in config_combinado:
            QMessageBox.critical(
                self.mw, "Erro", "Dados da sobreposição estão corrompidos!"
            )
            return

        try:
            sinais = []
            cores = ["r", "g", "b", "c", "m", "y", "k"]

            for i, ref_grafico in enumerate(config_combinado["graficos_fonte"]):
                arquivo = ref_grafico["arquivo"]
                grafico = ref_grafico["grafico"]

                if grafico not in self.mw.estado.get_graficos().get(arquivo, {}):
                    print(f"ERRO: Gráfico '{grafico}' não encontrado em '{arquivo}'!")
                    continue

                config_original = self.mw.estado.get_graficos()[arquivo][grafico]
                df = self.mw.estado.get_arquivos()[arquivo]["dataframe"]

                # Extract Data
                if config_original["eixo_x"] not in df.columns:
                    print(
                        f"Aviso: Coluna X '{config_original['eixo_x']}' não encontrada no arquivo '{arquivo}'"
                    )
                    continue
                dados_x_plot = df[config_original["eixo_x"]]

                if "dados_y_calc" in config_original:
                    dados_y_plot = config_original["dados_y_calc"]
                else:
                    if config_original["eixo_y"] not in df.columns:
                        print(
                            f"Aviso: Coluna Y '{config_original['eixo_y']}' não encontrada no arquivo '{arquivo}'"
                        )
                        continue
                    dados_y_plot = df[config_original["eixo_y"]]

                filtros = config_original.get("filtros_ativos", [])
                filtros_ativos = [f for f in filtros if f.get("ativo", True)]
                if filtros_ativos:
                    dados_y_plot = recomputar_dados_com_filtros(
                        dados_x_plot, dados_y_plot, filtros_ativos
                    )

                # Extract Units
                unidade_x = config_original.get("unidade_x", "")
                unidade_y = config_original.get("unidade_y", "")

                # Format Labels without redundant units
                label_x_base = config_original.get(
                    "label_x", config_original.get("eixo_x", "X")
                )

                label_y_base = config_original.get(
                    "label_y", config_original.get("eixo_y", "Y")
                )

                nome_legenda_base = ref_grafico.get(
                    "nome_legenda", f"{arquivo} - {grafico}"
                )

                sinal = {
                    "x_data": dados_x_plot,
                    "y_data": dados_y_plot,
                    "x_unit": unidade_x,
                    "y_unit": unidade_y,
                    "nome": nome_legenda_base,
                    "cor": ref_grafico.get("cor", cores[i % len(cores)]),
                    "tipo": config_original.get("tipo", "Linha"),
                    "label_x": label_x_base,
                    "label_y": label_y_base,
                }
                sinais.append(sinal)

            if sinais:
                tendencia = config_combinado.get("tendencia_visual", False)

                # Coleta referências ativas de todos os gráficos-fonte (com x_data próprio)
                todas_refs = []
                for ref_grafico in config_combinado["graficos_fonte"]:
                    arquivo = ref_grafico["arquivo"]
                    grafico = ref_grafico["grafico"]
                    if grafico in self.mw.estado.get_graficos().get(arquivo, {}):
                        config_orig = self.mw.estado.get_graficos()[arquivo][grafico]
                        df_ref = self.mw.estado.get_arquivos()[arquivo]["dataframe"]
                        x_data_ref = df_ref[config_orig["eixo_x"]]
                        for lr in config_orig.get("linhas_referencia", []):
                            # Copia o dict para não poluir o original com x_data
                            lr_com_x = dict(lr)
                            lr_com_x["_x_data"] = x_data_ref
                            todas_refs.append(lr_com_x)

                config_combinado["_linhas_referencia_coletadas"] = todas_refs
                titulo_composicao = config_combinado.get(
                    "titulo", self.mw.estado.grafico_ativo
                )
                self.mw.gerador_graficos.plotar_sinais_sobrepostos(
                    sinais,
                    titulo_composicao,
                    self,
                    tendencia_visual=tendencia,
                    config_geral=config_combinado,
                )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"ERRO ao exibir gráfico sobreposto: {e}")

    def criar_grafico(self):
        if not self.mw.estado.arquivo_ativo:
            return

        df = self.mw.estado.get_arquivos()[self.mw.estado.arquivo_ativo]["dataframe"]
        cabecalho = (
            self.mw.estado.get_arquivos()[self.mw.estado.arquivo_ativo].get("cabecalho")
            or {}
        )
        unidades_colunas = self.mw.estado.get_arquivos()[
            self.mw.estado.arquivo_ativo
        ].get("unidades_colunas", {})

        # Injeta unidade_y_default se existir no cabecalho
        janela = JanelaConfig(
            df,
            self.mw,
            unidade_y_default=cabecalho.get("measure_unit", ""),
            unidades_colunas=unidades_colunas,
        )

        if janela.exec() == QDialog.DialogCode.Accepted:
            config = janela.get_configuracoes()

            # Obter unidades configuradas na Janela
            unidade_y = config.get("unidade_y", "")
            unidade_x = config.get("unidade_x", "")

            # Criar nome do gráfico (usa o título digitado ou gera automaticamente)
            nome_grafico = (
                config["titulo"]
                or f"Gráfico {len(self.mw.estado.get_graficos().get(self.mw.estado.arquivo_ativo, {})) + 1}"
            )

            # Criar gráfico principal
            dados_grafico = {
                "tipo": config["tipo"],
                "titulo": nome_grafico,
                "eixo_x": config["eixo_x"],
                "eixo_y": config["eixo_y"],
                "unidade_x": unidade_x,
                "unidade_y": unidade_y,
            }

            # Verifica se gráfico ja existe
            if self.mw.estado.nome_existe(self.mw.estado.arquivo_ativo, nome_grafico):
                QMessageBox.warning(
                    self.mw,
                    "Nome Duplicado",
                    f"Já existe um gráfico chamado '{nome_grafico}' neste arquivo.\n"
                    "Por favor, escolha outro nome.",
                )
                return

            # Salvar gráfico principal
            if self.mw.estado.arquivo_ativo not in self.mw.estado.get_graficos():
                self.mw.estado.get_graficos()[self.mw.estado.arquivo_ativo] = {}
            self.mw.estado.get_graficos()[self.mw.estado.arquivo_ativo][
                nome_grafico
            ] = dados_grafico

            self.mw.arvore._adicionar_grafico_na_arvore(nome_grafico)
            self.mw.estado.grafico_ativo = nome_grafico
            self.mw.arvore._selecionar_item_na_arvore(
                self.mw.estado.arquivo_ativo, nome_grafico
            )
            self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _abrir_janela_sobreposicao(self):
        """Abre janela para selecionar gráficos a sobrepor"""
        # Coleta todos os gráficos disponíveis
        graficos_disponiveis = []

        for nome_arquivo in self.mw.estado.get_graficos():
            for nome_grafico in self.mw.estado.get_graficos()[nome_arquivo]:
                if self.mw.estado.get_graficos()[nome_arquivo][nome_grafico].get(
                    "hidden", False
                ):
                    continue
                graficos_disponiveis.append(
                    {
                        "arquivo": nome_arquivo,
                        "grafico": nome_grafico,
                        "label": f"{nome_arquivo} → {nome_grafico}",
                    }
                )

        if len(graficos_disponiveis) < 2:
            QMessageBox.warning(
                self.mw,
                "Gráficos Insuficientes",
                "É necessário ter pelo menos 2 gráficos criados para sobrepor.",
            )
            return

        # Abre janela de seleção
        janela = JanelaSobreporGraficos(graficos_disponiveis, self.mw)
        if janela.exec() == QDialog.DialogCode.Accepted:
            selecionados = janela.get_selecionados()
            nome_combinacao = janela.get_nome()

            # Nome genérico se o usuário não digitou
            if not nome_combinacao:
                i = 1
                while f"Sobreposicao{i}" in self.mw.estado.get_sobreposicoes():
                    i += 1
                nome_combinacao = f"Sobreposicao{i}"

            if len(selecionados) < 2:
                QMessageBox.warning(
                    self.mw, "Seleção Inválida", "Selecione pelo menos 2 gráficos."
                )
                return

            # Verifica conflito
            unidades_x_unicas = set()
            unidades_y_unicas = set()
            for ref in selecionados:
                arq = ref["arquivo"]
                graf = ref["grafico"]
                if graf in self.mw.estado.get_graficos().get(arq, {}):
                    config = self.mw.estado.get_graficos()[arq][graf]
                    unidades_x_unicas.add(config.get("unidade_x", ""))
                    unidades_y_unicas.add(config.get("unidade_y", ""))

            tendencia_visual = False
            if (
                len(unidades_x_unicas) > 2
                or len(unidades_y_unicas) > 2
                or (len(unidades_x_unicas) > 1 and len(unidades_y_unicas) > 1)
            ):
                msg_box = QMessageBox(self.mw)
                msg_box.setWindowTitle("Incompatibilidade de Unidades Detectada")
                msg_box.setText(
                    "Os sinais selecionados possuem unidades divergentes em múltiplos eixos.\n\n"
                    "Recomendação: Para evitar distorções, utilize o modo de exibicao simultanea para analisar os gráficos.\n\n"
                    "Deseja gerar uma Tendência Visual mesmo assim (sem rótulos dimensionais)?"
                )

                try:
                    btn_sim = msg_box.addButton(
                        "Sobrepor mesmo assim", QMessageBox.ButtonRole.AcceptRole
                    )
                    msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
                except Exception:
                    btn_sim = msg_box.addButton(
                        "Sobrepor mesmo assim", QMessageBox.AcceptRole
                    )
                    msg_box.addButton("Cancelar", QMessageBox.RejectRole)

                msg_box.exec()

                if msg_box.clickedButton() == btn_sim:
                    tendencia_visual = True
                else:
                    return

            # Cria a sobreposição
            self._criar_grafico_sobreposto(
                selecionados, nome_combinacao, tendencia_visual=tendencia_visual
            )

    def _abrir_janela_exibicao_simultanea(self):
        """Abre janela para selecionar gráficos e configurar exibição simultânea."""
        # Coleta todos os gráficos disponíveis
        graficos_disponiveis = []

        for nome_arquivo in self.mw.estado.get_graficos():
            for nome_grafico in self.mw.estado.get_graficos()[nome_arquivo]:
                if self.mw.estado.get_graficos()[nome_arquivo][nome_grafico].get(
                    "hidden", False
                ):
                    continue
                graficos_disponiveis.append(
                    {
                        "arquivo": nome_arquivo,
                        "grafico": nome_grafico,
                        "label": f"{nome_arquivo} → {nome_grafico}",
                    }
                )

        if len(graficos_disponiveis) < 2:
            QMessageBox.warning(
                self.mw,
                "Gráficos Insuficientes",
                "É necessário ter pelo menos 2 gráficos criados para exibição simultânea.",
            )
            return

        janela = JanelaExibicaoSimultanea(graficos_disponiveis, self.mw)
        if janela.exec() == QDialog.DialogCode.Accepted:
            nome_analise = janela.get_nome()
            layout_config = janela.get_layout_config()

            # Nome genérico se o usuário não digitou
            if not nome_analise:
                i = 1
                while f"Exibicao{i}" in self.mw.estado.get_exibicoes_simultaneas():
                    i += 1
                nome_analise = f"Exibicao{i}"

            # Salvar a configuração
            self.mw.estado.get_exibicoes_simultaneas()[nome_analise] = {
                "layout": layout_config,
                "tipo": "ExibicaoSimultanea",
            }

            # Adicionar na nova árvore (isso reconstrói a árvore de composições)
            self.mw.arvore._atualizar_arvore_composicoes()

            # Exibe na janela principal
            self.mw.estado.arquivo_ativo = None
            self.mw.estado.grafico_ativo = nome_analise
            self.mw.arvore._selecionar_item_composicao(nome_analise)
            self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _abrir_editar_exibicao_simultanea(self, item):
        """Abre janela de edição para composições de exibição simultânea."""
        nome_atual = item.text(0)

        if nome_atual not in self.mw.estado.get_exibicoes_simultaneas():
            QMessageBox.warning(self.mw, "Aviso", "Composição não encontrada.")
            return

        config = self.mw.estado.get_exibicoes_simultaneas()[nome_atual]

        janela = JanelaEditarExibicaoSimultanea(nome_atual, config, self.mw)
        if janela.exec() == QDialog.DialogCode.Accepted:
            janela.aplicar_alteracoes()

            novo_nome = janela.get_novo_nome()
            if novo_nome and novo_nome != nome_atual:
                # Verifica se o novo nome já existe
                if (
                    novo_nome in self.mw.estado.get_exibicoes_simultaneas()
                    or novo_nome in self.mw.estado.get_sobreposicoes()
                ):
                    QMessageBox.warning(
                        self.mw,
                        "Nome Inválido",
                        f"Já existe uma composição chamada '{novo_nome}'.",
                    )
                else:
                    # Renomeia no dicionário
                    self.mw.estado.get_exibicoes_simultaneas()[
                        novo_nome
                    ] = self.mw.estado.get_exibicoes_simultaneas().pop(nome_atual)

                    # Atualiza na árvore
                    item.setText(0, novo_nome)

                    # Atualiza referência ativa
                    if self.mw.estado.grafico_ativo == nome_atual:
                        self.mw.estado.grafico_ativo = novo_nome

            self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _criar_grafico_sobreposto(
        self, graficos_selecionados, nome_combinacao, tendencia_visual=False
    ):
        """Cria dados do gráfico combinado"""

        # Cria estrutura de dados
        dados_combinado = {
            "tipo": "Sobreposto",
            "titulo": nome_combinacao,
            "graficos_fonte": graficos_selecionados,  # ← Lista de dicts
            "tendencia_visual": tendencia_visual,
        }

        # Salva no dicionário
        self.mw.estado.get_sobreposicoes()[nome_combinacao] = dados_combinado

        # Reconstrói a lista e seleciona o item
        self.mw.arvore._atualizar_arvore_composicoes()

        self.mw.estado.arquivo_ativo = None  # Não tem arquivo pai
        self.mw.estado.grafico_ativo = nome_combinacao
        self.mw.arvore._selecionar_item_composicao(nome_combinacao)
        self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _abrir_janela_ajustes(self, item):
        """Prepara os dados e abre a janela de Ajustes de Exibição"""

        # Determina o gráfico clicado e constrói a lista de configurações fonte
        graficos_fonte = []
        configs_originais = []  # configs reais dos gráficos (para editar referências)

        # É uma composição de visualização (Sobreposição)
        if item.treeWidget() == self.mw.tree_composicoes:
            nome_grafico = item.text(0)
            if nome_grafico in self.mw.estado.get_sobreposicoes():
                graficos_fonte = self.mw.estado.get_sobreposicoes()[nome_grafico].get(
                    "graficos_fonte", []
                )
                # Resolve configs originais para poder editar referências
                for ref in graficos_fonte:
                    arq = ref.get("arquivo", "")
                    graf = ref.get("grafico", "")
                    if graf in self.mw.estado.get_graficos().get(arq, {}):
                        configs_originais.append(
                            self.mw.estado.get_graficos()[arq][graf]
                        )

        # É um gráfico normal (e.g. abaixo de um arquivo)
        elif item.parent() is not None:
            nome_arquivo = self.mw._get_arquivo_nome(item)
            nome_grafico = item.text(0)

            if (
                nome_arquivo in self.mw.estado.get_graficos()
                and nome_grafico in self.mw.estado.get_graficos()[nome_arquivo]
            ):
                config = self.mw.estado.get_graficos()[nome_arquivo][nome_grafico]
                graficos_fonte = [config]  # Único item
                configs_originais = [config]

        if not graficos_fonte:
            QMessageBox.warning(
                self.mw,
                "Aviso",
                "Não foi possível carregar as configurações deste gráfico.",
            )
            return

        nome_atual_grafico = item.text(0)

        # Abre a janela passando a referência aos dicts (assim altera dinamicamente)
        # Para sobreposições, passa configs_originais separadamente para editar referências
        janela = JanelaAjustesExibicao(
            graficos_fonte,
            nome_atual_grafico,
            self.mw,
            configs_originais=configs_originais,
        )
        if janela.exec() == QDialog.DialogCode.Accepted:
            novo_nome = janela.get_novo_nome()
            if novo_nome and novo_nome != nome_atual_grafico:
                if item.treeWidget() == self.mw.tree_composicoes:
                    nome_arquivo = None
                else:
                    nome_arquivo = self.mw._get_arquivo_nome(item)

                sucesso = self.mw.estado._executar_renomeacao(
                    nome_atual_grafico, novo_nome, nome_arquivo
                )
                if sucesso:
                    item.setText(0, novo_nome)

            janela.aplicar_alteracoes()
            self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _adicionar_linha_referencia(self, item):
        from processamento.operacoes import calcular_linha_referencia

        CORES_REFERENCIA = ["r", "g", "c", "m", "y"]

        nome_arquivo = self.mw._get_arquivo_nome(item)
        nome_grafico = item.text(0)

        config_original = self.mw.estado.get_graficos()[nome_arquivo][nome_grafico]
        linhas_existentes = config_original.get("linhas_referencia", [])

        if len(linhas_existentes) >= 5:
            QMessageBox.warning(
                self.mw,
                "Limite Atingido",
                "Cada gráfico pode ter no máximo 5 linhas de referência.",
            )
            return

        df = self.mw.estado.get_arquivos()[nome_arquivo]["dataframe"]
        dados_x = df[config_original["eixo_x"]]

        dialog = JanelaLinhaReferencia(self.mw)
        try:
            resultado = dialog.exec_()
        except AttributeError:
            resultado = dialog.exec()

        if resultado:
            titulo = dialog.get_titulo()
            nomes_existentes = [lr["titulo"] for lr in linhas_existentes]

            if not titulo:
                contador = 1
                while f"Polinômio {contador}" in nomes_existentes:
                    contador += 1
                titulo = f"Polinômio {contador}"

            coeficientes = dialog.get_coeficientes()
            dados_y, _ = calcular_linha_referencia(dados_x, coeficientes)

            # Verifica nome duplicado
            if titulo in nomes_existentes:
                QMessageBox.warning(
                    self.mw,
                    "Nome Duplicado",
                    f"Já existe uma referência chamada '{titulo}' neste gráfico.",
                )
                return

            cor = CORES_REFERENCIA[len(linhas_existentes) % len(CORES_REFERENCIA)]

            nova_ref = {
                "titulo": titulo,
                "dados_y": dados_y,
                "coeficientes": coeficientes,
                "cor": cor,
                "ativo": True,
            }

            if "linhas_referencia" not in config_original:
                config_original["linhas_referencia"] = []
            config_original["linhas_referencia"].append(nova_ref)

            # Atualiza display
            if (
                self.mw.estado.arquivo_ativo == nome_arquivo
                and self.mw.estado.grafico_ativo == nome_grafico
            ):
                self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _toggle_referencia(self, item, idx):
        # interruptor (liga/desliga) para ocultar ou mostrar uma linha que foi adicionada
        nome_arquivo = self.mw._get_arquivo_nome(item)
        nome_grafico = item.text(0)
        config = self.mw.estado.get_graficos()[nome_arquivo][nome_grafico]

        linhas = config.get("linhas_referencia", [])
        if 0 <= idx < len(linhas):
            linhas[idx]["ativo"] = not linhas[idx].get("ativo", True)

        if (
            self.mw.estado.arquivo_ativo == nome_arquivo
            and self.mw.estado.grafico_ativo == nome_grafico
        ):
            self.mw.exibidor_graficos._exibir_grafico_selecionado()

    def _excluir_referencias(self, item):
        """Abre diálogo para selecionar quais referências excluir."""
        nome_arquivo = self.mw._get_arquivo_nome(item)
        nome_grafico = item.text(0)
        config = self.mw.estado.get_graficos()[nome_arquivo][nome_grafico]

        linhas = config.get("linhas_referencia", [])
        if not linhas:
            return

        janela = JanelaExcluirReferencias(linhas, self.mw)
        if janela.exec() == QDialog.DialogCode.Accepted:
            indices_remover = janela.get_indices_remover()
            for i in reversed(indices_remover):
                linhas.pop(i)

            if (
                self.mw.estado.arquivo_ativo == nome_arquivo
                and self.mw.estado.grafico_ativo == nome_grafico
            ):
                self.mw.exibidor_graficos._exibir_grafico_selecionado()
