import os
import tempfile
import zipfile
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt6.QtGui import QPdfWriter, QPainter, QPageSize, QPageLayout
from PyQt6.QtCore import QMarginsF, QRect, Qt
from processamento.informacoes_curvas import AnaliseCurva
from processamento.limpeza import recomputar_dados_com_filtros


def exportar_graficos(main_window, selecionados, formato):
    # Preparar caminhos
    extensao = f".{formato.lower()}"
    caminho_salvar, _ = QFileDialog.getSaveFileName(
        main_window, f"Salvar {formato}", "", f"Arquivo {formato} (*{extensao})"
    )
    if not caminho_salvar:
        return

    if not caminho_salvar.lower().endswith(extensao):
        caminho_salvar += extensao

    try:
        # Diretório temporário para gerar os arquivos se for ZIP
        with tempfile.TemporaryDirectory() as tmpdirname:
            path_pdf = (
                caminho_salvar
                if formato == "PDF"
                else os.path.join(tmpdirname, "graficos.pdf")
            )
            path_txt = (
                caminho_salvar
                if formato == "TXT"
                else os.path.join(tmpdirname, "informacoes.txt")
            )

            # Gerar PDF
            if formato in ["PDF", "ZIP"]:
                # Salva o estado atual
                arquivo_ativo_antigo = main_window.estado.arquivo_ativo
                grafico_ativo_antigo = main_window.estado.grafico_ativo

                pixmaps = []
                for item in selecionados:
                    if item["tipo_item"] == "normal":
                        main_window.estado.arquivo_ativo = item["arquivo"]
                        main_window.estado.grafico_ativo = item["grafico"]
                    elif item["tipo_item"] in ["sobreposicao", "simultanea"]:
                        main_window.estado.arquivo_ativo = None
                        main_window.estado.grafico_ativo = item["grafico"]

                    # Força exibição na UI para capturar a imagem
                    main_window.exibidor_graficos._exibir_grafico_selecionado()
                    QApplication.processEvents()

                    if item["tipo_item"] == "simultanea":
                        pixmaps.append(main_window.area_simultanea.grab())
                    else:
                        pixmaps.append(main_window.area_grafico.grab())

                # Restaura o estado antigo
                main_window.estado.arquivo_ativo = arquivo_ativo_antigo
                main_window.estado.grafico_ativo = grafico_ativo_antigo
                main_window.exibidor_graficos._exibir_grafico_selecionado()
                QApplication.processEvents()

                if pixmaps:
                    pdf_writer = QPdfWriter(path_pdf)
                    pdf_writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                    pdf_writer.setPageOrientation(QPageLayout.Orientation.Landscape)
                    pdf_writer.setPageMargins(
                        QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter
                    )
                    pdf_writer.setResolution(300)

                    painter = QPainter(pdf_writer)
                    for i, pix in enumerate(pixmaps):
                        if i > 0:
                            pdf_writer.newPage()

                        # Ajusta a imagem para caber na página e centraliza
                        w_pdf = pdf_writer.width()
                        h_pdf = pdf_writer.height()

                        size_img = pix.size()
                        size_img.scale(w_pdf, h_pdf, Qt.AspectRatioMode.KeepAspectRatio)

                        x_pos = int((w_pdf - size_img.width()) / 2)
                        y_pos = int((h_pdf - size_img.height()) / 2)

                        painter.drawPixmap(
                            QRect(x_pos, y_pos, size_img.width(), size_img.height()),
                            pix,
                            pix.rect(),
                        )

                    painter.end()

            # Gerar TXT
            if formato in ["TXT", "ZIP"]:
                linhas_txt = []
                for item in selecionados:
                    if item["tipo_item"] == "normal":
                        nome_arq = item["arquivo"]
                        nome_graf = item["grafico"]
                        config = main_window.estado.get_config_grafico(
                            nome_arq, nome_graf
                        )
                        df = main_window.estado.get_dataframe(nome_arq)

                        dados_x = df[config["eixo_x"]]
                        if "dados_y_calc" in config:
                            dados_y = config["dados_y_calc"]
                        else:
                            dados_y = df[config["eixo_y"]]

                        filtros = config.get("filtros_ativos", [])
                        filtros_ativos = [f for f in filtros if f.get("ativo", True)]
                        if filtros_ativos:
                            dados_y = recomputar_dados_com_filtros(
                                dados_x, dados_y, filtros_ativos
                            )

                        analise = AnaliseCurva(dados_x, dados_y)
                        info = analise.resumo()

                        def fmt(val, decimais=4):
                            return f"{val:.{decimais}f}" if val is not None else "N/A"

                        unidades = main_window.estado.get_unidades_colunas(nome_arq)
                        un_x = config.get("unidade_x") or unidades.get(
                            config["eixo_x"], ""
                        )
                        un_y = config.get("unidade_y") or unidades.get(
                            config["eixo_y"], ""
                        )

                        linhas_txt.append(
                            f"--- Gráfico: {nome_graf} (Arquivo: {nome_arq}) ---\n"
                        )
                        linhas_txt.append(f"Eixo X: {config.get('eixo_x', '')}")
                        linhas_txt.append(f"  Valor Mínimo: {fmt(info['x_minimo'])}")
                        linhas_txt.append(f"  Valor Máximo: {fmt(info['x_maximo'])}\n")
                        linhas_txt.append(f"Eixo Y: {config.get('eixo_y', '')}")
                        linhas_txt.append(
                            f"  Valor Mínimo: {fmt(info['valor_minimo'])} (X = {fmt(info['x_no_minimo'])} {un_x})"
                        )
                        linhas_txt.append(
                            f"  Valor Máximo: {fmt(info['valor_maximo'])} (X = {fmt(info['x_no_maximo'])} {un_x})"
                        )
                        linhas_txt.append(f"  Amplitude: {fmt(info['amplitude'])}")
                        if info.get("rms") is not None:
                            linhas_txt.append(
                                f"  RMS (Root Mean Square): {fmt(info['rms'])}"
                            )
                        linhas_txt.append("")
                        linhas_txt.append(
                            f"Pico Máximo Global: {fmt(info['valor_maximo'])} (X = {fmt(info['x_no_maximo'])} {un_x})"
                        )
                        linhas_txt.append(
                            f"Pico Mínimo Global: {fmt(info['valor_minimo'])} (X = {fmt(info['x_no_minimo'])} {un_x})\n"
                        )

                        fs = info.get("taxa_amostragem")
                        linhas_txt.append(
                            f"Taxa de Amostragem: {fmt(fs, 2) + ' Hz' if fs is not None else 'N/A'}"
                        )
                        linhas_txt.append(
                            f"Amostras Válidas: {info['amostras_validas']} / {info['total_amostras']}"
                        )
                        linhas_txt.append("\n\n")

                if linhas_txt:
                    with open(path_txt, "w", encoding="utf-8") as f:
                        f.write("\n".join(linhas_txt))
                elif formato == "TXT":
                    QMessageBox.warning(
                        main_window,
                        "Aviso",
                        "Nenhum gráfico normal selecionado. O TXT ficaria vazio.",
                    )
                    return

            # Gerar ZIP
            if formato == "ZIP":
                with zipfile.ZipFile(caminho_salvar, "w", zipfile.ZIP_DEFLATED) as zipf:
                    if os.path.exists(path_pdf):
                        zipf.write(path_pdf, arcname="graficos.pdf")
                    if os.path.exists(path_txt):
                        zipf.write(path_txt, arcname="informacoes.txt")

        QMessageBox.information(
            main_window, "Sucesso", f"Exportação para {formato} concluída com sucesso!"
        )

    except Exception as e:
        QMessageBox.critical(main_window, "Erro", f"Erro ao exportar: {e}")
