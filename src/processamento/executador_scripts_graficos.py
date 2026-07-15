import pandas as pd
import copy
from PyQt6.QtWidgets import QMessageBox


def executar_script_grafico(
    estado, main_window, nome_script, nome_arquivo, nome_grafico, silencioso=False
):
    script = estado.guarda_scripts_graficos.get(nome_script)
    if not script:
        return

    arq_data = estado.guarda_arquivos.get(nome_arquivo)
    if not arq_data:
        return

    df = arq_data["dataframe"]
    config_orig = estado.guarda_graficos.get(nome_arquivo, {}).get(nome_grafico)
    if not config_orig:
        return

    titulo_script = script.get("acoes", {}).get("titulo", "")
    if not titulo_script:
        titulo_script = nome_script

    novo_nome_grafico = f"{nome_grafico}_{titulo_script}"
    contador = 1
    while novo_nome_grafico in estado.guarda_graficos.get(nome_arquivo, {}):
        novo_nome_grafico = f"{nome_grafico}_{titulo_script}_{contador}"
        contador += 1

    config_novo = {}
    for k, v in config_orig.items():
        if k != "arvore":
            config_novo[k] = copy.deepcopy(v)

    eixo_y = config_novo.get("eixo_y")
    if "dados_y_calc" in config_novo and config_novo["dados_y_calc"] is not None:
        y_data = pd.Series(config_novo["dados_y_calc"], index=df.index)
    else:
        if eixo_y in df.columns:
            y_data = df[eixo_y].copy()
        else:
            QMessageBox.warning(
                main_window,
                "Aviso",
                f"{nome_arquivo} | {nome_grafico} : Variável Y '{eixo_y}' não encontrada no arquivo.",
            )
            return

    acoes = script.get("acoes", {})

    try:
        # 1. Filtros
        for f_op in acoes.get("filtros", []):
            tipo = f_op.get("tipo", "passa_baixa")
            fc = f_op.get("fc", 10.0)
            ordem = f_op.get("ordem", 4)
            retificar = f_op.get("retificar", False)
            fc_manual = f_op.get("fc_manual", True)

            fs = None
            if "informacoes" in estado.guarda_arquivos.get(nome_arquivo, {}):
                freq = estado.guarda_arquivos[nome_arquivo]["informacoes"].get(
                    "Frequência de Amostragem"
                )
                if freq:
                    try:
                        fs = float(freq)
                    except ValueError:
                        pass
            if not fs:
                eixo_x = config_novo.get("eixo_x")
                if eixo_x in df.columns:
                    from processamento.limpeza import calcular_fs

                    fs = calcular_fs(df[eixo_x].values)

            if not fs or fs <= 0:
                raise ValueError(
                    "Frequência de amostragem (fs) não pôde ser calculada automaticamente. Verifique se o eixo X está em segundos."
                )
            if retificar and tipo == "passa_baixa":
                y_data = y_data.abs()

            if not fc_manual:
                from processamento.limpeza import calcular_fc_winter

                fc, _, _ = calcular_fc_winter(y_data.values, fs, order=ordem)

            nyq = 0.5 * fs
            normal_cutoff = fc / nyq
            if normal_cutoff >= 1.0:
                raise ValueError(
                    f"Frequência de corte ({fc}Hz) é maior ou igual à frequência de Nyquist ({nyq}Hz)."
                )

            from scipy.signal import butter, filtfilt

            b, a = butter(
                ordem,
                normal_cutoff,
                btype="low" if tipo == "passa_baixa" else "high",
                analog=False,
            )

            mask = y_data.notna()
            if not mask.all():
                y_filled = y_data.interpolate(method="linear").bfill().ffill()
            else:
                y_filled = y_data

            y_filt = filtfilt(b, a, y_filled.values)
            y_data = pd.Series(y_filt, index=df.index)

        # 2. Interpolações
        for i_op in acoes.get("interpolacoes", []):
            if y_data.isna().sum() == 0:
                continue

            metodo = i_op.get("metodo", "linear")
            if metodo == "linear":
                y_data = y_data.interpolate(method="linear")
            elif metodo == "spline":
                y_data = y_data.interpolate(method="spline", order=3)
            elif metodo == "média":
                y_data = y_data.fillna(y_data.mean())

        # 3. Offsets
        for o_op in acoes.get("offsets", []):
            valor = o_op.get("valor", 0.0)
            nova_var = o_op.get("nova_var", False)
            nome_nova = o_op.get("nome_nova_var", "")

            # Offset = subtração do valor (como na JanelaOffset original)
            y_data = y_data - valor

            if nova_var and nome_nova:
                if nome_nova in df.columns:
                    res = QMessageBox.question(
                        main_window,
                        "Aviso",
                        f"{nome_arquivo} | {nome_grafico} : A variável '{nome_nova}' já existe.\nDeseja sobrescrevê-la?",
                    )
                    if res != QMessageBox.StandardButton.Yes:
                        return
                df[nome_nova] = y_data
                arq_data["unidades_colunas"][nome_nova] = arq_data[
                    "unidades_colunas"
                ].get(eixo_y, "")
                config_novo["eixo_y"] = nome_nova
                # Como criamos no df definitivo, podemos limpar os dados_y_calc se quisermos, mas a cascata pode precisar.

        # 4. Polinômios de Referência
        for p_op in acoes.get("polinomios", []):
            if "linhas_referencia" not in config_novo:
                config_novo["linhas_referencia"] = []

            titulo_pol = p_op.get("titulo", "")
            if not titulo_pol:
                contador_pol = len(config_novo["linhas_referencia"]) + 1
                titulo_pol = f"Polinômio {contador_pol}"

            config_novo["linhas_referencia"].append(
                {
                    "titulo": titulo_pol,
                    "coeficientes": p_op.get("coeficientes", []),
                    "cor": "g",
                    "ativo": True,
                }
            )

    except Exception as e:
        QMessageBox.warning(
            main_window,
            "Erro",
            f"{nome_arquivo} | {nome_grafico} : Ocorreu um erro durante a execução do script:\n{e}",
        )
        return

    # Finalizando
    if (
        "dados_y_calc" in config_novo
        or acoes.get("filtros")
        or acoes.get("interpolacoes")
        or (
            acoes.get("offsets")
            and not any(o.get("nova_var") for o in acoes.get("offsets", []))
        )
    ):
        config_novo["dados_y_calc"] = y_data.values.tolist()

    historico = config_novo.get("pipeline_grafico", [])
    if not historico and "pipeline_colunas" in estado.guarda_arquivos.get(
        nome_arquivo, {}
    ):
        eixo_y_graf = config_novo.get("eixo_y")
        if eixo_y_graf:
            historico = estado.guarda_arquivos[nome_arquivo]["pipeline_colunas"].get(
                eixo_y_graf, []
            )
    historico = copy.deepcopy(historico)
    for f in acoes.get("filtros", []):
        f_copy = copy.deepcopy(f)
        f_copy["tipo_operacao"] = "filtro"
        historico.append(f_copy)
    for i in acoes.get("interpolacoes", []):
        i_copy = copy.deepcopy(i)
        i_copy["tipo_operacao"] = "interpolacao"
        historico.append(i_copy)
    for o in acoes.get("offsets", []):
        o_copy = copy.deepcopy(o)
        o_copy["tipo_operacao"] = "offset"
        historico.append(o_copy)
    config_novo["pipeline_grafico"] = historico

    estado.guarda_graficos[nome_arquivo][novo_nome_grafico] = config_novo
    main_window.arvore._adicionar_grafico_na_arvore_de_arquivo(
        nome_arquivo, novo_nome_grafico
    )

    # Atualiza o painel
    main_window.arvore._selecionar_item_na_arvore(nome_arquivo, novo_nome_grafico)
    main_window.exibidor_graficos._exibir_grafico_selecionado()
    if not silencioso:
        QMessageBox.information(
            main_window,
            "Sucesso",
            f"Script '{nome_script}' aplicado com sucesso ao gráfico '{nome_grafico}'!",
        )
    return True
