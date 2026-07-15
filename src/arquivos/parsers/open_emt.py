# ASCII (legível)
# Organizado por tabulação

import pandas as pd
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import os


class TratamentoEMT:  # Le arquivos EMT e cria DataFrame

    def __init__(self):
        self.dataframe = None
        self.file_path = None
        self.nome_arqv = None

    def open_emt_file(self):  # --> BOOLEANO

        try:
            # Abre o diálogo para selecionar o arquivo
            file_path, _ = QFileDialog.getOpenFileName(
                parent=None,
                caption="Abrir Arquivo EMT",
                directory=None,
                filter="Arquivos EMT (*.emt);;Todos os arquivos (*)",
            )

            # Se o usuário cancelou a seleção
            if not file_path:
                return False

            # Tenta carregar o arquivo
            success = self.load_emt_file(file_path)

            if success:
                # Mostra mensagem de sucesso
                QMessageBox.information(
                    None,
                    "Sucesso",
                    f"Arquivo '{self.nome_arqv}' carregado com sucesso!\n",
                )
            return success

        except Exception as e:
            print(f"ERRO: {str(e)}")
            QMessageBox.critical(None, "Erro", f"Erro ao abrir arquivo: {str(e)}")
            return False

    def load_emt_file(self, file_path):  # --> booleano
        """Carrega um arquivo EMT no formato BTS ASCII específico
        Padrao esperado:
        - Linhas 1-5: Cabeçalho
        - Linha 6: Linha vazia
        - Linha 7: Titulo colunas (Item, nome_coluna1, nome_coluna2)
        - Linha 8+: Dados numéricos"""

        try:

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

            self.dataframe = pd.read_csv(
                file_path,
                sep="\t",  # Separador por tabulação
                skiprows=6,  # Pula cabeçalho BTS (linhas 1-6)
                encoding="latin-1",  # Encoding inclui caracteres especiais
            )

            # Salva infos
            self.file_path = file_path
            self.nome_arqv = os.path.basename(file_path)

            # Limpa dados vazios
            self.dataframe = self.dataframe.dropna(
                how="all", axis=0
            )  # Remove linhas vazias
            self.dataframe = self.dataframe.dropna(
                how="all", axis=1
            )  # Remove colunas vazias
            self.dataframe.columns = self.dataframe.columns.str.strip()
            # Reseta o índice
            self.dataframe = self.dataframe.reset_index(drop=True)

            return True

        except Exception as e:
            print(f"Erro ao carregar arquivo EMT: {str(e)}")
            return False

    def get_dataframe(self):
        return self.dataframe

    def get_file_info(self):  # --> dict or none

        if self.dataframe is not None:
            informacoes = {
                "nome_arqv": self.nome_arqv,
                "file_path": self.file_path,
                "arvore": None,
                "linhas": len(self.dataframe),
                "colunas": len(self.dataframe.columns),
                "nomes_colunas": list(self.dataframe.columns),
            }

            header_info = self.get_header_info()
            if header_info:
                informacoes.update(
                    {
                        "format": header_info["format"],
                        "type": header_info["type"],
                        "measure_unit": header_info["measure_unit"],
                        "sequences": header_info["sequences"],
                    }
                )

            return informacoes
        return None

    def is_loaded(self):  # --> booleano
        return self.dataframe is not None

    def get_header_info(self):  # --> dict or none

        if not self.file_path:
            return None

        try:
            with open(self.file_path, "r", encoding="latin-1") as file:
                header_lines = [file.readline().strip() for _ in range(6)]

            header_info = {
                "format": header_lines[0] if len(header_lines) > 0 else "",
                "type": "",
                "measure_unit": "",
                "sequences": "",
            }

            for line in header_lines:
                if line.startswith("Type:"):
                    header_info["type"] = line.replace("Type:", "").strip()
                elif line.startswith("Measure unit:"):
                    header_info["measure_unit"] = line.replace(
                        "Measure unit:", ""
                    ).strip()
                elif line.startswith("Sequences:"):
                    header_info["sequences"] = line.replace("Sequences:", "").strip()

            return header_info

        except Exception as e:
            print(f"Erro ao ler cabeçalho: {str(e)}")
            return None

    # Integração com a main
    def extrai_infos(self):
        sucesso = self.open_emt_file()

        if sucesso:
            df = self.get_dataframe()
            conteudo = self.get_file_info()
            cabecalho = self.get_header_info()
            return df, conteudo, cabecalho
        else:
            return None, None, None
