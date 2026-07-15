import pandas as pd
import json
import zipfile
import os
import tempfile
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom encoder para garantir que arrays e escalares do NumPy sejam serializáveis para JSON."""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        return super(NumpyEncoder, self).default(obj)


class GerenciadorSAS:

    @staticmethod
    def _extrair_dataframes(obj, dataframes_dir):
        """Busca recursivamente DataFrames e Series, salva como parquet e os substitui por dicionários de marcação."""
        import uuid

        if isinstance(obj, dict):
            novo_dict = {}
            for k, v in obj.items():
                # Ignora referências de interface (QTreeWidgetItem) que não podem ser salvas
                if k == "arvore":
                    continue
                novo_dict[k] = GerenciadorSAS._extrair_dataframes(v, dataframes_dir)
            return novo_dict
        elif isinstance(obj, list):
            return [GerenciadorSAS._extrair_dataframes(v, dataframes_dir) for v in obj]
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            filename = f"df_{uuid.uuid4().hex}.parquet"
            filepath = os.path.join(dataframes_dir, filename)

            if isinstance(obj, pd.Series):
                df_to_save = obj.to_frame(name="_series_data")
                is_series = True
            else:
                df_to_save = obj
                is_series = False

            df_to_save.to_parquet(filepath, index=False)
            return {
                "__tipo_dado_sas__": "dataframe",
                "arquivo_parquet": filename,
                "is_series": is_series,
            }
        else:
            return obj

    @staticmethod
    def _restaurar_dataframes(obj, dataframes_dir):
        """Busca recursivamente os dicionários de marcação e carrega os DataFrames/Series do disco."""
        if isinstance(obj, dict):
            if obj.get("__tipo_dado_sas__") == "dataframe":
                filepath = os.path.join(dataframes_dir, obj["arquivo_parquet"])
                if os.path.exists(filepath):
                    df = pd.read_parquet(filepath)
                    if obj.get("is_series", False):
                        return df["_series_data"]
                    return df
                return None

            novo_dict = {}
            for k, v in obj.items():
                novo_dict[k] = GerenciadorSAS._restaurar_dataframes(v, dataframes_dir)
            return novo_dict
        elif isinstance(obj, list):
            return [
                GerenciadorSAS._restaurar_dataframes(v, dataframes_dir) for v in obj
            ]
        else:
            return obj

    @staticmethod
    def salvar_projeto(
        caminho_arquivo_sas,
        guarda_arquivos,
        guarda_graficos,
        guarda_sobreposicoes,
        guarda_exibicoes_simultaneas,
        guarda_scripts=None,
    ):
        """
        Salva o progresso do usuário criando um arquivo .sas, que é um .zip contendo:
        - 1 arquivo config.json (com os dicionários de configuração e metadados)
        - N arquivos .parquet (um para cada dataframe ou series localizados nas configurações)
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            dataframes_dir = os.path.join(tmpdirname, "dataframes")
            os.makedirs(dataframes_dir, exist_ok=True)

            # Extrai recursivamente todos os objetos Pandas das configurações
            config = {
                "guarda_arquivos": GerenciadorSAS._extrair_dataframes(
                    guarda_arquivos, dataframes_dir
                ),
                "guarda_graficos": GerenciadorSAS._extrair_dataframes(
                    guarda_graficos, dataframes_dir
                ),
                "guarda_sobreposicoes": GerenciadorSAS._extrair_dataframes(
                    guarda_sobreposicoes, dataframes_dir
                ),
                "guarda_exibicoes_simultaneas": GerenciadorSAS._extrair_dataframes(
                    guarda_exibicoes_simultaneas, dataframes_dir
                ),
                "guarda_scripts": guarda_scripts or {},
            }

            # Salva todos os dicionários (agora sem DataFrames ou elementos UI) em um arquivo JSON
            caminho_json = os.path.join(tmpdirname, "config.json")
            with open(caminho_json, "w", encoding="utf-8") as f:
                json.dump(config, f, cls=NumpyEncoder, indent=4, ensure_ascii=False)

            # Compacta a estrutura e disfarça a extensão com o nome que o usuário escolheu (.sas)
            with zipfile.ZipFile(
                caminho_arquivo_sas, "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for root, dirs, files in os.walk(tmpdirname):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, tmpdirname)
                        zipf.write(file_path, arcname)

    @staticmethod
    def abrir_projeto(caminho_arquivo_sas):
        """
        Lê um arquivo .sas, extrai seus conteúdos e remonta todos os dados,
        incluindo DataFrames e Series.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            with zipfile.ZipFile(caminho_arquivo_sas, "r") as zipf:
                zipf.extractall(tmpdirname)

            caminho_json = os.path.join(tmpdirname, "config.json")
            if not os.path.exists(caminho_json):
                raise FileNotFoundError(
                    "O arquivo selecionado não é um projeto .sas válido (config.json não encontrado)."
                )

            with open(caminho_json, "r", encoding="utf-8") as f:
                config = json.load(f)

            guarda_arquivos = config.get("guarda_arquivos", {})
            guarda_graficos = config.get("guarda_graficos", {})
            guarda_sobreposicoes = config.get("guarda_sobreposicoes", {})
            guarda_exibicoes_simultaneas = config.get(
                "guarda_exibicoes_simultaneas", {}
            )
            guarda_scripts = config.get("guarda_scripts", {})

            dataframes_dir = os.path.join(tmpdirname, "dataframes")

            # Reconstrói os DataFrames varrendo os dicionários recursivamente
            guarda_arquivos = GerenciadorSAS._restaurar_dataframes(
                guarda_arquivos, dataframes_dir
            )
            guarda_graficos = GerenciadorSAS._restaurar_dataframes(
                guarda_graficos, dataframes_dir
            )
            guarda_sobreposicoes = GerenciadorSAS._restaurar_dataframes(
                guarda_sobreposicoes, dataframes_dir
            )
            guarda_exibicoes_simultaneas = GerenciadorSAS._restaurar_dataframes(
                guarda_exibicoes_simultaneas, dataframes_dir
            )

            # Restaura tipos específicos que o JSON perdeu (ex: set)
            for nome_arquivo, config_arq in guarda_arquivos.items():
                if "colunas_modificadas" in config_arq:
                    config_arq["colunas_modificadas"] = set(
                        config_arq["colunas_modificadas"]
                    )

            return (
                guarda_arquivos,
                guarda_graficos,
                guarda_sobreposicoes,
                guarda_exibicoes_simultaneas,
                guarda_scripts,
            )
