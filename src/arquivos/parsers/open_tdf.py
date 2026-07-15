import pandas as pd
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import os
from typing import Optional, Dict, Tuple
from basictdf import Tdf

# Mapeamento centralizado de unidades do formato TDF (BTS Bioengineering)
# O formato TDF armazena TODOS os dados no Sistema Internacional (SI).
# A biblioteca basictdf aplica automaticamente gain/offset e retorna valores em SI.
# NÃO existem atributos de unidade explícitos no binário – são convenção do formato.
UNIDADES_TDF = {
    "3d_posicao": "m",  # Coordenadas X, Y, Z dos marcadores
    "forca": "N",  # Componentes de força Fx, Fy, Fz
    "cop": "m",  # Centro de Pressão (CoPx, CoPy)
    "torque": "N.m",  # Componentes de torque/momento
    "emg": "V",  # Sinais eletromiográficos
    "tempo": "s",  # Tempo (calculado via frequência em Hz)
}


class TratamentoTDF:

    def __init__(self):
        self.dataframe = None
        self.file_path = None
        self.nome_arqv = None
        self.unidades_colunas = {}  # {nome_coluna: unidade}

    def open_tdf_file(self) -> bool:
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                parent=None,
                caption="Abrir Arquivo TDF",
                directory=None,
                filter="Arquivos TDF (*.tdf);;Todos os arquivos (*)",
            )

            if not file_path:
                return False

            success = self.load_tdf_file(file_path)

            if success:
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

    def load_tdf_file(self, file_path: str) -> bool:
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

            self.file_path = file_path
            self.nome_arqv = os.path.basename(file_path)

            self.dataframe, self.unidades_colunas = self._parse_tdf_file(file_path)
            return True

        except ValueError:
            raise  # Propaga para o chamador exibir mensagem ao usuário
        except Exception as e:
            print(f"Erro ao carregar arquivo TDF: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    def get_dataframe(self):
        return self.dataframe

    def get_file_info(self) -> Optional[Dict]:
        if self.dataframe is not None:
            return {
                "nome_arqv": self.nome_arqv,
                "file_path": self.file_path,
                "arvore": None,
                "linhas": len(self.dataframe),
                "colunas": len(self.dataframe.columns),
                "nomes_colunas": list(self.dataframe.columns),
            }
        return None

    def get_header_info(self) -> Optional[Dict]:
        if not self.file_path:
            return None

        unidades = set(self.unidades_colunas.values())

        is_3d = "m" in unidades  # posições 3D em metros
        is_emg = "V" in unidades  # EMG em Volts
        is_force = "N" in unidades  # Forças em Newtons

        types_found = []
        if is_3d:
            types_found.append("3D")
        if is_emg:
            types_found.append("EMG")
        if is_force:
            types_found.append("Force")

        type_str = " + ".join(types_found) if types_found else "Unknown Data"

        return {
            "format": "BTS TDF Binary",
            "type": type_str,
            "measure_unit": "",
            "sequences": (
                str(len(self.dataframe)) if self.dataframe is not None else "0"
            ),
        }

    def is_loaded(self) -> bool:
        return self.dataframe is not None

    def extrai_infos(self) -> Tuple:
        sucesso = self.open_tdf_file()

        if sucesso:
            df = self.get_dataframe()
            conteudo = self.get_file_info()
            cabecalho = self.get_header_info()
            return df, conteudo, cabecalho, self.unidades_colunas
        else:
            return None, None, None, None

    @staticmethod
    def _obter_unidades_tdf() -> Dict[str, str]:
        """Retorna o mapeamento de unidades convencionais do formato TDF.

        O formato TDF da BTS Bioengineering armazena dados nativamente em SI.
        A biblioteca basictdf NÃO expõe atributos de unidade explícitos —
        as unidades são convenção do formato binário.

        Returns:
            Dicionário com as chaves de grandeza e suas unidades SI.
        """
        return UNIDADES_TDF.copy()

    def _parse_tdf_file(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
        tdf = Tdf(file_path)
        dfs_to_merge = []
        unidades_colunas = {}  # {nome_coluna: unidade}

        # Unidades do formato TDF (SI)
        u = UNIDADES_TDF

        # 1. Processa dados 3D (Cinemática)
        if hasattr(tdf, "has_data3D") and tdf.has_data3D:
            data3D = tdf.data3D
            n_frames = data3D.nFrames
            frequency = data3D.frequency
            start_time = getattr(data3D, "startTime", 0.0)

            data_dict_3d = {
                "time": [start_time + (i / frequency) for i in range(n_frames)]
            }

            un_pos = u["3d_posicao"]  # m
            for track in data3D.tracks:
                label = track.label
                col_x = f"{label}_x"
                col_y = f"{label}_y"
                col_z = f"{label}_z"
                data_dict_3d[col_x] = track.X
                data_dict_3d[col_y] = track.Y
                data_dict_3d[col_z] = track.Z
                unidades_colunas[col_x] = un_pos
                unidades_colunas[col_y] = un_pos
                unidades_colunas[col_z] = un_pos

            df_3d = pd.DataFrame(data_dict_3d)
            dfs_to_merge.append(df_3d)

        # 2. Processa Dados EMG (Eletromiografia)
        if hasattr(tdf, "has_emg") and tdf.has_emg:
            emg = tdf.emg
            n_samples = emg.nSamples
            frequency = emg.frequency
            start_time = getattr(emg, "startTime", 0.0)

            data_dict_emg = {
                "time": [start_time + (i / frequency) for i in range(n_samples)]
            }

            un_emg = u["emg"]  # V
            for signal in emg:
                label = signal.label
                data_dict_emg[label] = signal.data
                unidades_colunas[label] = un_emg

            df_emg = pd.DataFrame(data_dict_emg)
            dfs_to_merge.append(df_emg)

        # 3. Processa Dados da Plataforma de Força (Dinâmica)

        #    Formato processado (forceAndTorqueData, tipo 12)
        if hasattr(tdf, "has_force_and_torque") and tdf.has_force_and_torque:
            force_block = tdf.force_and_torque
            n_frames = force_block.nFrames
            frequency = force_block.frequency
            start_time = getattr(force_block, "startTime", 0.0)

            data_dict_force = {
                "time": [start_time + (i / frequency) for i in range(n_frames)]
            }

            un_forca = u["forca"]  # N
            un_cop = u["cop"]  # m
            un_torque = u["torque"]  # N.m

            for channel, plat in enumerate(force_block.tracks):

                col_fx = f"Plat{channel}_Fx"
                col_fy = f"Plat{channel}_Fy"
                col_fz = f"Plat{channel}_Fz"
                data_dict_force[col_fx] = plat.force[:, 0]
                data_dict_force[col_fy] = plat.force[:, 1]
                data_dict_force[col_fz] = plat.force[:, 2]
                unidades_colunas[col_fx] = un_forca
                unidades_colunas[col_fy] = un_forca
                unidades_colunas[col_fz] = un_forca

                col_copx = f"Plat{channel}_CoPx"
                col_copy = f"Plat{channel}_CoPy"
                data_dict_force[col_copx] = plat.application_point[:, 0]
                data_dict_force[col_copy] = plat.application_point[:, 1]
                unidades_colunas[col_copx] = un_cop
                unidades_colunas[col_copy] = un_cop

                col_tz = f"Plat{channel}_Tz"
                data_dict_force[col_tz] = plat.torque[:, 2]
                unidades_colunas[col_tz] = un_torque

            df_force = pd.DataFrame(data_dict_force)
            dfs_to_merge.append(df_force)

        else:
            # Fallback: Formato bruto (forcePlatformsData, tipo 9)
            # Arquivos TDF nao trackeados armazenam força neste bloco
            from basictdf.tdfForcePlatformsData import ForcePlatformsDataBlock

            force_raw_block = None
            for blk in tdf.blocks:
                if isinstance(blk, ForcePlatformsDataBlock) and blk.nBytes > 0:
                    force_raw_block = blk
                    break

            if force_raw_block is not None:
                n_frames = force_raw_block.n_frames
                frequency = int(force_raw_block.frequency)
                start_time = float(getattr(force_raw_block, "start_time", 0.0))

                data_dict_force = {
                    "time": [start_time + (i / frequency) for i in range(n_frames)]
                }

                un_forca = u["forca"]  # N
                un_cop = u["cop"]  # m
                un_torque = u["torque"]  # N.m

                for channel, plat in enumerate(force_raw_block._platforms):
                    col_fx = f"Plat{channel}_Fx"
                    col_fy = f"Plat{channel}_Fy"
                    col_fz = f"Plat{channel}_Fz"
                    data_dict_force[col_fx] = plat.force[:, 0]
                    data_dict_force[col_fy] = plat.force[:, 1]
                    data_dict_force[col_fz] = plat.force[:, 2]
                    unidades_colunas[col_fx] = un_forca
                    unidades_colunas[col_fy] = un_forca
                    unidades_colunas[col_fz] = un_forca

                    col_copx = f"Plat{channel}_CoPx"
                    col_copy = f"Plat{channel}_CoPy"
                    data_dict_force[col_copx] = plat.application_point[:, 0]
                    data_dict_force[col_copy] = plat.application_point[:, 1]
                    unidades_colunas[col_copx] = un_cop
                    unidades_colunas[col_copy] = un_cop

                    col_tz = f"Plat{channel}_Tz"
                    data_dict_force[col_tz] = plat.torque
                    unidades_colunas[col_tz] = un_torque

                df_force = pd.DataFrame(data_dict_force)
                dfs_to_merge.append(df_force)

        # Unidades das colunas padrão
        unidades_colunas["time"] = "s"
        unidades_colunas["frame"] = "frames"

        # Verificação de segurança
        if not dfs_to_merge:
            raise ValueError(
                "O arquivo TDF não contém dados 3D, EMG ou de Plataforma de Força."
            )

        # Lógica de Merge Unificada
        if len(dfs_to_merge) == 1:
            final_df = dfs_to_merge[0]
        else:
            for df in dfs_to_merge:
                df["time_round"] = df["time"].round(4)

            final_df = dfs_to_merge[0]
            for i in range(1, len(dfs_to_merge)):
                final_df = pd.merge(
                    final_df,
                    dfs_to_merge[i],
                    on="time_round",
                    how="outer",
                    suffixes=("", "_dup"),
                )

                if "time_dup" in final_df.columns:
                    final_df["time"] = final_df["time"].fillna(final_df["time_dup"])
                    final_df = final_df.drop(columns=["time_dup"])

            final_df = final_df.drop(columns=["time_round"])

        # Limpeza e ordenação
        final_df = final_df.sort_values("time").reset_index(drop=True)
        final_df.insert(0, "frame", final_df.index)

        cols = list(final_df.columns)
        cols.remove("frame")
        cols.remove("time")
        final_df = final_df[["frame", "time"] + cols]

        return final_df, unidades_colunas
