import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from controller.gerenciador_estado import GerenciadorEstado
from processamento.executador_scripts_graficos import executar_script_grafico


@pytest.fixture
def estado_com_script_grafico():
    """Estado inicializado com script de gráfico, arquivo e gráfico original."""
    # 1. ARRANGE
    estado = GerenciadorEstado()
    estado.guarda_scripts_graficos = {}

    # Adiciona script de gráfico de teste
    estado.guarda_scripts_graficos["script_grafico_teste"] = {
        "acoes": {
            "titulo": "filtrado",
            "filtros": [
                {
                    "tipo": "passa_baixa",
                    "fc": 2.0,
                    "ordem": 2,
                    "retificar": False,
                    "fc_manual": True,
                }
            ],
            "offsets": [{"valor": 2.0, "nova_var": False, "nome_nova_var": ""}],
        }
    }

    df = pd.DataFrame(
        {
            "tempo": np.linspace(0, 0.14, 15),
            "sinal": [
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
                6.0,
                5.0,
                4.0,
                3.0,
                2.0,
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
            ],
        }
    )

    estado.guarda_arquivos["arquivo_teste"] = {
        "dataframe": df,
        "dataframe_original": df.copy(),
        "conteudo": {"nome_arqv": "arquivo_teste"},
        "cabecalho": {"measure_unit": "V"},
        "unidades_colunas": {"tempo": "s", "sinal": "V"},
        "pipeline": [],
        "colunas_modificadas": set(),
    }

    estado.guarda_graficos["arquivo_teste"] = {
        "grafico_original": {
            "tipo": "Linha",
            "titulo": "grafico_original",
            "eixo_x": "tempo",
            "eixo_y": "sinal",
            "unidade_x": "s",
            "unidade_y": "V",
        }
    }

    return estado


def test_executar_script_grafico_sucesso_aplica_filtros_e_offsets(
    estado_com_script_grafico,
):
    # 1. ARRANGE
    estado = estado_com_script_grafico
    main_window = MagicMock()
    arvore_mock = MagicMock()

    def mock_adicionar_grafico_na_arvore_de_arquivo(nome_arquivo, nome_grafico):
        return MagicMock()

    def mock_selecionar_item_na_arvore(nome_arquivo=None, nome_grafico=None):
        return MagicMock()

    arvore_mock._adicionar_grafico_na_arvore_de_arquivo = (
        mock_adicionar_grafico_na_arvore_de_arquivo
    )
    arvore_mock._selecionar_item_na_arvore = mock_selecionar_item_na_arvore
    main_window.arvore = arvore_mock

    # 2. ACT
    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_grafico_teste",
            "arquivo_teste",
            "grafico_original",
            silencioso=True,
        )
        warning_calls = mock_box.warning.call_args_list
        assert (
            not warning_calls
        ), f"QMessageBox.warning foi chamado com: {warning_calls}"

    # 3. ASSERT
    assert sucesso is True
    novo_nome = "grafico_original_filtrado"
    assert novo_nome in estado.guarda_graficos["arquivo_teste"]

    config_novo = estado.guarda_graficos["arquivo_teste"][novo_nome]
    assert config_novo["dados_y_calc"] is not None
    assert len(config_novo["dados_y_calc"]) == 15


def test_executar_script_grafico_early_returns(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # 1. Script inexistente
    res = executar_script_grafico(
        estado,
        main_window,
        "script_inexistente",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert res is None

    # 2. Arquivo inexistente
    res = executar_script_grafico(
        estado,
        main_window,
        "script_grafico_teste",
        "arquivo_inexistente",
        "grafico_original",
        silencioso=True,
    )
    assert res is None

    # 3. Gráfico original inexistente
    res = executar_script_grafico(
        estado,
        main_window,
        "script_grafico_teste",
        "arquivo_teste",
        "grafico_inexistente",
        silencioso=True,
    )
    assert res is None


def test_executar_script_grafico_titulo_fallback_e_colisao(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Script sem título
    estado.guarda_scripts_graficos["script_sem_titulo"] = {"acoes": {"filtros": []}}

    # Adicionar gráficos no estado para forçar colisão de nomes
    estado.guarda_graficos["arquivo_teste"]["grafico_original_script_sem_titulo"] = {}
    estado.guarda_graficos["arquivo_teste"]["grafico_original_script_sem_titulo_1"] = {}

    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_sem_titulo",
            "arquivo_teste",
            "grafico_original",
            silencioso=True,
        )
        assert sucesso is True
        # Deve ter colidido e gerado grafico_original_script_sem_titulo_2
        assert (
            "grafico_original_script_sem_titulo_2"
            in estado.guarda_graficos["arquivo_teste"]
        )


def test_executar_script_grafico_dados_y_calc_e_eixo_y_inexistente(
    estado_com_script_grafico,
):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Caso A: Usa dados_y_calc já existente
    estado.guarda_graficos["arquivo_teste"]["grafico_com_calc"] = {
        "tipo": "Linha",
        "titulo": "grafico_com_calc",
        "eixo_x": "tempo",
        "eixo_y": "sinal",
        "dados_y_calc": [10.0] * 15,
    }

    # Script vazio para ver se ele copia corretamente os dados_y_calc
    estado.guarda_scripts_graficos["script_vazio"] = {"acoes": {}}

    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_vazio",
        "arquivo_teste",
        "grafico_com_calc",
        silencioso=True,
    )
    assert sucesso is True
    novo_graf = estado.guarda_graficos["arquivo_teste"]["grafico_com_calc_script_vazio"]
    assert novo_graf["dados_y_calc"] == [10.0] * 15

    # Caso B: Eixo Y não existe no DataFrame
    estado.guarda_graficos["arquivo_teste"]["grafico_eixo_invalido"] = {
        "tipo": "Linha",
        "titulo": "grafico_eixo_invalido",
        "eixo_x": "tempo",
        "eixo_y": "coluna_inexistente",
    }

    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_vazio",
            "arquivo_teste",
            "grafico_eixo_invalido",
            silencioso=True,
        )
        assert sucesso is None
        mock_box.warning.assert_called_once()


def test_executar_script_grafico_fs_fontes_e_invalidas(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Script com filtro
    estado.guarda_scripts_graficos["script_filtro"] = {
        "acoes": {
            "filtros": [
                {"tipo": "passa_baixa", "fc": 5.0, "ordem": 2, "fc_manual": True}
            ]
        }
    }

    # Caso A: fs a partir das informações
    estado.guarda_arquivos["arquivo_teste"]["informacoes"] = {
        "Frequência de Amostragem": "200.0"
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_filtro",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True

    # Caso B: fs a partir das informações sendo string inválida (deve usar calcular_fs pelo eixo x)
    estado.guarda_arquivos["arquivo_teste"]["informacoes"] = {
        "Frequência de Amostragem": "nao_e_float"
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_filtro",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True

    # Caso C: fs inválido/zero
    # Forçamos uma situação onde fs calculado seja zero ou negativo
    # Limpando eixo_x e informações
    estado.guarda_graficos["arquivo_teste"]["grafico_original"][
        "eixo_x"
    ] = "eixo_invalido"
    estado.guarda_arquivos["arquivo_teste"]["informacoes"] = {
        "Frequência de Amostragem": "0.0"
    }
    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_filtro",
            "arquivo_teste",
            "grafico_original",
            silencioso=True,
        )
        assert sucesso is None
        mock_box.warning.assert_called_once()
        assert "Frequência de amostragem" in mock_box.warning.call_args[0][2]


def test_executar_script_grafico_winter_e_nyquist(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Caso A: Frequência de corte Winter (fc_manual = False)
    estado.guarda_scripts_graficos["script_winter"] = {
        "acoes": {"filtros": [{"tipo": "passa_baixa", "ordem": 2, "fc_manual": False}]}
    }
    # fs = 100 Hz (tempo de 0 a 0.14 com 15 pontos -> dt ~ 0.01s -> fs ~ 100)
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_winter",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True

    # Caso B: Frequência de corte maior ou igual a Nyquist
    estado.guarda_scripts_graficos["script_nyquist_alto"] = {
        "acoes": {
            "filtros": [
                {"tipo": "passa_baixa", "fc": 200.0, "ordem": 2, "fc_manual": True}
            ]
        }
    }
    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_nyquist_alto",
            "arquivo_teste",
            "grafico_original",
            silencioso=True,
        )
        assert sucesso is None
        mock_box.warning.assert_called_once()
        assert "Frequência de corte" in mock_box.warning.call_args[0][2]


def test_executar_script_grafico_filtros_com_nan_e_retificacao(
    estado_com_script_grafico,
):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Insere NaNs no dataframe
    df = estado.guarda_arquivos["arquivo_teste"]["dataframe"]
    df.loc[3, "sinal"] = np.nan
    df.loc[4, "sinal"] = np.nan

    # Filtro com retificação
    estado.guarda_scripts_graficos["script_nan_retif"] = {
        "acoes": {
            "filtros": [
                {
                    "tipo": "passa_baixa",
                    "fc": 2.0,
                    "ordem": 2,
                    "retificar": True,
                    "fc_manual": True,
                }
            ]
        }
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_nan_retif",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True
    novo_graf = estado.guarda_graficos["arquivo_teste"][
        "grafico_original_script_nan_retif"
    ]
    assert novo_graf["dados_y_calc"] is not None
    assert len(novo_graf["dados_y_calc"]) == 15


def test_executar_script_grafico_interpolacoes_e_offsets(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Insere NaNs no dataframe para testar interpolações
    df = estado.guarda_arquivos["arquivo_teste"]["dataframe"]
    df.loc[5, "sinal"] = np.nan

    # Caso A: Interpolações (linear, spline, média)
    estado.guarda_scripts_graficos["script_interp_linear"] = {
        "acoes": {"interpolacoes": [{"metodo": "linear"}]}
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_interp_linear",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True

    estado.guarda_scripts_graficos["script_interp_spline"] = {
        "acoes": {"interpolacoes": [{"metodo": "spline"}]}
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_interp_spline",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True

    estado.guarda_scripts_graficos["script_interp_media"] = {
        "acoes": {"interpolacoes": [{"metodo": "média"}]}
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_interp_media",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True

    # Caso B: Offset gerando nova variável
    estado.guarda_scripts_graficos["script_offset_nova_var"] = {
        "acoes": {
            "offsets": [
                {"valor": 1.5, "nova_var": True, "nome_nova_var": "nova_coluna_sinal"}
            ]
        }
    }

    # Coluna não existe no df -> sucesso direto
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_offset_nova_var",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True
    assert (
        "nova_coluna_sinal"
        in estado.guarda_arquivos["arquivo_teste"]["dataframe"].columns
    )

    # Coluna já existe -> questionando
    # Subcaso B1: Usuário responde "Não" -> cancela
    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.No
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_offset_nova_var",
            "arquivo_teste",
            "grafico_original",
            silencioso=True,
        )
        assert sucesso is None

    # Subcaso B2: Usuário responde "Sim" -> sobrescreve
    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.Yes
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_offset_nova_var",
            "arquivo_teste",
            "grafico_original",
            silencioso=True,
        )
        assert sucesso is True


def test_executar_script_grafico_polinomios_e_nao_silencioso(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Script com polinômios de referência (um sem título, outro com título)
    estado.guarda_scripts_graficos["script_polinomios"] = {
        "acoes": {
            "polinomios": [
                {"coeficientes": [1.0, 2.0]},
                {"titulo": "Pol_Custom", "coeficientes": [3.0, 4.0]},
            ]
        }
    }

    with patch("processamento.executador_scripts_graficos.QMessageBox") as mock_box:
        sucesso = executar_script_grafico(
            estado,
            main_window,
            "script_polinomios",
            "arquivo_teste",
            "grafico_original",
            silencioso=False,
        )
        assert sucesso is True
        # Deve ter chamado a caixa de informação de sucesso
        mock_box.information.assert_called_once()

    novo_graf = estado.guarda_graficos["arquivo_teste"][
        "grafico_original_script_polinomios"
    ]
    linhas_ref = novo_graf["linhas_referencia"]
    assert len(linhas_ref) == 2
    assert linhas_ref[0]["titulo"] == "Polinômio 1"
    assert linhas_ref[0]["coeficientes"] == [1.0, 2.0]
    assert linhas_ref[1]["titulo"] == "Pol_Custom"
    assert linhas_ref[1]["coeficientes"] == [3.0, 4.0]


def test_executar_script_grafico_pipeline_colunas(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()

    # Caso onde não há pipeline_grafico mas há pipeline_colunas no arquivo
    estado.guarda_arquivos["arquivo_teste"]["pipeline_colunas"] = {
        "sinal": [{"tipo_operacao": "filtro_antigo"}]
    }

    estado.guarda_scripts_graficos["script_vazio"] = {"acoes": {}}

    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_vazio",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True
    novo_graf = estado.guarda_graficos["arquivo_teste"]["grafico_original_script_vazio"]
    assert len(novo_graf["pipeline_grafico"]) == 1
    assert novo_graf["pipeline_grafico"][0]["tipo_operacao"] == "filtro_antigo"


def test_executar_script_grafico_interpolacoes_sem_nan(estado_com_script_grafico):
    estado = estado_com_script_grafico
    main_window = MagicMock()
    # Sem NaNs no sinal
    estado.guarda_scripts_graficos["script_interp_sem_nan"] = {
        "acoes": {"interpolacoes": [{"metodo": "linear"}]}
    }
    sucesso = executar_script_grafico(
        estado,
        main_window,
        "script_interp_sem_nan",
        "arquivo_teste",
        "grafico_original",
        silencioso=True,
    )
    assert sucesso is True
