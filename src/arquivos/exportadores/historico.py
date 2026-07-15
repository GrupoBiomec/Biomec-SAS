import json
from collections import defaultdict


def salvar_historico_processamento(caminho: str, pipelines: dict) -> tuple[bool, str]:
    """
    Grava o dicionário de pipelines no disco no formato estruturado solicitado (TXT ou JSON).
    pipelines: {nome_arquivo: lista_de_steps}
    Retorna uma tupla (sucesso_boolean, mensagem_de_erro_str_se_falhar).
    """
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            if caminho.endswith(".json"):
                json.dump(pipelines, f, indent=4, ensure_ascii=False)
            else:
                for nome_arquivo, pipeline in pipelines.items():
                    f.write("Histórico de Processamento\n")
                    f.write(f"Arquivo: {nome_arquivo}\n")
                    f.write("===================================================\n\n")

                    grupos = defaultdict(list)
                    for step in pipeline:
                        cat = step.get("categoria", "Outros")
                        grupos[cat].append(step)

                    for cat, steps in grupos.items():
                        f.write(f"--- {cat.upper()} ---\n")
                        for idx, step in enumerate(steps, start=1):
                            f.write(f"[{idx}] {step.get('acao', 'Ação Indefinida')}\n")
                            for k, v in step.items():
                                if k not in (
                                    "categoria",
                                    "acao",
                                    "batch_id",
                                    "is_operation_var",
                                ):
                                    f.write(
                                        f"      {k.replace('_', ' ').title()}: {v}\n"
                                    )
                        f.write("\n")
                    f.write("\n")
        return True, ""
    except Exception as e:
        return False, f"Erro ao exportar histórico: {str(e)}"
