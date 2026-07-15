import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from controller.gerenciador_estado import GerenciadorEstado
from processamento.operacoes import operar_calculo_escalar, operar_trigonometria


@pytest.fixture
def dataframe_padrao():
    """Fixture para fornecer um DataFrame básico com tempo e sinal."""
    # 1. ARRANGE
    t = np.linspace(0, 1, 10)
    y = np.array([1, 2, 3, 2, 1, 0, -1, 0, 1, 2], dtype=float)
    return pd.DataFrame({"tempo": t, "sinal": y})


@pytest.fixture
def estado_inicializado(dataframe_padrao):
    """Fixture que fornece um GerenciadorEstado já populado com um arquivo e um gráfico."""
    # 1. ARRANGE
    estado = GerenciadorEstado()
    nome_arquivo = "arquivo_teste"

    estado.guarda_arquivos[nome_arquivo] = {
        "dataframe_original": dataframe_padrao.copy(),
        "dataframe": dataframe_padrao,
        "conteudo": {"nome_arqv": nome_arquivo},
        "cabecalho": {"measure_unit": "V"},
        "pipeline": [],
        "colunas_modificadas": set(),
        "unidades_colunas": {"tempo": "s", "sinal": "V"},
    }

    estado.guarda_graficos[nome_arquivo] = {
        "grafico_original": {
            "tipo": "Linha",
            "titulo": "grafico_original",
            "eixo_x": "tempo",
            "eixo_y": "sinal",
            "unidade_x": "s",
            "unidade_y": "V",
        }
    }

    estado.arquivo_ativo = nome_arquivo
    return estado


def test_processar_carregamento_duplicado_lanca_value_error(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    mock_leitor = MagicMock()
    mock_leitor.load_emt_file.return_value = True
    mock_leitor.get_file_info.return_value = {
        "nome_arqv": "arquivo_teste"
    }  # Mesmo nome já aberto

    # 2. ACT & 3. ASSERT
    with patch("arquivos.parsers.open_emt.TratamentoEMT", return_value=mock_leitor):
        with pytest.raises(
            ValueError, match="O arquivo 'arquivo_teste' já está aberto."
        ):
            estado.processar_carregamento_emt("fake_caminho.emt")


def test_processar_carregamento_excede_limite_lanca_value_error(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    # Preenche o gerenciador até atingir o limite de 50 arquivos
    for i in range(50):
        estado.guarda_arquivos[f"arquivo_{i}"] = {}

    mock_leitor = MagicMock()
    mock_leitor.load_emt_file.return_value = True
    mock_leitor.get_file_info.return_value = {"nome_arqv": "novo_arquivo"}

    # 2. ACT & 3. ASSERT
    with patch("arquivos.parsers.open_emt.TratamentoEMT", return_value=mock_leitor):
        with pytest.raises(
            ValueError,
            match="Você atingiu o limite de 50 arquivos abertos simultaneamente.",
        ):
            estado.processar_carregamento_emt("fake_caminho.emt")


def test_desfazer_ultima_operacao_remove_coluna_e_atualiza_dataframe(
    estado_inicializado,
):
    # 1. ARRANGE
    estado = estado_inicializado
    # Adiciona uma nova variável calculada simulando um pipeline de operações
    resultado = {
        "nome_arquivo": "arquivo_teste",
        "nome": "sinal_calculado",
        "valores": pd.Series([10.0] * 10),
        "unidade": "V",
        "pipeline_step": {
            "acao": "Operação Aritmética",
            "variavel_gerada": "sinal_calculado",
            "timestamp": 123456,
        },
    }
    estado._salvar_nova_variavel(resultado)

    # Verifica que a nova coluna existe antes de desfazer
    assert (
        "sinal_calculado"
        in estado.guarda_arquivos["arquivo_teste"]["dataframe"].columns
    )

    # 2. ACT
    var_removida = estado.desfazer_ultima_operacao("arquivo_teste")

    # 3. ASSERT
    assert var_removida == "sinal_calculado"
    assert (
        "sinal_calculado"
        not in estado.guarda_arquivos["arquivo_teste"]["dataframe"].columns
    )
    assert (
        "sinal_calculado"
        not in estado.guarda_arquivos["arquivo_teste"]["dataframe_original"].columns
    )


def test_desfazer_ultima_operacao_sem_variaveis_lanca_value_error(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    # O pipeline está vazio (nenhuma variável gerada)

    # 2. ACT & 3. ASSERT
    with pytest.raises(
        ValueError, match="Não há variáveis recém-criadas para desfazer."
    ):
        estado.desfazer_ultima_operacao("arquivo_teste")


def test_executar_renomeacao_arquivo_duplicado_lanca_value_error(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    estado.guarda_arquivos["arquivo_existente"] = {}

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="O arquivo 'arquivo_existente' já existe."):
        estado._executar_renomeacao(
            "arquivo_teste", "arquivo_existente", nome_arquivo=None
        )


def test_remover_arquivo_limpa_dados_e_graficos(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado

    # 2. ACT
    estado._remover_arquivo("arquivo_teste")

    # 3. ASSERT
    assert "arquivo_teste" not in estado.guarda_arquivos
    assert "arquivo_teste" not in estado.guarda_graficos
    assert estado.arquivo_ativo is None


def test_operar_calculo_escalar_integral_calcula_corretamente(dataframe_padrao):
    # 1. ARRANGE
    x = dataframe_padrao["tempo"]
    y = dataframe_padrao["sinal"]

    # 2. ACT
    res, erro = operar_calculo_escalar(x, y, "integral")

    # 3. ASSERT
    assert erro is None
    assert isinstance(res, pd.Series)
    assert len(res) == len(x)
    assert res.iloc[0] == 0.0  # Primeira área acumulada é zero


def test_operar_calculo_escalar_inverso_evita_divisao_por_zero(dataframe_padrao):
    # 1. ARRANGE
    x = dataframe_padrao["tempo"]
    # Insere um zero para testar divisão por zero
    y = pd.Series([1.0, 0.0, 2.0], index=[0, 1, 2])
    x_curto = x.iloc[:3]

    # 2. ACT
    res, erro = operar_calculo_escalar(x_curto, y, "inverso")

    # 3. ASSERT
    assert erro is None
    assert np.isnan(res.iloc[1])  # Divisão por zero deve retornar NaN
    assert res.iloc[0] == 1.0
    assert res.iloc[2] == 0.5


def test_operar_trigonometria_graus_converte_e_calcula():
    # 1. ARRANGE
    graus = pd.Series([0.0, 90.0, 180.0])

    # 2. ACT
    res, erro = operar_trigonometria(graus, "seno", unidade="deg")

    # 3. ASSERT
    assert erro is None
    assert res.iloc[0] == pytest.approx(0.0)
    assert res.iloc[1] == pytest.approx(1.0)
    assert res.iloc[2] == pytest.approx(0.0, abs=1e-7)


def test_aplicar_operacao_inversa_calcula_valores_inversos(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado

    # 2. ACT
    nome_graf_novo = estado._aplicar_operacao(
        "arquivo_teste", "grafico_original", "inversa"
    )

    # 3. ASSERT
    assert nome_graf_novo in estado.guarda_graficos["arquivo_teste"]
    config_novo = estado.guarda_graficos["arquivo_teste"][nome_graf_novo]
    assert config_novo["unidade_y"] == "1/V"
    assert config_novo["dados_y_calc"][0] == pytest.approx(1.0)


def test_aplicar_operacao_dispersao_com_derivada_lanca_value_error(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    estado.guarda_graficos["arquivo_teste"]["grafico_original"]["tipo"] = "Dispersão"

    # 2. ACT & 3. ASSERT
    with pytest.raises(
        ValueError,
        match="Não é possível calcular a Derivada diretamente de um gráfico de Dispersão.",
    ):
        estado._aplicar_operacao("arquivo_teste", "grafico_original", "derivada")


def test_executar_renomeacao_sobreposicao_sucesso(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    estado.guarda_sobreposicoes["Sobreposicao_1"] = {"titulo": "Sobreposicao_1"}
    estado.grafico_ativo = "Sobreposicao_1"

    # 2. ACT
    sucesso = estado._executar_renomeacao("Sobreposicao_1", "Sobreposicao_Nova")

    # 3. ASSERT
    assert sucesso is True
    assert "Sobreposicao_Nova" in estado.guarda_sobreposicoes
    assert "Sobreposicao_1" not in estado.guarda_sobreposicoes
    assert (
        estado.guarda_sobreposicoes["Sobreposicao_Nova"]["titulo"]
        == "Sobreposicao_Nova"
    )
    assert estado.grafico_ativo == "Sobreposicao_Nova"


def test_executar_renomeacao_exibicao_simultanea_sucesso(estado_inicializado):
    # 1. ARRANGE
    estado = estado_inicializado
    estado.guarda_exibicoes_simultaneas["Simultanea_1"] = {"titulo": "Simultanea_1"}
    estado.grafico_ativo = "Simultanea_1"

    # 2. ACT
    sucesso = estado._executar_renomeacao("Simultanea_1", "Simultanea_Nova")

    # 3. ASSERT
    assert sucesso is True
    assert "Simultanea_Nova" in estado.guarda_exibicoes_simultaneas
    assert "Simultanea_1" not in estado.guarda_exibicoes_simultaneas
    assert (
        estado.guarda_exibicoes_simultaneas["Simultanea_Nova"]["titulo"]
        == "Simultanea_Nova"
    )
    assert estado.grafico_ativo == "Simultanea_Nova"


def test_executar_renomeacao_sobreposicao_duplicada_lanca_value_error(
    estado_inicializado,
):
    # 1. ARRANGE
    estado = estado_inicializado
    estado.guarda_sobreposicoes["Sobreposicao_1"] = {"titulo": "Sobreposicao_1"}
    estado.guarda_exibicoes_simultaneas["Simultanea_1"] = {"titulo": "Simultanea_1"}

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="A composição 'Simultanea_1' já existe."):
        estado._executar_renomeacao("Sobreposicao_1", "Simultanea_1")
