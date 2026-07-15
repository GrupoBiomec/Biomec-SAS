import time


class GerenciadorEstado:
    """Centraliza a lógica de negócios, cálculos e o estado principal da aplicação."""

    def __init__(self):
        self.guarda_arquivos = {}
        self.guarda_graficos = {}
        self.guarda_sobreposicoes = {}
        self.guarda_exibicoes_simultaneas = {}
        self.guarda_scripts = {}
        self.guarda_scripts_graficos = {}
        self.arquivo_ativo = None
        self.grafico_ativo = None

    def nome_existe(self, nome_arquivo, nome_grafico):
        return nome_grafico in self.guarda_graficos.get(nome_arquivo, {})

    def salvar_nova_variavel(self, resultado):
        """Salva uma nova variável gerada por operações matemáticas e atualiza o pipeline."""
        nome_arquivo = resultado["nome_arquivo"]
        nome_grafico = resultado["nome_grafico"]

        if nome_arquivo not in self.guarda_arquivos:
            self.guarda_arquivos[nome_arquivo] = {}
        if "pipeline" not in self.guarda_arquivos[nome_arquivo]:
            self.guarda_arquivos[nome_arquivo]["pipeline"] = []

        self.guarda_arquivos[nome_arquivo]["pipeline"].append(
            {
                "operacao": resultado["descricao"],
                "grafico": nome_grafico,
                "coluna": resultado["coluna"],
                "timestamp": time.time(),
                "arquivo": nome_arquivo,
            }
        )

        if nome_arquivo not in self.guarda_graficos:
            self.guarda_graficos[nome_arquivo] = {}

        self.guarda_graficos[nome_arquivo][nome_grafico] = resultado["config"]
        return True

    def exportar_pipeline(self, nome_arquivo):
        """Retorna uma string contendo o histórico de operações de um arquivo."""
        pipeline = self.guarda_arquivos.get(nome_arquivo, {}).get("pipeline", [])
        if not pipeline:
            return "Nenhuma operação registrada para este arquivo."

        texto_export = f"=== HISTÓRICO DE PROCESSAMENTO: {nome_arquivo} ===\n\n"
        for i, op in enumerate(pipeline, 1):
            ts = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(op.get("timestamp", 0))
            )
            desc = op.get("operacao", "Operação desconhecida")
            coluna = op.get("coluna", "N/A")
            grafico = op.get("grafico", "N/A")

            texto_export += f"[{i}] {ts}\n"
            texto_export += f"    Gráfico/Coluna Alvo: {grafico} ({coluna})\n"
            texto_export += f"    Detalhes: {desc}\n\n"

        return texto_export

    def processar_carregamento_emt(self, file_path):
        from arquivos.parsers.open_emt import TratamentoEMT

        leitor = TratamentoEMT()
        sucesso = leitor.load_emt_file(file_path)
        if not sucesso:
            raise ValueError(f"Não foi possível processar o arquivo EMT: {file_path}")

        df = leitor.get_dataframe()
        conteudo = leitor.get_file_info()
        cabecalho = leitor.get_header_info()

        nome = conteudo["nome_arqv"]
        if nome in self.guarda_arquivos:
            raise ValueError(f"O arquivo '{nome}' já está aberto.")

        if len(self.guarda_arquivos) >= 50:
            raise ValueError(
                "Você atingiu o limite de 50 arquivos abertos simultaneamente."
            )

        self.guarda_arquivos[nome] = {
            "dataframe_original": df.copy(),
            "dataframe": df,
            "conteudo": conteudo,
            "cabecalho": cabecalho,
            "pipeline": [],
            "colunas_modificadas": set(),
            "unidades_colunas": {},
        }
        self.guarda_graficos[nome] = {}
        self.arquivo_ativo = nome
        return nome

    def processar_carregamento_tdf(self, file_path):
        from arquivos.parsers.open_tdf import TratamentoTDF

        leitor = TratamentoTDF()
        try:
            sucesso = leitor.load_tdf_file(file_path)
        except ValueError as e:
            raise ValueError(
                "Não foram identificados dados 3D, EMG ou de Plataforma de Força."
            ) from e

        if not sucesso:
            raise ValueError(f"Não foi possível processar o arquivo TDF: {file_path}")

        df = leitor.get_dataframe()
        conteudo = leitor.get_file_info()
        cabecalho = leitor.get_header_info()
        unidades_colunas = leitor.unidades_colunas

        nome = conteudo["nome_arqv"]
        if nome in self.guarda_arquivos:
            raise ValueError(f"O arquivo '{nome}' já está aberto.")

        if len(self.guarda_arquivos) >= 50:
            raise ValueError(
                "Você atingiu o limite de 50 arquivos abertos simultaneamente."
            )

        self.guarda_arquivos[nome] = {
            "dataframe_original": df.copy(),
            "dataframe": df,
            "conteudo": conteudo,
            "cabecalho": cabecalho,
            "pipeline": [],
            "colunas_modificadas": set(),
            "unidades_colunas": unidades_colunas or {},
        }
        self.guarda_graficos[nome] = {}
        self.arquivo_ativo = nome
        return nome

    def salvar_projeto(self, caminho_arquivo):
        from arquivos.projeto.gerenciadorSAS import GerenciadorSAS

        if not caminho_arquivo.endswith(".sas"):
            caminho_arquivo += ".sas"
        GerenciadorSAS.salvar_projeto(
            caminho_arquivo,
            self.guarda_arquivos,
            self.guarda_graficos,
            self.guarda_sobreposicoes,
            self.guarda_exibicoes_simultaneas,
            self.guarda_scripts,
        )

    def abrir_projeto(self, caminho_arquivo):
        from arquivos.projeto.gerenciadorSAS import GerenciadorSAS

        ga, gg, gs, ges, gscripts = GerenciadorSAS.abrir_projeto(caminho_arquivo)

        self.guarda_scripts = gscripts

        mapeamento_nomes = {}
        for nome, dados in ga.items():
            novo_nome = nome
            contador = 1
            while novo_nome in self.guarda_arquivos:
                novo_nome = f"{nome}_{contador}"
                contador += 1

            mapeamento_nomes[nome] = novo_nome
            self.guarda_arquivos[novo_nome] = dados

            if nome in gg:
                self.guarda_graficos[novo_nome] = gg[nome]
            else:
                self.guarda_graficos[novo_nome] = {}

        for nome, config in gs.items():
            novo_nome = nome
            contador = 1
            while (
                novo_nome in self.guarda_sobreposicoes
                or novo_nome in self.guarda_exibicoes_simultaneas
            ):
                novo_nome = f"{nome}_{contador}"
                contador += 1

            if "graficos_fonte" in config:
                for ref in config["graficos_fonte"]:
                    if ref["arquivo"] in mapeamento_nomes:
                        ref["arquivo"] = mapeamento_nomes[ref["arquivo"]]

            self.guarda_sobreposicoes[novo_nome] = config

        for nome, config in ges.items():
            novo_nome = nome
            contador = 1
            while (
                novo_nome in self.guarda_sobreposicoes
                or novo_nome in self.guarda_exibicoes_simultaneas
            ):
                novo_nome = f"{nome}_{contador}"
                contador += 1

            if "layout" in config:
                for row in config["layout"]:
                    for ref in row:
                        if ref is not None and ref["arquivo"] in mapeamento_nomes:
                            ref["arquivo"] = mapeamento_nomes[ref["arquivo"]]

            self.guarda_exibicoes_simultaneas[novo_nome] = config

        return list(mapeamento_nomes.values())

    def _aplicar_operacao(self, nome_arquivo, nome_grafico_original, tipo_operacao):
        from processamento.operacoes import operar_calculo_escalar, calcular_media_movel
        import pandas as pd

        df_completo = self.guarda_arquivos[nome_arquivo]["dataframe"]
        config_original = self.guarda_graficos[nome_arquivo][nome_grafico_original]
        tipo_grafico = config_original.get("tipo", "Linha")

        if "dados_y_calc" in config_original:
            dados_y = pd.Series(
                config_original["dados_y_calc"], index=df_completo.index
            )
            dados_y.name = config_original["titulo"]
        else:
            dados_y = df_completo[config_original["eixo_y"]]

        dados_x = df_completo[config_original["eixo_x"]]
        coluna_x = config_original["eixo_x"]

        if tipo_grafico == "Dispersão" and tipo_operacao in ["integral", "derivada"]:
            raise ValueError(
                f"Não é possível calcular a {tipo_operacao.capitalize()} diretamente de um gráfico de Dispersão."
            )

        unidade_x = config_original.get("unidade_x", "")
        unidade_y = config_original.get("unidade_y", "")
        nova_unidade_y = unidade_y

        if tipo_operacao == "integral":
            resultado_y, erro = operar_calculo_escalar(dados_x, dados_y, "integral")
            nome_base_grafico = f"Integral({dados_y.name})"
            if unidade_y and unidade_x:
                nova_unidade_y = f"{unidade_y}*{unidade_x}"
        elif tipo_operacao == "derivada":
            resultado_y, erro = operar_calculo_escalar(dados_x, dados_y, "derivada_1")
            nome_base_grafico = f"Derivada({dados_y.name})"
            if unidade_y and unidade_x:
                nova_unidade_y = f"{unidade_y}/{unidade_x}"
        elif tipo_operacao == "media":
            resultado_y, nome_base_grafico = calcular_media_movel(
                dados_x, dados_y, janela=5
            )
            erro = None
        elif tipo_operacao == "modulo":
            resultado_y, erro = operar_calculo_escalar(dados_x, dados_y, "modulo")
            nome_base_grafico = f"Módulo({dados_y.name})"
        elif tipo_operacao == "inversa":
            resultado_y, erro = operar_calculo_escalar(dados_x, dados_y, "inverso")
            nome_base_grafico = f"Inversa({dados_y.name})"
            if unidade_y:
                nova_unidade_y = f"1/{unidade_y}"
        else:
            raise ValueError("Operação desconhecida.")

        if erro:
            raise ValueError(erro)

        contagem = 1
        nome_novo_grafico = nome_base_grafico
        while self.nome_existe(nome_arquivo, nome_novo_grafico):
            contagem += 1
            nome_novo_grafico = f"{nome_base_grafico} ({contagem})"

        config_novo = {
            "tipo": tipo_grafico,
            "titulo": nome_novo_grafico,
            "eixo_x": coluna_x,
            "eixo_y": f"Calculado({tipo_operacao})",
            "dados_y_calc": resultado_y.tolist(),
            "origem_arquivo": nome_arquivo,
            "origem_grafico_pai": nome_grafico_original,
            "operacao": tipo_operacao,
            "unidade_x": unidade_x,
            "unidade_y": nova_unidade_y,
        }

        if nome_arquivo not in self.guarda_graficos:
            self.guarda_graficos[nome_arquivo] = {}
        self.guarda_graficos[nome_arquivo][nome_novo_grafico] = config_novo

        self.grafico_ativo = nome_novo_grafico
        self.arquivo_ativo = nome_arquivo
        return nome_novo_grafico

    def desfazer_ultima_operacao(self, nome_arquivo):
        dados_arq = self.guarda_arquivos[nome_arquivo]
        pipeline = dados_arq.get("pipeline", [])

        idx_remover = -1
        for i in range(len(pipeline) - 1, -1, -1):
            if pipeline[i].get("is_operation_var"):
                idx_remover = i
                break

        if idx_remover == -1:
            raise ValueError("Não há variáveis recém-criadas para desfazer.")

        step = pipeline.pop(idx_remover)
        nome_var = step.get("variavel_gerada")

        df = dados_arq["dataframe"]
        df_orig = dados_arq["dataframe_original"]

        if nome_var and nome_var in df.columns:
            df.drop(columns=[nome_var], inplace=True)
            df_orig.drop(columns=[nome_var], inplace=True)
            return nome_var
        else:
            raise ValueError("Variável não encontrada no DataFrame para ser removida.")

    def desfazer_ultima_interpolacao(self):
        ultimo_batch_id = -1
        for nome_arq, dados_arq in self.guarda_arquivos.items():
            pipeline = dados_arq["pipeline"]
            for step in pipeline:
                if (
                    step.get("acao") == "Preencher Lacunas (Interpolação)"
                    and step.get("batch_id", -1) > ultimo_batch_id
                ):
                    ultimo_batch_id = step["batch_id"]

        if ultimo_batch_id == -1:
            raise ValueError("Não há interpolações recentes para desfazer.")

        revertidos = 0
        graficos_removidos = []
        for nome_arq, dados_arq in self.guarda_arquivos.items():
            pipeline = dados_arq["pipeline"]
            idx_step = None
            for i in range(len(pipeline) - 1, -1, -1):
                if pipeline[i].get("batch_id") == ultimo_batch_id:
                    idx_step = i
                    break

            if idx_step is None:
                continue

            step = pipeline.pop(idx_step)
            df = dados_arq["dataframe"]
            df_orig = dados_arq["dataframe_original"]

            colunas_criadas = step.get("colunas_criadas", {})
            for col_orig, col_nova in colunas_criadas.items():
                if col_nova in df.columns:
                    df.drop(columns=[col_nova], inplace=True)
                if col_nova in df_orig.columns:
                    df_orig.drop(columns=[col_nova], inplace=True)

            graficos_criados = step.get("graficos_criados", [])
            for g_info in graficos_criados:
                nome_graf = g_info["grafico"]
                if (
                    nome_arq in self.guarda_graficos
                    and nome_graf in self.guarda_graficos[nome_arq]
                ):
                    del self.guarda_graficos[nome_arq][nome_graf]
                graficos_removidos.append((nome_arq, nome_graf))

            revertidos += 1

            if self.arquivo_ativo == nome_arq and self.grafico_ativo:
                graficos_arq = self.guarda_graficos.get(nome_arq, {})
                if self.grafico_ativo not in graficos_arq:
                    self.grafico_ativo = None

        return revertidos, graficos_removidos

    def _executar_renomeacao(self, nome_antigo, novo_nome, nome_arquivo=None):
        if not novo_nome or novo_nome == nome_antigo:
            return False

        if nome_arquivo is None:  # É um arquivo ou uma composição/sobreposição
            if nome_antigo in self.guarda_sobreposicoes:
                if (
                    novo_nome in self.guarda_sobreposicoes
                    or novo_nome in self.guarda_exibicoes_simultaneas
                ):
                    raise ValueError(f"A composição '{novo_nome}' já existe.")
                config = self.guarda_sobreposicoes.pop(nome_antigo)
                config["titulo"] = novo_nome
                self.guarda_sobreposicoes[novo_nome] = config
                if self.grafico_ativo == nome_antigo:
                    self.grafico_ativo = novo_nome
                return True
            elif nome_antigo in self.guarda_exibicoes_simultaneas:
                if (
                    novo_nome in self.guarda_sobreposicoes
                    or novo_nome in self.guarda_exibicoes_simultaneas
                ):
                    raise ValueError(f"A composição '{novo_nome}' já existe.")
                config = self.guarda_exibicoes_simultaneas.pop(nome_antigo)
                config["titulo"] = novo_nome
                self.guarda_exibicoes_simultaneas[novo_nome] = config
                if self.grafico_ativo == nome_antigo:
                    self.grafico_ativo = novo_nome
                return True
            else:
                if novo_nome in self.guarda_arquivos:
                    raise ValueError(f"O arquivo '{novo_nome}' já existe.")
                if nome_antigo not in self.guarda_arquivos:
                    raise ValueError(f"O arquivo '{nome_antigo}' não existe.")

                self.guarda_arquivos[novo_nome] = self.guarda_arquivos.pop(nome_antigo)
                self.guarda_graficos[novo_nome] = self.guarda_graficos.pop(
                    nome_antigo, {}
                )
                if self.arquivo_ativo == nome_antigo:
                    self.arquivo_ativo = novo_nome

                if "pipeline" not in self.guarda_arquivos[novo_nome]:
                    self.guarda_arquivos[novo_nome]["pipeline"] = []
                self.guarda_arquivos[novo_nome]["pipeline"].append(
                    {
                        "categoria": "Modificações Estruturais",
                        "acao": "Renomeação de Arquivo",
                        "nome_original": nome_antigo,
                        "novo_nome": novo_nome,
                    }
                )
                return True
        else:  # É um gráfico
            if self.nome_existe(nome_arquivo, novo_nome):
                raise ValueError(
                    f"O gráfico '{novo_nome}' já existe em '{nome_arquivo}'."
                )

            if (
                nome_arquivo in self.guarda_graficos
                and nome_antigo in self.guarda_graficos[nome_arquivo]
            ):
                props = self.guarda_graficos[nome_arquivo].pop(nome_antigo)
                props["titulo"] = novo_nome
                self.guarda_graficos[nome_arquivo][novo_nome] = props

                if (
                    self.grafico_ativo == nome_antigo
                    and self.arquivo_ativo == nome_arquivo
                ):
                    self.grafico_ativo = novo_nome
            return True

    def _remover_arquivo(self, nome_arquivo):
        if nome_arquivo in self.guarda_arquivos:
            del self.guarda_arquivos[nome_arquivo]
        if nome_arquivo in self.guarda_graficos:
            del self.guarda_graficos[nome_arquivo]

        comp_para_remover = []
        for nome_comp, config in list(self.guarda_sobreposicoes.items()):
            fontes = config.get("graficos_fonte", [])
            if any(f.get("arquivo") == nome_arquivo for f in fontes):
                comp_para_remover.append(("sobreposicao", nome_comp))
                del self.guarda_sobreposicoes[nome_comp]

        for nome_comp, config in list(self.guarda_exibicoes_simultaneas.items()):
            layout = config.get("layout", [])
            para_remover = False
            for row in layout:
                for ref in row:
                    if ref and ref.get("arquivo") == nome_arquivo:
                        para_remover = True
                        break
            if para_remover:
                comp_para_remover.append(("exibicao_simultanea", nome_comp))
                del self.guarda_exibicoes_simultaneas[nome_comp]

        if self.arquivo_ativo == nome_arquivo:
            self.arquivo_ativo = None
            self.grafico_ativo = None

        return comp_para_remover

    def _remover_composicao(self, nome_composicao, tipo):
        if tipo == "Sobreposicao" or tipo == "sobreposicao":
            if nome_composicao in self.guarda_sobreposicoes:
                config = self.guarda_sobreposicoes[nome_composicao]
                if config.get("tipo_composicao") == "multiplas_curvas":
                    for ref in config.get("graficos_fonte", []):
                        arq = ref.get("arquivo")
                        graf = ref.get("grafico")
                        if (
                            arq in self.guarda_graficos
                            and graf in self.guarda_graficos[arq]
                        ):
                            if self.guarda_graficos[arq][graf].get("hidden", False):
                                del self.guarda_graficos[arq][graf]
                del self.guarda_sobreposicoes[nome_composicao]
        elif tipo == "ExibicaoSimultanea" or tipo == "simultanea":
            if nome_composicao in self.guarda_exibicoes_simultaneas:
                del self.guarda_exibicoes_simultaneas[nome_composicao]

        if self.grafico_ativo == nome_composicao:
            self.grafico_ativo = None
            self.arquivo_ativo = None

    def _salvar_nova_variavel(self, resultado):
        nome_arquivo = resultado.get("nome_arquivo")
        if not nome_arquivo or nome_arquivo not in self.guarda_arquivos:
            raise ValueError("Arquivo não encontrado.")

        dados_arquivo = self.guarda_arquivos[nome_arquivo]
        df = dados_arquivo["dataframe"]

        nome_nova_var = resultado["nome"]
        valores = resultado["valores"]
        df[nome_nova_var] = valores

        # Tenta atualizar o original, ignorando erro se houver incompatibilidade de tamanho (ex: após recortes manuais)
        if "dataframe_original" in dados_arquivo:
            try:
                dados_arquivo["dataframe_original"][nome_nova_var] = valores.copy()
            except ValueError:
                pass

        if "unidade" in resultado and resultado["unidade"]:
            unidades = dados_arquivo.get("unidades_colunas", {})
            unidades[nome_nova_var] = resultado["unidade"]

        if "pipeline_step" in resultado:
            if "pipeline" not in dados_arquivo:
                dados_arquivo["pipeline"] = []

            step = resultado["pipeline_step"]
            step["is_operation_var"] = True
            dados_arquivo["pipeline"].append(step)

        return nome_nova_var

    # --- API de Acesso Encapsulado aos Dicionários ---
    def get_arquivos(self):
        return self.guarda_arquivos

    def get_arquivo(self, nome_arquivo):
        return self.guarda_arquivos.get(nome_arquivo)

    def get_dataframe(self, nome_arquivo):
        arq = self.get_arquivo(nome_arquivo)
        return arq["dataframe"] if arq and "dataframe" in arq else None

    def get_dataframe_original(self, nome_arquivo):
        arq = self.get_arquivo(nome_arquivo)
        return (
            arq["dataframe_original"] if arq and "dataframe_original" in arq else None
        )

    def set_dataframe(self, nome_arquivo, df):
        if nome_arquivo in self.guarda_arquivos:
            self.guarda_arquivos[nome_arquivo]["dataframe"] = df

    def set_dataframe_original(self, nome_arquivo, df):
        if nome_arquivo in self.guarda_arquivos:
            self.guarda_arquivos[nome_arquivo]["dataframe_original"] = df

    def get_unidades_colunas(self, nome_arquivo):
        arq = self.get_arquivo(nome_arquivo)
        return arq.get("unidades_colunas", {}) if arq else {}

    def get_cabecalho(self, nome_arquivo):
        arq = self.get_arquivo(nome_arquivo)
        return arq.get("cabecalho", {}) if arq else {}

    def get_pipeline(self, nome_arquivo):
        arq = self.get_arquivo(nome_arquivo)
        return arq.get("pipeline", []) if arq else []

    def adicionar_evento_pipeline_arquivo(self, nome_arquivo, evento):
        if nome_arquivo in self.guarda_arquivos:
            if "pipeline" not in self.guarda_arquivos[nome_arquivo]:
                self.guarda_arquivos[nome_arquivo]["pipeline"] = []
            self.guarda_arquivos[nome_arquivo]["pipeline"].append(evento)

    def get_pipeline_colunas(self, nome_arquivo):
        arq = self.get_arquivo(nome_arquivo)
        return arq.get("pipeline_colunas", {}) if arq else {}

    def atualizar_pipeline_colunas(self, nome_arquivo, coluna, historico):
        if nome_arquivo in self.guarda_arquivos:
            if "pipeline_colunas" not in self.guarda_arquivos[nome_arquivo]:
                self.guarda_arquivos[nome_arquivo]["pipeline_colunas"] = {}
            self.guarda_arquivos[nome_arquivo]["pipeline_colunas"][coluna] = historico

    def get_graficos(self, nome_arquivo=None):
        if nome_arquivo:
            return self.guarda_graficos.get(nome_arquivo, {})
        return self.guarda_graficos

    def get_config_grafico(self, nome_arquivo, nome_grafico):
        return self.guarda_graficos.get(nome_arquivo, {}).get(nome_grafico)

    def adicionar_config_grafico(self, nome_arquivo, nome_grafico, config):
        if nome_arquivo not in self.guarda_graficos:
            self.guarda_graficos[nome_arquivo] = {}
        self.guarda_graficos[nome_arquivo][nome_grafico] = config

    def remover_grafico(self, nome_arquivo, nome_grafico):
        if (
            nome_arquivo in self.guarda_graficos
            and nome_grafico in self.guarda_graficos[nome_arquivo]
        ):
            del self.guarda_graficos[nome_arquivo][nome_grafico]

    def set_grafico_hidden(self, nome_arquivo, nome_grafico, hidden=True):
        if (
            nome_arquivo in self.guarda_graficos
            and nome_grafico in self.guarda_graficos[nome_arquivo]
        ):
            self.guarda_graficos[nome_arquivo][nome_grafico]["hidden"] = hidden

    def _buscar_composicoes_que_usam_grafico(self, nome_arquivo, nomes_graficos):
        """Retorna lista de (tipo, nome) de composições que referenciam algum dos gráficos informados."""
        composicoes_afetadas = []

        for nome_comp, config in self.guarda_sobreposicoes.items():
            for ref in config.get("graficos_fonte", []):
                if (
                    ref.get("arquivo") == nome_arquivo
                    and ref.get("grafico") in nomes_graficos
                ):
                    composicoes_afetadas.append(("sobreposicao", nome_comp))
                    break

        for nome_comp, config in self.guarda_exibicoes_simultaneas.items():
            encontrou = False
            for row in config.get("layout", []):
                for ref in row:
                    if (
                        ref
                        and ref.get("arquivo") == nome_arquivo
                        and ref.get("grafico") in nomes_graficos
                    ):
                        composicoes_afetadas.append(("simultanea", nome_comp))
                        encontrou = True
                        break
                if encontrou:
                    break

        return composicoes_afetadas

    def get_sobreposicoes(self):
        return self.guarda_sobreposicoes

    def get_config_sobreposicao(self, nome_composicao):
        return self.guarda_sobreposicoes.get(nome_composicao)

    def adicionar_sobreposicao(self, nome_composicao, config):
        self.guarda_sobreposicoes[nome_composicao] = config

    def get_exibicoes_simultaneas(self):
        return self.guarda_exibicoes_simultaneas

    def get_config_exibicao_simultanea(self, nome_composicao):
        return self.guarda_exibicoes_simultaneas.get(nome_composicao)

    def adicionar_exibicao_simultanea(self, nome_composicao, config):
        self.guarda_exibicoes_simultaneas[nome_composicao] = config
