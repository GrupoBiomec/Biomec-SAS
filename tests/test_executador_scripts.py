import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from controller.gerenciador_estado import GerenciadorEstado
from processamento.executador_scripts import executar_script


@pytest.fixture
def estado_com_script():
    """Fixture para fornecer um estado com arquivo e script configurados."""
    # 1. ARRANGE
    estado = GerenciadorEstado()

    # Configura um script que realiza recorte, soma constante e plota automaticamente
    estado.guarda_scripts["script_teste"] = {
        "salvar_como_novo": True,
        "plotar_auto": True,
        "acoes": {
            "recorte_temporal": {
                "modo": "pontos",
                "inicio": 0,
                "fim": 4,
                "deslocar_0": True,
            },
            "operacoes": [
                {
                    "tipo": "Aritmética Básica",
                    "nome_nova": "sinal_soma",
                    "var_a": "sinal",
                    "operador": "+",
                    "is_const_b": True,
                    "val_b": 10.0,
                }
            ],
        },
    }

    df = pd.DataFrame(
        {
            "tempo": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "sinal": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
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

    return estado


def test_executar_script_sucesso_salva_novo_arquivo_e_aplica_operacoes(
    estado_com_script,
):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()
    arvore_mock = MagicMock()

    # Definimos os mocks com as assinaturas reais da classe GerenciadorArvore
    # para flagrar erros de assinatura obsoleta (TypeErrors)
    def mock_adicionar_arquivo(nome_arquivo):
        return MagicMock()

    def mock_adicionar_grafico_na_arvore_de_arquivo(nome_arquivo, nome_grafico):
        return MagicMock()

    arvore_mock._adicionar_arquivo = mock_adicionar_arquivo
    arvore_mock._adicionar_grafico_na_arvore_de_arquivo = (
        mock_adicionar_grafico_na_arvore_de_arquivo
    )
    main_window.arvore = arvore_mock

    # 2. ACT
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.Yes
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is True
    novo_nome = "arquivo_teste_script_teste"
    assert novo_nome in estado.guarda_arquivos

    df_novo = estado.guarda_arquivos[novo_nome]["dataframe"]
    # Recorte foi de index 0 a 4 (5 pontos)
    assert len(df_novo) == 5
    assert "sinal_soma" in df_novo.columns
    # Sinal original no index 0 era 1.0, somado a 10.0 resulta em 11.0
    assert df_novo["sinal_soma"].iloc[0] == 11.0


def test_executar_script_ausencias(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()

    # 2. ACT
    res_no_script = executar_script(
        estado, main_window, "script_inexistente", "arquivo_teste", silencioso=True
    )
    res_no_file = executar_script(
        estado, main_window, "script_teste", "arquivo_inexistente", silencioso=True
    )

    # 3. ASSERT
    assert res_no_script is None
    assert res_no_file is None


def test_executar_script_recorte_temporal_tempo(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()

    # Modifica o script para modo 'tempo', limites de 0.1 a 0.35, e deslocar_0
    estado.guarda_scripts["script_teste"]["acoes"]["recorte_temporal"] = {
        "modo": "tempo",
        "inicio": 0.1,
        "fim": 0.35,
        "deslocar_0": True,
    }

    # 2. ACT
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.Yes
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is True
    novo_nome = "arquivo_teste_script_teste"
    df_novo = estado.guarda_arquivos[novo_nome]["dataframe"]
    # Pontos originais: 0.1, 0.2, 0.3 (3 pontos na máscara)
    assert len(df_novo) == 3
    # Com deslocar_0, o primeiro tempo (0.1) vira 0.0
    assert df_novo["tempo"].iloc[0] == 0.0
    assert df_novo["tempo"].iloc[1] == pytest.approx(0.1)

    # Testar falha no recorte (sem pontos válidos)
    estado.guarda_scripts["script_teste"]["acoes"]["recorte_temporal"]["inicio"] = 10.0
    estado.guarda_scripts["script_teste"]["acoes"]["recorte_temporal"]["fim"] = 12.0
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        res = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )
        mock_box.warning.assert_called_once()
        assert res is None


def test_executar_script_operacao_sobrescrever_ou_abortar(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()

    # A variável 'sinal_soma' já existe no dataframe original
    df = estado.guarda_arquivos["arquivo_teste"]["dataframe"]
    df["sinal_soma"] = [0, 0, 0, 0, 0, 0]

    # 2. ACT (Usuário clica em Cancelar/No para não sobrescrever)
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.No
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is None  # Retornou antecipadamente sem completar o script


def test_executar_script_aritmetica_completa(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()

    # Caso 1: Divisão por variável e unidades corretas
    estado.guarda_scripts["script_teste"]["acoes"]["operacoes"] = [
        {
            "tipo": "Aritmética Básica",
            "nome_nova": "var_div",
            "var_a": "sinal",
            "operador": "/",
            "is_const_b": False,
            "var_b": "tempo",
        }
    ]

    # 2. ACT
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is True
    novo_nome = "arquivo_teste_script_teste"
    df_novo = estado.guarda_arquivos[novo_nome]["dataframe"]
    assert "var_div" in df_novo.columns
    # sinal / tempo = V / s
    assert estado.guarda_arquivos[novo_nome]["unidades_colunas"]["var_div"] == "V/s"

    # Caso 2: Multiplicação por variável
    estado.guarda_scripts["script_teste"]["acoes"]["operacoes"][0]["operador"] = "*"
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )
    assert (
        estado.guarda_arquivos["arquivo_teste_script_teste_1"]["unidades_colunas"][
            "var_div"
        ]
        == "V*s"
    )

    # Caso 3: Variável em falta lança erro e usuário opta por abortar script
    estado.guarda_scripts["script_teste"]["acoes"]["operacoes"][0]["var_a"] = "invalida"
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        # Clica em 'No' para abortar no dialog de ignorar erro
        mock_box.question.return_value = mock_box.StandardButton.No
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )
        assert sucesso is False
        from unittest.mock import ANY

        mock_box.information.assert_called_once_with(main_window, "Abortado", ANY)


def test_executar_script_trigonometria_e_funcoes_escalares(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()

    # Configura operações de Trigonometria e Cálculo Escalar
    estado.guarda_scripts["script_teste"]["acoes"]["operacoes"] = [
        {
            "tipo": "Trigonometria",
            "nome_nova": "var_trig",
            "var": "sinal",
            "operador": "seno",
        },
        {
            "tipo": "Cálculo e Funções Escalares",
            "nome_nova": "var_int",
            "var_principal": "sinal",
            "var_tempo": "tempo",
            "operador": "integral",
        },
        {
            "tipo": "Cálculo e Funções Escalares",
            "nome_nova": "var_inv",
            "var_principal": "sinal",
            "var_tempo": "tempo",
            "operador": "inverso",
        },
        {
            "tipo": "Cálculo e Funções Escalares",
            "nome_nova": "var_raiz",
            "var_principal": "sinal",
            "var_tempo": "tempo",
            "operador": "raiz_quadrada",
        },
    ]

    # 2. ACT
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is True
    novo_nome = "arquivo_teste_script_teste"
    df_novo = estado.guarda_arquivos[novo_nome]["dataframe"]
    assert "var_trig" in df_novo.columns
    assert "var_int" in df_novo.columns
    assert "var_inv" in df_novo.columns
    assert "var_raiz" in df_novo.columns
    assert estado.guarda_arquivos[novo_nome]["unidades_colunas"]["var_int"] == "V*s"
    assert estado.guarda_arquivos[novo_nome]["unidades_colunas"]["var_inv"] == "1/V"
    assert estado.guarda_arquivos[novo_nome]["unidades_colunas"]["var_raiz"] == "√(V)"


def test_executar_script_definir_angulos_nao_suportado(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()

    estado.guarda_scripts["script_teste"]["acoes"]["operacoes"] = [
        {"tipo": "Definir Ângulos", "nome_nova": "ang"}
    ]

    # 2. ACT
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        # Clica em 'No' para abortar
        mock_box.question.return_value = mock_box.StandardButton.No
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is False


def test_executar_script_substituir_original_e_plots(estado_com_script):
    # 1. ARRANGE
    estado = estado_com_script
    main_window = MagicMock()
    arvore_mock = MagicMock()
    main_window.arvore = arvore_mock

    # Não salva como novo, substitui o original
    estado.guarda_scripts["script_teste"]["salvar_como_novo"] = False

    # Define plotagem explícita de gráficos no script
    estado.guarda_scripts["script_teste"]["acoes"]["graficos"] = [
        {
            "nome_grafico": "meu_graf",
            "tipo_grafico": "Linha",
            "eixo_x": "tempo",
            "eixo_y": "sinal_soma",
        }
    ]

    # Previne colisão com gráfico já existente
    estado.guarda_graficos["arquivo_teste"] = {"meu_graf": {}}

    # 2. ACT
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        sucesso = executar_script(
            estado, main_window, "script_teste", "arquivo_teste", silencioso=True
        )

    # 3. ASSERT
    assert sucesso is True
    # arq original foi modificado
    df = estado.guarda_arquivos["arquivo_teste"]["dataframe"]
    assert "sinal_soma" in df.columns
    # Gráfico foi adicionado com tratamento de colisão de nomes
    assert "meu_graf_1" in estado.guarda_graficos["arquivo_teste"]
    arvore_mock._adicionar_grafico_na_arvore_de_arquivo.assert_called_with(
        "arquivo_teste", "meu_graf_1"
    )


def test_executar_script_missing_branches(estado_com_script):
    estado = estado_com_script
    main_window = MagicMock()
    arvore_mock = MagicMock()
    main_window.arvore = arvore_mock

    # 1. var_b não encontrada no df (Aritmética Básica)
    estado.guarda_scripts["script_b_falta"] = {
        "salvar_como_novo": False,
        "acoes": {
            "operacoes": [
                {
                    "tipo": "Aritmética Básica",
                    "nome_nova": "soma_invalida",
                    "var_a": "sinal",
                    "operador": "+",
                    "is_const_b": False,
                    "var_b": "var_b_inexistente",
                }
            ]
        },
    }
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.No  # Aborta
        res = executar_script(
            estado, main_window, "script_b_falta", "arquivo_teste", silencioso=True
        )
        assert res is False

    # 2. Operador diferente de * ou / na Aritmética para ver else: u_res = u_a
    # E não-silencioso para testar QMessageBox.information
    estado.guarda_scripts["script_soma_var"] = {
        "salvar_como_novo": False,
        "acoes": {
            "operacoes": [
                {
                    "tipo": "Aritmética Básica",
                    "nome_nova": "soma_vars",
                    "var_a": "sinal",
                    "operador": "+",
                    "is_const_b": False,
                    "var_b": "tempo",
                }
            ]
        },
    }
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        res = executar_script(
            estado, main_window, "script_soma_var", "arquivo_teste", silencioso=False
        )
        assert res is True
        mock_box.information.assert_called_once()
        assert (
            estado.guarda_arquivos["arquivo_teste"]["unidades_colunas"]["soma_vars"]
            == "V"
        )

    # 3. Trigonometria angular var missing
    estado.guarda_scripts["script_trig_invalido"] = {
        "salvar_como_novo": False,
        "acoes": {
            "operacoes": [
                {
                    "tipo": "Trigonometria",
                    "nome_nova": "trig_invalida",
                    "var": "angular_invalida",
                    "operador": "seno",
                }
            ]
        },
    }
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.No
        res = executar_script(
            estado,
            main_window,
            "script_trig_invalido",
            "arquivo_teste",
            silencioso=True,
        )
        assert res is False

    # 4. Cálculo Escalar: var_principal missing
    estado.guarda_scripts["script_calc_invalido1"] = {
        "salvar_como_novo": False,
        "acoes": {
            "operacoes": [
                {
                    "tipo": "Cálculo e Funções Escalares",
                    "nome_nova": "calc_nova",
                    "var_principal": "var_invalida",
                    "var_tempo": "tempo",
                    "operador": "integral",
                }
            ]
        },
    }
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.No
        res = executar_script(
            estado,
            main_window,
            "script_calc_invalido1",
            "arquivo_teste",
            silencioso=True,
        )
        assert res is False

    # 5. Cálculo Escalar: var_tempo missing quando precisa_x
    estado.guarda_scripts["script_calc_invalido2"] = {
        "salvar_como_novo": False,
        "acoes": {
            "operacoes": [
                {
                    "tipo": "Cálculo e Funções Escalares",
                    "nome_nova": "calc_nova",
                    "var_principal": "sinal",
                    "var_tempo": "tempo_invalido",
                    "operador": "integral",
                }
            ]
        },
    }
    with patch("processamento.executador_scripts.QMessageBox") as mock_box:
        mock_box.question.return_value = mock_box.StandardButton.No
        res = executar_script(
            estado,
            main_window,
            "script_calc_invalido2",
            "arquivo_teste",
            silencioso=True,
        )
        assert res is False

    # 6. Cálculo Escalar: outro operador
    estado.guarda_scripts["script_calc_modulo"] = {
        "salvar_como_novo": False,
        "acoes": {
            "operacoes": [
                {
                    "tipo": "Cálculo e Funções Escalares",
                    "nome_nova": "calc_abs",
                    "var_principal": "sinal",
                    "var_tempo": "tempo",
                    "operador": "modulo",
                }
            ]
        },
    }
    res = executar_script(
        estado, main_window, "script_calc_modulo", "arquivo_teste", silencioso=True
    )
    assert res is True
    assert (
        estado.guarda_arquivos["arquivo_teste"]["unidades_colunas"]["calc_abs"] == "V"
    )

    # 7. arq_destino not in guarda_graficos e plotagem
    # 8. eixo_x fallback
    # Limpa guarda_graficos
    estado.guarda_graficos = {}
    estado.guarda_scripts["script_plot_auto_custom"] = {
        "salvar_como_novo": False,
        "acoes": {
            "graficos": [
                {
                    "nome_grafico": "graf_novo",
                    "tipo_grafico": "Linha",
                    "eixo_x": "eixo_x_inexistente",
                    "eixo_y": "sinal",
                }
            ]
        },
    }
    res = executar_script(
        estado, main_window, "script_plot_auto_custom", "arquivo_teste", silencioso=True
    )
    assert res is True
    assert "arquivo_teste" in estado.guarda_graficos
    graf_config = estado.guarda_graficos["arquivo_teste"]["graf_novo"]
    # Eixo X fallback deve ser df.columns[0]
    assert graf_config["eixo_x"] == "tempo"
