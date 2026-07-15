import traceback
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from arquivos.projeto.gerenciadorSAS import GerenciadorSAS


def carregar_emt(main_window):
    if len(main_window.estado.guarda_arquivos) >= 50:
        QMessageBox.warning(
            main_window,
            "Limite Atingido",
            "Você atingiu o limite de 50 arquivos abertos simultaneamente.",
        )
        return

    df, conteudo, cabecalho = main_window.leitorEMT.extrai_infos()

    if df is not None:
        nome = conteudo["nome_arqv"]

        if nome in main_window.estado.guarda_arquivos:
            QMessageBox.warning(
                main_window, "Arquivo Duplicado", f"O arquivo '{nome}' já está aberto."
            )
            return

        main_window.estado.guarda_arquivos[nome] = {
            "dataframe_original": df.copy(),
            "dataframe": df,
            "conteudo": conteudo,
            "cabecalho": cabecalho,
            "pipeline": [],
            "colunas_modificadas": set(),
            "unidades_colunas": {},
        }
        main_window.estado.guarda_graficos[nome] = {}
        main_window.arquivo_ativo = nome
        main_window.arvore._adicionar_arquivo(nome)


def carregar_tdf(main_window):
    if len(main_window.estado.guarda_arquivos) >= 50:
        QMessageBox.warning(
            main_window,
            "Limite Atingido",
            "Você atingiu o limite de 50 arquivos abertos simultaneamente.",
        )
        return

    try:
        df, conteudo, cabecalho, unidades_colunas = main_window.leitorTDF.extrai_infos()
    except ValueError:
        QMessageBox.warning(
            main_window,
            "Aviso",
            "Não foram identificados dados 3D, EMG ou de Plataforma de Força.",
        )
        return

    if df is not None:
        nome = conteudo["nome_arqv"]

        if nome in main_window.estado.guarda_arquivos:
            QMessageBox.warning(
                main_window, "Arquivo Duplicado", f"O arquivo '{nome}' já está aberto."
            )
            return

        main_window.estado.guarda_arquivos[nome] = {
            "dataframe_original": df.copy(),
            "dataframe": df,
            "conteudo": conteudo,
            "cabecalho": cabecalho,
            "pipeline": [],
            "colunas_modificadas": set(),
            "unidades_colunas": unidades_colunas or {},
        }
        main_window.estado.guarda_graficos[nome] = {}
        main_window.arquivo_ativo = nome
        main_window.arvore._adicionar_arquivo(nome)
        main_window._resetar_interface()


def salvar_projeto_sas(main_window):
    caminho_arquivo, _ = QFileDialog.getSaveFileName(
        main_window, "Salvar Projeto", "", "Projeto SAS (*.sas)"
    )
    if caminho_arquivo:
        if not caminho_arquivo.endswith(".sas"):
            caminho_arquivo += ".sas"
        try:
            GerenciadorSAS.salvar_projeto(
                caminho_arquivo,
                main_window.estado.guarda_arquivos,
                main_window.estado.guarda_graficos,
                main_window.estado.guarda_sobreposicoes,
                main_window.estado.guarda_exibicoes_simultaneas,
            )
            QMessageBox.information(
                main_window, "Sucesso", "Projeto salvo com sucesso!"
            )
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(main_window, "Erro", f"Erro ao salvar projeto:\n{e}")


def abrir_projeto_sas(main_window):
    caminho_arquivo, _ = QFileDialog.getOpenFileName(
        main_window, "Abrir Projeto", "", "Projeto SAS (*.sas)"
    )
    if caminho_arquivo:
        try:
            ga, gg, gs, ges = GerenciadorSAS.abrir_projeto(caminho_arquivo)

            # Mesclar arquivos e tratar colisões de nomes
            mapeamento_nomes = {}
            for nome, dados in ga.items():
                novo_nome = nome
                contador = 1
                while novo_nome in main_window.estado.guarda_arquivos:
                    novo_nome = f"{nome}_{contador}"
                    contador += 1

                mapeamento_nomes[nome] = novo_nome
                main_window.estado.guarda_arquivos[novo_nome] = dados
                main_window.arvore._adicionar_arquivo(novo_nome)

                if nome in gg:
                    main_window.estado.guarda_graficos[novo_nome] = gg[nome]
                    for nome_grafico in main_window.estado.guarda_graficos[novo_nome]:
                        config = main_window.estado.guarda_graficos[novo_nome][
                            nome_grafico
                        ]
                        if not config.get("hidden", False):
                            main_window.arvore._adicionar_grafico_na_arvore_de_arquivo(
                                novo_nome, nome_grafico
                            )

            # Mesclar sobreposições atualizando referências internas
            for nome, config in gs.items():
                novo_nome = nome
                contador = 1
                while (
                    novo_nome in main_window.estado.guarda_sobreposicoes
                    or novo_nome in main_window.estado.guarda_exibicoes_simultaneas
                ):
                    novo_nome = f"{nome}_{contador}"
                    contador += 1

                if "graficos_fonte" in config:
                    for ref in config["graficos_fonte"]:
                        if ref["arquivo"] in mapeamento_nomes:
                            ref["arquivo"] = mapeamento_nomes[ref["arquivo"]]

                main_window.estado.guarda_sobreposicoes[novo_nome] = config

            # Mesclar exibições simultâneas atualizando referências internas
            for nome, config in ges.items():
                novo_nome = nome
                contador = 1
                while (
                    novo_nome in main_window.estado.guarda_sobreposicoes
                    or novo_nome in main_window.estado.guarda_exibicoes_simultaneas
                ):
                    novo_nome = f"{nome}_{contador}"
                    contador += 1

                if "layout" in config:
                    for row in config["layout"]:
                        for ref in row:
                            if ref is not None and ref["arquivo"] in mapeamento_nomes:
                                ref["arquivo"] = mapeamento_nomes[ref["arquivo"]]

                main_window.estado.guarda_exibicoes_simultaneas[novo_nome] = config

            main_window.arvore._atualizar_arvore_composicoes()
            QMessageBox.information(
                main_window, "Sucesso", "Projeto carregado com sucesso!"
            )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(main_window, "Erro", f"Erro ao abrir projeto:\n{e}")
        main_window._resetar_interface()
