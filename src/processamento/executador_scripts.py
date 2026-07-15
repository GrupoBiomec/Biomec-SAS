import pandas as pd
import copy
from PyQt6.QtWidgets import QMessageBox


def executar_script(estado, main_window, nome_script, nome_arquivo, silencioso=False):
    script = estado.guarda_scripts.get(nome_script)
    if not script:
        return

    arq_data = estado.guarda_arquivos.get(nome_arquivo)
    if not arq_data:
        return

    df = arq_data["dataframe"].copy()
    unidades = arq_data.get("unidades_colunas", {}).copy()
    pipeline = arq_data.get("pipeline", []).copy()

    acoes = script.get("acoes", {})

    # 1. Recorte Temporal
    if "recorte_temporal" in acoes:
        recorte = acoes["recorte_temporal"]
        modo = recorte["modo"]
        t_ini = recorte["inicio"]
        t_fim = recorte["fim"]
        deslocar_0 = recorte["deslocar_0"]

        # Encontrar coluna de tempo
        col_tempo = None
        for col in df.columns:
            if col.lower() in ["time", "tempo", "frame", "frames", "item"]:
                col_tempo = col
                break

        if modo == "tempo" and col_tempo:
            mask = (df[col_tempo] >= t_ini) & (df[col_tempo] <= t_fim)
            df = df[mask].copy()
            df.reset_index(drop=True, inplace=True)
        else:
            idx_ini = max(0, int(t_ini))
            idx_fim = min(len(df) - 1, int(t_fim))
            df = df.iloc[idx_ini : idx_fim + 1].copy()
            df.reset_index(drop=True, inplace=True)

        if len(df) == 0:
            QMessageBox.warning(
                main_window,
                "Aviso de Recorte",
                f"{nome_arquivo} : O recorte temporal falhou pois os limites selecionados ({t_ini} a {t_fim}) estão fora do alcance dos dados.\n\nA execução do script será abortada.",
            )
            return

        if deslocar_0 and len(df) > 0:
            for c in df.columns:
                if c.lower() in ["time", "tempo", "frame", "frames", "item"]:
                    df[c] = df[c] - df[c].iloc[0]

        pipeline.append(
            {
                "categoria": "Tratamento de Dados",
                "acao": "Recorte Temporal",
                "modo": modo,
                "inicio": t_ini,
                "fim": t_fim,
                "deslocar_0": deslocar_0,
            }
        )

    # 2. Operações em variáveis
    from processamento.operacoes import (
        operar_variaveis,
        operar_trigonometria,
        operar_calculo_escalar,
    )

    ops = acoes.get("operacoes", [])
    for op in ops:
        tipo = op["tipo"]
        nome_nova = op["nome_nova"]

        if nome_nova in df.columns:
            res = QMessageBox.question(
                main_window,
                "Aviso",
                f"{nome_arquivo} : A variável '{nome_nova}' já existe durante a execução.\nDeseja sobrescrevê-la?",
            )
            if res != QMessageBox.StandardButton.Yes:
                return  # Aborta

        try:
            if tipo == "Aritmética Básica":
                var_a = op["var_a"]
                operador = op["operador"]
                is_const_b = op.get("is_const_b", False)

                if var_a not in df.columns:
                    raise ValueError(f"Variável '{var_a}' não encontrada no arquivo.")

                if is_const_b:
                    valores_b = float(op.get("val_b", 0.0))
                    b_texto = str(valores_b)
                else:
                    var_b = op["var_b"]
                    if var_b not in df.columns:
                        raise ValueError(
                            f"Variável '{var_b}' não encontrada no arquivo."
                        )
                    valores_b = df[var_b]
                    b_texto = var_b

                mapa_op = {"+": 0, "-": 1, "*": 2, "/": 3}
                idx_op = mapa_op.get(operador, 0)

                resultado, erro = operar_variaveis(df[var_a], valores_b, idx_op)
                if erro:
                    raise ValueError(erro)

                df[nome_nova] = resultado

                # Unidades
                u_a = unidades.get(var_a, "")
                if is_const_b:
                    u_res = u_a
                else:
                    u_b = unidades.get(var_b, "")
                    if idx_op == 2 and u_a and u_b:
                        u_res = f"{u_a}*{u_b}"
                    elif idx_op == 3 and u_a and u_b:
                        u_res = f"{u_a}/{u_b}"
                    else:
                        u_res = u_a
                unidades[nome_nova] = u_res

                pipeline.append(
                    {
                        "categoria": "Operações e Atributos",
                        "acao": "Aritmética de Colunas",
                        "variavel_gerada": nome_nova,
                        "detalhe": f"{var_a} {operador} {b_texto}",
                    }
                )

            elif tipo == "Trigonometria":
                var = op["var"]
                if var not in df.columns:
                    raise ValueError(f"Variável angular '{var}' não encontrada.")

                operador = op["operador"]
                # O operador agora já vem como 'seno', 'cosseno' ou 'tangente'
                op_nome = (
                    operador if operador in ["seno", "cosseno", "tangente"] else "seno"
                )

                unidade_var = unidades.get(var, "rad")
                resultado, erro = operar_trigonometria(
                    df[var], op_nome, unidade=unidade_var
                )
                if erro:
                    raise ValueError(erro)

                df[nome_nova] = resultado
                unidades[nome_nova] = ""

                pipeline.append(
                    {
                        "categoria": "Operações e Atributos",
                        "acao": "Trigonometria",
                        "variavel_gerada": nome_nova,
                        "detalhe": f"{op_nome} de '{var}'",
                    }
                )

            elif tipo == "Cálculo e Funções Escalares":
                var_principal = op["var_principal"]
                var_tempo = op["var_tempo"]
                operador = op["operador"]

                if var_principal not in df.columns:
                    raise ValueError(
                        f"Variável principal '{var_principal}' não encontrada."
                    )

                precisa_x = operador in ["integral", "derivada_1", "derivada_2"]
                if precisa_x and var_tempo not in df.columns:
                    raise ValueError(f"Variável de tempo '{var_tempo}' não encontrada.")

                dados_x = (
                    df[var_tempo]
                    if (var_tempo and var_tempo in df.columns)
                    else pd.Series(df.index, index=df.index)
                )
                resultado, erro = operar_calculo_escalar(
                    dados_x, df[var_principal], operador
                )
                if erro:
                    raise ValueError(erro)

                df[nome_nova] = resultado
                u_p = unidades.get(var_principal, "")
                u_t = unidades.get(var_tempo, "") if precisa_x else ""

                if operador == "integral" and u_p and u_t:
                    u_res = f"{u_p}*{u_t}"
                elif "derivada" in operador and u_p and u_t:
                    u_res = f"{u_p}/{u_t}"
                elif operador == "inverso" and u_p:
                    u_res = f"1/{u_p}"
                elif operador == "raiz_quadrada" and u_p:
                    u_res = f"√({u_p})"
                else:
                    u_res = u_p
                unidades[nome_nova] = u_res

                pipeline.append(
                    {
                        "categoria": "Operações e Atributos",
                        "acao": "Cálculo Escalar",
                        "variavel_gerada": nome_nova,
                        "detalhe": f"{operador} de '{var_principal}'",
                    }
                )

            elif tipo == "Definir Ângulos":
                # Fica como placeholder. Caso o usuario tentar rodar:
                raise ValueError(
                    "Definir ângulos por script ainda não está suportado integralmente.\nPor favor, faça isso manualmente e tente rodar as outras ações em outro script."
                )

        except ValueError as e:
            res = QMessageBox.question(
                main_window,
                "Erro na Operação",
                f"{nome_arquivo} : Falha na operação '{tipo}' ({nome_nova}):\n{str(e)}\n\nDeseja ignorar este erro e CONTINUAR com o script?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res != QMessageBox.StandardButton.Yes:
                QMessageBox.information(
                    main_window,
                    "Abortado",
                    f"{nome_arquivo} : A execução do script foi cancelada e nenhuma alteração foi salva no arquivo.",
                )
                return False  # Abortar e não salvar

    # 3. Aplicar as alterações
    salvar_como_novo = script.get("salvar_como_novo", False)

    if salvar_como_novo:
        # Simplifica o nome do script para usar no nome do arquivo (remove espaços e caracteres especiais básicos)
        import re

        nome_script_limpo = re.sub(r"[^a-zA-Z0-9_\-]", "_", nome_script)
        novo_nome = f"{nome_arquivo}_{nome_script_limpo}"
        contador = 1
        while novo_nome in estado.guarda_arquivos:
            novo_nome = f"{nome_arquivo}_{nome_script_limpo}_{contador}"
            contador += 1

        estado.guarda_arquivos[novo_nome] = {
            "dataframe": df,
            "dataframe_original": df.copy(),
            "conteudo": copy.deepcopy(arq_data["conteudo"]),
            "cabecalho": copy.deepcopy(arq_data["cabecalho"]),
            "unidades_colunas": unidades,
            "pipeline": pipeline,
            "colunas_modificadas": set(),
        }
        estado.guarda_arquivos[novo_nome]["conteudo"]["nome_arqv"] = novo_nome
        estado.guarda_graficos[novo_nome] = {}

        item = main_window.arvore._adicionar_arquivo(novo_nome)
        main_window.tree.setCurrentItem(item)
    else:
        # Se for substituir, precisamos também refletir nos arrays dos gráficos que dependem dessas linhas.
        if "recorte_temporal" in acoes:
            # Puxa lógica similar ao trim na main window para atualizar config['dados_y_calc']
            pass  # Por segurança, em scripts complexos deixaremos que o usuário refaça os gráficos ou implementaremos dps

        estado.guarda_arquivos[nome_arquivo]["dataframe"] = df
        estado.guarda_arquivos[nome_arquivo]["unidades_colunas"] = unidades
        estado.guarda_arquivos[nome_arquivo]["pipeline"] = pipeline

    # 4. Plotagem Automática
    if script.get("plotar_auto", False) or "graficos" in script.get("acoes", {}):
        arq_destino = novo_nome if salvar_como_novo else nome_arquivo

        if arq_destino not in estado.guarda_graficos:
            estado.guarda_graficos[arq_destino] = {}

        graficos_ops = script.get("acoes", {}).get("graficos", [])

        # Se a pessoa marcou o checkbox antigo, mas não preencheu o form novo, plotamos todas as vars geradas (legado)
        if script.get("plotar_auto", False) and not graficos_ops:
            col_tempo = None
            for col in df.columns:
                if col.lower() in ["time", "tempo", "frame", "frames", "item"]:
                    col_tempo = col
                    break
            eixo_x_padrao = col_tempo if col_tempo else df.columns[0]

            vars_geradas = [op["nome_nova"] for op in ops if "nome_nova" in op]
            for var in vars_geradas:
                if var in df.columns and var not in estado.guarda_graficos[arq_destino]:
                    graficos_ops.append(
                        {
                            "nome_grafico": var,
                            "tipo_grafico": "Linha",
                            "eixo_x": eixo_x_padrao,
                            "eixo_y": var,
                        }
                    )

        # Plota os gráficos definidos no novo form ou no legado
        for graf_op in graficos_ops:
            eixo_y = graf_op.get("eixo_y")
            if eixo_y in df.columns:
                nome_graf = graf_op.get("nome_grafico")

                # Garante nome unico no arquivo
                if nome_graf in estado.guarda_graficos[arq_destino]:
                    contador = 1
                    base_nome = nome_graf
                    while nome_graf in estado.guarda_graficos[arq_destino]:
                        nome_graf = f"{base_nome}_{contador}"
                        contador += 1

                eixo_x = graf_op.get("eixo_x")
                if eixo_x not in df.columns:
                    # Tenta achar um fallback sensato
                    eixo_x = df.columns[0]

                config = {
                    "tipo": graf_op.get("tipo_grafico", "Linha"),
                    "eixo_x": eixo_x,
                    "eixo_y": eixo_y,
                    "cor": "b",
                    "unidade_x": unidades.get(eixo_x, ""),
                    "unidade_y": unidades.get(eixo_y, ""),
                    "hidden": False,
                }
                estado.guarda_graficos[arq_destino][nome_graf] = config
                main_window.arvore._adicionar_grafico_na_arvore_de_arquivo(
                    arq_destino, nome_graf
                )

    if not silencioso:
        QMessageBox.information(
            main_window,
            "Sucesso",
            f"O script '{nome_script}' foi executado com sucesso.",
        )
    main_window.exibidor_graficos._exibir_grafico_selecionado()
    return True
