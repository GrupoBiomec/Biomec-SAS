import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from controller.gerenciador_estado import GerenciadorEstado


@pytest.fixture
def base_estado():
    """Fixture que fornece um GerenciadorEstado populado com um arquivo e DataFrame básico."""
    # Arrange
    estado = GerenciadorEstado()
    nome_arquivo = "arquivo_teste"
    df = pd.DataFrame({"tempo": [0.0, 1.0, 2.0], "sinal": [1.0, 2.0, 3.0]})

    estado.guarda_arquivos[nome_arquivo] = {
        "dataframe_original": df.copy(),
        "dataframe": df,
        "conteudo": {"nome_arqv": nome_arquivo},
        "cabecalho": {},
        "pipeline": [],
        "colunas_modificadas": set(),
        "unidades_colunas": {"tempo": "s", "sinal": "V"},
    }
    estado.guarda_graficos[nome_arquivo] = {}
    estado.arquivo_ativo = nome_arquivo
    return estado


def test_exportar_pipeline_vazio_retorna_mensagem_padrao(base_estado):
    # 1. Arrange
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # 2. Act
    resultado = estado.exportar_pipeline(nome_arquivo)

    # 3. Assert
    assert resultado == "Nenhuma operação registrada para este arquivo."


def test_exportar_pipeline_populado_formata_operacoes_corretamente(base_estado):
    # 1. Arrange
    estado = base_estado
    nome_arquivo = "arquivo_teste"
    estado.guarda_arquivos[nome_arquivo]["pipeline"] = [
        {
            "operacao": "Ajuste de ganho",
            "grafico": "grafico_1",
            "coluna": "sinal",
            "timestamp": 1717717717.0,
            "arquivo": nome_arquivo,
        }
    ]

    # 2. Act
    resultado = estado.exportar_pipeline(nome_arquivo)

    # 3. Assert
    assert "=== HISTÓRICO DE PROCESSAMENTO: arquivo_teste ===" in resultado
    assert "Ajuste de ganho" in resultado
    assert "grafico_1 (sinal)" in resultado


def test_desfazer_ultima_interpolacao_vazia_lanca_erro(base_estado):
    # 1. Arrange
    estado = base_estado
    # Sem histórico de interpolação no pipeline

    # 2. Act & 3. Assert
    with pytest.raises(
        ValueError, match="Não há interpolações recentes para desfazer."
    ):
        estado.desfazer_ultima_interpolacao()


def test_desfazer_ultima_interpolacao_sucesso_remove_colunas_e_graficos(base_estado):
    # 1. Arrange
    estado = base_estado
    nome_arquivo = "arquivo_teste"
    df = estado.guarda_arquivos[nome_arquivo]["dataframe"]
    df_orig = estado.guarda_arquivos[nome_arquivo]["dataframe_original"]

    # Adiciona a coluna interpolada nos dataframes
    df["sinal_interp"] = [1.0, 2.0, 3.0]
    df_orig["sinal_interp"] = [1.0, 2.0, 3.0]

    # Registra a interpolação no pipeline
    estado.guarda_arquivos[nome_arquivo]["pipeline"].append(
        {
            "acao": "Preencher Lacunas (Interpolação)",
            "batch_id": 42,
            "colunas_criadas": {"sinal": "sinal_interp"},
            "graficos_criados": [
                {"arquivo": nome_arquivo, "grafico": "grafico_interp"}
            ],
        }
    )

    # Registra o gráfico criado pela interpolação no estado
    estado.guarda_graficos[nome_arquivo]["grafico_interp"] = {
        "titulo": "grafico_interp",
        "eixo_x": "tempo",
        "eixo_y": "sinal_interp",
    }
    estado.grafico_ativo = "grafico_interp"

    # 2. Act
    revertidos, graficos_removidos = estado.desfazer_ultima_interpolacao()

    # 3. Assert
    assert revertidos == 1
    assert ("arquivo_teste", "grafico_interp") in graficos_removidos
    assert "sinal_interp" not in df.columns
    assert "sinal_interp" not in df_orig.columns
    assert "grafico_interp" not in estado.guarda_graficos[nome_arquivo]
    assert estado.grafico_ativo is None


def test_remover_arquivo_exclui_composicoes_dependentes(base_estado):
    # 1. Arrange
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # Adiciona sobreposição dependente do arquivo
    estado.guarda_sobreposicoes["sobreposicao_dep"] = {
        "graficos_fonte": [{"arquivo": nome_arquivo, "grafico": "grafico_1"}]
    }

    # Adiciona exibição simultânea dependente do arquivo
    estado.guarda_exibicoes_simultaneas["simultanea_dep"] = {
        "layout": [[{"arquivo": nome_arquivo, "grafico": "grafico_1"}]]
    }

    # 2. Act
    comp_removidas = estado._remover_arquivo(nome_arquivo)

    # 3. Assert
    assert ("sobreposicao", "sobreposicao_dep") in comp_removidas
    assert ("exibicao_simultanea", "simultanea_dep") in comp_removidas
    assert "sobreposicao_dep" not in estado.guarda_sobreposicoes
    assert "simultanea_dep" not in estado.guarda_exibicoes_simultaneas


def test_remover_composicao_multiplas_curvas_limpa_graficos_ocultos(base_estado):
    # 1. Arrange
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # Adiciona gráficos no estado (um oculto, outro visível)
    estado.guarda_graficos[nome_arquivo] = {
        "grafico_oculto": {"hidden": True},
        "grafico_visivel": {"hidden": False},
    }

    # Adiciona composição de múltiplas curvas referenciando ambos os gráficos
    estado.guarda_sobreposicoes["multiplas_curvas_dep"] = {
        "tipo_composicao": "multiplas_curvas",
        "graficos_fonte": [
            {"arquivo": nome_arquivo, "grafico": "grafico_oculto"},
            {"arquivo": nome_arquivo, "grafico": "grafico_visivel"},
        ],
    }

    # 2. Act
    estado._remover_composicao("multiplas_curvas_dep", "sobreposicao")

    # 3. Assert
    assert "multiplas_curvas_dep" not in estado.guarda_sobreposicoes
    # O gráfico que era oculto deve ter sido removido
    assert "grafico_oculto" not in estado.guarda_graficos[nome_arquivo]
    # O gráfico visível deve permanecer
    assert "grafico_visivel" in estado.guarda_graficos[nome_arquivo]


def test_salvar_nova_variavel_lanca_erro_se_arquivo_nao_existe(base_estado):
    # 1. Arrange
    estado = base_estado
    resultado = {
        "nome_arquivo": "arquivo_inexistente",
        "nome": "nova_var",
        "valores": pd.Series([1.0, 2.0, 3.0]),
    }

    # 2. Act & 3. Assert
    with pytest.raises(ValueError, match="Arquivo não encontrado."):
        estado._salvar_nova_variavel(resultado)


def test_processar_carregamento_emt_sucesso_e_falhas(base_estado, tmp_path):
    # 1. ARRANGE
    estado = base_estado

    from unittest.mock import patch

    # Caso 1: Falha no carregamento
    with patch(
        "arquivos.parsers.open_emt.TratamentoEMT.load_emt_file", return_value=False
    ):
        with pytest.raises(
            ValueError, match="Não foi possível processar o arquivo EMT:"
        ):
            estado.processar_carregamento_emt("invalido.emt")

    # Caso 2: Arquivo já aberto
    with (
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.load_emt_file", return_value=True
        ),
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.get_file_info",
            return_value={"nome_arqv": "arquivo_teste"},
        ),
    ):
        with pytest.raises(ValueError, match="já está aberto"):
            estado.processar_carregamento_emt("arquivo_teste.emt")

    # Caso 3: Limite de 50 arquivos atingido
    estado.guarda_arquivos = {f"arq{i}": {} for i in range(50)}
    with (
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.load_emt_file", return_value=True
        ),
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.get_file_info",
            return_value={"nome_arqv": "novo.emt"},
        ),
    ):
        with pytest.raises(ValueError, match="atingiu o limite de 50 arquivos"):
            estado.processar_carregamento_emt("novo.emt")

    # Caso 4: Sucesso
    estado.guarda_arquivos = {}
    mock_df = pd.DataFrame({"tempo": [0, 1], "sinal": [10, 20]})
    with (
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.load_emt_file", return_value=True
        ),
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.get_dataframe",
            return_value=mock_df,
        ),
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.get_file_info",
            return_value={"nome_arqv": "novo.emt"},
        ),
        patch(
            "arquivos.parsers.open_emt.TratamentoEMT.get_header_info",
            return_value={"format": "EMG"},
        ),
    ):

        nome = estado.processar_carregamento_emt("novo.emt")
        assert nome == "novo.emt"
        assert nome in estado.guarda_arquivos
        assert estado.guarda_arquivos[nome]["dataframe"] is mock_df


def test_processar_carregamento_tdf_sucesso_e_falhas(base_estado):
    # 1. ARRANGE
    estado = base_estado
    from unittest.mock import patch

    # Caso 1: ValueError propagado pelo parser (sem dados 3D, etc.)
    with patch(
        "arquivos.parsers.open_tdf.TratamentoTDF.load_tdf_file",
        side_effect=ValueError("Sem dados"),
    ):
        with pytest.raises(
            ValueError,
            match="Não foram identificados dados 3D, EMG ou de Plataforma de Força",
        ):
            estado.processar_carregamento_tdf("invalido.tdf")

    # Caso 2: Falha no carregamento geral
    with patch(
        "arquivos.parsers.open_tdf.TratamentoTDF.load_tdf_file", return_value=False
    ):
        with pytest.raises(
            ValueError, match="Não foi possível processar o arquivo TDF"
        ):
            estado.processar_carregamento_tdf("invalido.tdf")

    # Caso 3: Arquivo já aberto
    with (
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.load_tdf_file", return_value=True
        ),
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.get_file_info",
            return_value={"nome_arqv": "arquivo_teste"},
        ),
    ):
        with pytest.raises(ValueError, match="já está aberto"):
            estado.processar_carregamento_tdf("arquivo_teste.tdf")

    # Caso 4: Limite de 50 arquivos
    estado.guarda_arquivos = {f"arq{i}": {} for i in range(50)}
    with (
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.load_tdf_file", return_value=True
        ),
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.get_file_info",
            return_value={"nome_arqv": "novo.tdf"},
        ),
    ):
        with pytest.raises(ValueError, match="atingiu o limite de 50 arquivos"):
            estado.processar_carregamento_tdf("novo.tdf")

    # Caso 5: Sucesso
    estado.guarda_arquivos = {}
    mock_df = pd.DataFrame({"tempo": [0, 1], "sinal": [10, 20]})
    with (
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.load_tdf_file", return_value=True
        ),
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.get_dataframe",
            return_value=mock_df,
        ),
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.get_file_info",
            return_value={"nome_arqv": "novo.tdf"},
        ),
        patch(
            "arquivos.parsers.open_tdf.TratamentoTDF.get_header_info", return_value={}
        ),
    ):

        nome = estado.processar_carregamento_tdf("novo.tdf")
        assert nome == "novo.tdf"
        assert nome in estado.guarda_arquivos


def test_salvar_e_abrir_projeto_estado(base_estado):
    # 1. ARRANGE
    estado = base_estado
    from unittest.mock import patch

    # Caso 1: Salvar projeto
    with patch(
        "arquivos.projeto.gerenciadorSAS.GerenciadorSAS.salvar_projeto"
    ) as mock_salvar:
        estado.salvar_projeto("meu_projeto")
        # Deve ter adicionado .sas
        mock_salvar.assert_called_once_with(
            "meu_projeto.sas",
            estado.guarda_arquivos,
            estado.guarda_graficos,
            estado.guarda_sobreposicoes,
            estado.guarda_exibicoes_simultaneas,
            estado.guarda_scripts,
        )

    # Caso 2: Abrir projeto e mesclar dados com colisão de nomes
    estado.guarda_arquivos = {"arq1": {"dados": 1}}
    estado.guarda_sobreposicoes = {"sobre1": {}}
    estado.guarda_exibicoes_simultaneas = {"simul1": {}}

    # arq_sem_graf não tem entrada em gg_mock (cobre linha 165)
    ga_mock = {"arq1": {"dados_novos": 2}, "arq_sem_graf": {"dados": 3}}
    gg_mock = {"arq1": {"graf1": {"hidden": False}}}
    gs_mock = {"sobre1": {"graficos_fonte": [{"arquivo": "arq1"}]}}
    ges_mock = {"simul1": {"layout": [[{"arquivo": "arq1"}]]}}
    gscripts_mock = {"script1": {}}

    with patch(
        "arquivos.projeto.gerenciadorSAS.GerenciadorSAS.abrir_projeto",
        return_value=(ga_mock, gg_mock, gs_mock, ges_mock, gscripts_mock),
    ):
        arquivos_carregados = estado.abrir_projeto("meu_projeto.sas")

    # 3. ASSERT
    # arq1 já existia, então renomeou para arq1_1
    assert "arq1_1" in arquivos_carregados
    assert "arq_sem_graf" in arquivos_carregados
    assert estado.guarda_arquivos["arq1_1"] == {"dados_novos": 2}
    assert estado.guarda_graficos["arq1_1"] == {"graf1": {"hidden": False}}
    assert estado.guarda_graficos["arq_sem_graf"] == {}
    assert (
        estado.guarda_sobreposicoes["sobre1_1"]["graficos_fonte"][0]["arquivo"]
        == "arq1_1"
    )
    assert (
        estado.guarda_exibicoes_simultaneas["simul1_1"]["layout"][0][0]["arquivo"]
        == "arq1_1"
    )
    assert estado.guarda_scripts == {"script1": {}}


def test_aplicar_operacao_sucesso_e_falhas(base_estado):
    # 1. ARRANGE
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # Adicionamos dados_y_calc para testar linha 207-208
    estado.guarda_graficos[nome_arquivo]["graf1"] = {
        "titulo": "graf1",
        "tipo": "Linha",
        "eixo_x": "tempo",
        "eixo_y": "sinal",
        "unidade_x": "s",
        "unidade_y": "V",
        "dados_y_calc": [1.0, 2.0, 3.0],
    }

    # Caso 1: Operação Integral
    nome_novo = estado._aplicar_operacao(nome_arquivo, "graf1", "integral")
    assert nome_novo == "Integral(graf1)"
    assert estado.guarda_graficos[nome_arquivo][nome_novo]["unidade_y"] == "V*s"
    assert len(estado.guarda_graficos[nome_arquivo][nome_novo]["dados_y_calc"]) == 3

    # Caso 1b: Executa de novo para ver colisão (linhas 249-250)
    nome_novo_colisao = estado._aplicar_operacao(nome_arquivo, "graf1", "integral")
    assert nome_novo_colisao == "Integral(graf1) (2)"

    # Caso 1c: nome_arquivo não em guarda_graficos (linha 266)
    # Deleta temporariamente da guarda_graficos e chama novamente usando patch para deletar no meio
    from processamento.operacoes import operar_calculo_escalar

    def side_effect_deleta_graficos(x, y, op):
        estado.guarda_graficos.pop(nome_arquivo, None)
        return operar_calculo_escalar(x, y, op)

    with patch(
        "processamento.operacoes.operar_calculo_escalar",
        side_effect=side_effect_deleta_graficos,
    ):
        # Recria graf1
        estado.guarda_graficos[nome_arquivo] = {
            "graf1": {
                "titulo": "graf1",
                "tipo": "Linha",
                "eixo_x": "tempo",
                "eixo_y": "sinal",
                "unidade_x": "s",
                "unidade_y": "V",
            }
        }
        nome_novo_c = estado._aplicar_operacao(nome_arquivo, "graf1", "integral")
        assert nome_novo_c == "Integral(sinal)"
        assert nome_arquivo in estado.guarda_graficos

    # Caso 2: Operação Derivada
    estado.guarda_graficos[nome_arquivo]["graf1"] = {
        "titulo": "graf1",
        "tipo": "Linha",
        "eixo_x": "tempo",
        "eixo_y": "sinal",
        "unidade_x": "s",
        "unidade_y": "V",
    }
    nome_novo_2 = estado._aplicar_operacao(nome_arquivo, "graf1", "derivada")
    assert nome_novo_2 == "Derivada(sinal)"
    assert estado.guarda_graficos[nome_arquivo][nome_novo_2]["unidade_y"] == "V/s"

    # Caso 3: Operação Média
    nome_novo_3 = estado._aplicar_operacao(nome_arquivo, "graf1", "media")
    assert "Média Móvel (sinal)" in nome_novo_3

    # Caso 4: Operação Módulo
    nome_novo_4 = estado._aplicar_operacao(nome_arquivo, "graf1", "modulo")
    assert nome_novo_4 == "Módulo(sinal)"

    # Caso 5: Operação Inversa
    nome_novo_5 = estado._aplicar_operacao(nome_arquivo, "graf1", "inversa")
    assert nome_novo_5 == "Inversa(sinal)"
    assert estado.guarda_graficos[nome_arquivo][nome_novo_5]["unidade_y"] == "1/V"

    # Caso 6: Erro - Dispersão com Integral
    estado.guarda_graficos[nome_arquivo]["graf_disp"] = {
        "titulo": "graf_disp",
        "tipo": "Dispersão",
        "eixo_x": "tempo",
        "eixo_y": "sinal",
    }
    with pytest.raises(
        ValueError, match="Não é possível calcular a Integral diretamente"
    ):
        estado._aplicar_operacao(nome_arquivo, "graf_disp", "integral")

    # Caso 7: Erro - Operação Desconhecida
    with pytest.raises(ValueError, match="Operação desconhecida"):
        estado._aplicar_operacao(nome_arquivo, "graf1", "operacao_maluca")

    # Caso 8: Erro retornado pela operação matemática (linha 244)
    estado.guarda_arquivos["arq_poucos"] = {
        "dataframe": pd.DataFrame({"tempo": [0.0], "sinal": [1.0]}),  # Apenas 1 ponto
        "unidades_colunas": {"tempo": "s", "sinal": "V"},
        "pipeline": [],
    }
    estado.guarda_graficos["arq_poucos"] = {
        "graf_poucos": {
            "titulo": "graf_poucos",
            "tipo": "Linha",
            "eixo_x": "tempo",
            "eixo_y": "sinal",
            "unidade_x": "s",
            "unidade_y": "V",
        }
    }
    with pytest.raises(ValueError, match="São necessários pelo menos 2 pontos"):
        estado._aplicar_operacao("arq_poucos", "graf_poucos", "derivada")


def test_desfazer_ultima_operacao_sucesso_e_falhas(base_estado):
    # 1. ARRANGE
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # Caso 1: Sem variáveis no pipeline
    with pytest.raises(
        ValueError, match="Não há variáveis recém-criadas para desfazer"
    ):
        estado.desfazer_ultima_operacao(nome_arquivo)

    # Caso 2: Variável no pipeline, mas não encontrada no DataFrame
    estado.guarda_arquivos[nome_arquivo]["pipeline"] = [
        {"is_operation_var": True, "variavel_gerada": "var_inexistente"}
    ]
    with pytest.raises(ValueError, match="Variável não encontrada no DataFrame"):
        estado.desfazer_ultima_operacao(nome_arquivo)

    # Caso 3: Sucesso ao desfazer
    df = estado.guarda_arquivos[nome_arquivo]["dataframe"]
    df_orig = estado.guarda_arquivos[nome_arquivo]["dataframe_original"]
    df["nova_var"] = [10, 20, 30]
    df_orig["nova_var"] = [10, 20, 30]
    estado.guarda_arquivos[nome_arquivo]["pipeline"] = [
        {"is_operation_var": True, "variavel_gerada": "nova_var"}
    ]

    nome_removido = estado.desfazer_ultima_operacao(nome_arquivo)
    assert nome_removido == "nova_var"
    assert "nova_var" not in df.columns
    assert len(estado.guarda_arquivos[nome_arquivo]["pipeline"]) == 0


def test_desfazer_ultima_interpolacao_com_multiplos_arquivos(base_estado):
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # Adiciona um segundo arquivo sem interpolações (cobre linha 321 - idx_step is None -> continue)
    estado.guarda_arquivos["segundo_arquivo"] = {
        "dataframe": pd.DataFrame({"tempo": [0.0, 1.0, 2.0], "sinal": [1.0, 2.0, 3.0]}),
        "dataframe_original": pd.DataFrame(
            {"tempo": [0.0, 1.0, 2.0], "sinal": [1.0, 2.0, 3.0]}
        ),
        "pipeline": [],
    }

    # Adiciona a coluna interpolada no arquivo principal
    df = estado.guarda_arquivos[nome_arquivo]["dataframe"]
    df_orig = estado.guarda_arquivos[nome_arquivo]["dataframe_original"]
    df["sinal_interp"] = [1.0, 2.0, 3.0]
    df_orig["sinal_interp"] = [1.0, 2.0, 3.0]

    estado.guarda_arquivos[nome_arquivo]["pipeline"].append(
        {
            "acao": "Preencher Lacunas (Interpolação)",
            "batch_id": 100,
            "colunas_criadas": {"sinal": "sinal_interp"},
            "graficos_criados": [],
        }
    )

    revertidos, rem = estado.desfazer_ultima_interpolacao()
    assert revertidos == 1
    assert "sinal_interp" not in df.columns


def test_gerenciador_estado_compositions_and_api(base_estado):
    estado = base_estado
    nome_arquivo = "arquivo_teste"

    # 1. salvar_nova_variavel (linhas 22-44)
    resultado_nova_var = {
        "nome_arquivo": "arquivo_novo_var",
        "nome_grafico": "grafico_novo_var",
        "coluna": "nova_col",
        "descricao": "Op de Teste",
        "config": {
            "titulo": "grafico_novo_var",
            "eixo_x": "tempo",
            "eixo_y": "nova_col",
        },
    }
    res = estado.salvar_nova_variavel(resultado_nova_var)
    assert res is True
    assert "arquivo_novo_var" in estado.guarda_arquivos
    assert "arquivo_novo_var" in estado.guarda_graficos
    assert (
        estado.guarda_graficos["arquivo_novo_var"]["grafico_novo_var"]["titulo"]
        == "grafico_novo_var"
    )

    # 2. _executar_renomeacao edge cases
    # novo_nome == nome_antigo -> False (linha 352)
    assert estado._executar_renomeacao("arq1", "arq1") is False
    assert estado._executar_renomeacao("arq1", "") is False

    # Composição sobreposição já existente
    estado.guarda_sobreposicoes["sobre1"] = {}
    estado.guarda_sobreposicoes["sobre2"] = {}
    with pytest.raises(ValueError, match="A composição 'sobre2' já existe."):
        estado._executar_renomeacao("sobre1", "sobre2")

    # Composição simultanea já existente
    estado.guarda_exibicoes_simultaneas["simul1"] = {}
    estado.guarda_exibicoes_simultaneas["simul2"] = {}
    with pytest.raises(ValueError, match="A composição 'simul2' já existe."):
        estado._executar_renomeacao("simul1", "simul2")

    # Arquivo já existe
    estado.guarda_arquivos["arq1"] = {}
    estado.guarda_arquivos["arq2"] = {}
    with pytest.raises(ValueError, match="O arquivo 'arq2' já existe."):
        estado._executar_renomeacao("arq1", "arq2")

    # Arquivo de origem não existe
    with pytest.raises(ValueError, match="O arquivo 'arq_inexistente' não existe."):
        estado._executar_renomeacao("arq_inexistente", "novo_nome")

    # Renomeação bem-sucedida de arquivo (linhas 379-392, cobrindo 385 sem pipeline prévio)
    estado.guarda_arquivos["arq_orig"] = {}  # Sem pipeline key
    estado.guarda_graficos["arq_orig"] = {}
    estado.arquivo_ativo = "arq_orig"
    res_rename = estado._executar_renomeacao("arq_orig", "arq_novo_nome")
    assert res_rename is True
    assert "arq_novo_nome" in estado.guarda_arquivos
    assert "arq_orig" not in estado.guarda_arquivos
    assert len(estado.guarda_arquivos["arq_novo_nome"]["pipeline"]) == 1
    assert (
        estado.guarda_arquivos["arq_novo_nome"]["pipeline"][0]["acao"]
        == "Renomeação de Arquivo"
    )

    # Renomeação bem-sucedida de gráfico (linhas 393-404)
    estado.guarda_graficos["arq_novo_nome"] = {"graf_orig": {"titulo": "graf_orig"}}
    estado.grafico_ativo = "graf_orig"
    estado.arquivo_ativo = "arq_novo_nome"
    res_rename_graf = estado._executar_renomeacao(
        "graf_orig", "graf_novo_nome", nome_arquivo="arq_novo_nome"
    )
    assert res_rename_graf is True
    assert "graf_novo_nome" in estado.guarda_graficos["arq_novo_nome"]
    assert "graf_orig" not in estado.guarda_graficos["arq_novo_nome"]
    assert estado.grafico_ativo == "graf_novo_nome"

    # Renomeação de gráfico com colisão (linha 395)
    estado.guarda_graficos["arq_novo_nome"]["graf_colisao"] = {"titulo": "graf_colisao"}
    with pytest.raises(ValueError, match="já existe em"):
        estado._executar_renomeacao(
            "graf_novo_nome", "graf_colisao", nome_arquivo="arq_novo_nome"
        )

    # 3. _remover_composicao com simultanea (linha 449-451, 454-455)
    estado.guarda_exibicoes_simultaneas["simul_rem"] = {}
    estado.grafico_ativo = "simul_rem"
    estado._remover_composicao("simul_rem", "simultanea")
    assert "simul_rem" not in estado.guarda_exibicoes_simultaneas
    assert estado.grafico_ativo is None

    # 4. _salvar_nova_variavel exception path (linha 473-474) e sem pipeline prévio (linha 482)
    df_err = pd.DataFrame({"col": [1, 2]})
    estado.guarda_arquivos["arq_err"] = {
        "dataframe": df_err,
        "dataframe_original": pd.DataFrame({"col": [1, 2, 3]}),
        # pipeline está faltando de propósito para cobrir linha 482
    }
    resultado_err = {
        "nome_arquivo": "arq_err",
        "nome": "col_err",
        "valores": np.array([10, 20]),
        "unidade": "m",
        "pipeline_step": {"acao": "teste"},
    }
    res_err_name = estado._salvar_nova_variavel(resultado_err)
    assert res_err_name == "col_err"
    assert "col_err" in estado.guarda_arquivos["arq_err"]["dataframe"].columns
    assert (
        "col_err" not in estado.guarda_arquivos["arq_err"]["dataframe_original"].columns
    )
    assert len(estado.guarda_arquivos["arq_err"]["pipeline"]) == 1

    # 5. APIs getters/setters/adders
    assert estado.get_arquivos() == estado.guarda_arquivos
    assert estado.get_arquivo("arq_err") == estado.guarda_arquivos["arq_err"]
    assert estado.get_dataframe("arq_err") is df_err
    assert estado.get_dataframe_original("arq_err") is not None
    assert estado.get_dataframe("arq_inexistente") is None
    assert estado.get_dataframe_original("arq_inexistente") is None

    estado.set_dataframe("arq_err", pd.DataFrame())
    assert len(estado.get_dataframe("arq_err")) == 0
    estado.set_dataframe_original("arq_err", pd.DataFrame())
    assert len(estado.get_dataframe_original("arq_err")) == 0

    assert estado.get_unidades_colunas("arq_err") == {}
    assert estado.get_cabecalho("arq_err") == {}
    assert len(estado.get_pipeline("arq_err")) == 1

    estado.adicionar_evento_pipeline_arquivo("arq_err", {"acao": "outro"})
    assert len(estado.get_pipeline("arq_err")) == 2

    # Testar adicionar evento sem pipeline prévio (linha 528)
    estado.guarda_arquivos["arq_sem_pipe"] = {"dataframe": pd.DataFrame()}
    estado.adicionar_evento_pipeline_arquivo("arq_sem_pipe", {"acao": "novo_evento"})
    assert len(estado.get_pipeline("arq_sem_pipe")) == 1

    assert estado.get_pipeline_colunas("arq_err") == {}
    estado.atualizar_pipeline_colunas("arq_err", "col", [{"tipo": "filtro"}])
    assert estado.get_pipeline_colunas("arq_err") == {"col": [{"tipo": "filtro"}]}

    assert estado.get_graficos() == estado.guarda_graficos
    assert estado.get_graficos("arq_err") == {}

    estado.adicionar_config_grafico("arq_err", "graf_novo", {"hidden": False})
    assert estado.get_config_grafico("arq_err", "graf_novo") == {"hidden": False}

    estado.set_grafico_hidden("arq_err", "graf_novo", True)
    assert estado.get_config_grafico("arq_err", "graf_novo")["hidden"] is True

    estado.remover_grafico("arq_err", "graf_novo")
    assert estado.get_config_grafico("arq_err", "graf_novo") is None

    assert estado.get_sobreposicoes() == estado.guarda_sobreposicoes
    estado.adicionar_sobreposicao("comp1", {"val": 1})
    assert estado.get_config_sobreposicao("comp1") == {"val": 1}

    assert estado.get_exibicoes_simultaneas() == estado.guarda_exibicoes_simultaneas
    estado.adicionar_exibicao_simultanea("simul10", {"val": 2})
    assert estado.get_config_exibicao_simultanea("simul10") == {"val": 2}
