import os
import sys
from PyQt6.QtWidgets import QDialog


def resource_path(relative_path: str) -> str:
    """Resolve o caminho de um recurso para funcionar tanto em desenvolvimento
    quanto no executável empacotado pelo PyInstaller (--onefile).

    Quando o PyInstaller descompacta os arquivos incluídos via --add-data,
    eles ficam em um diretório temporário cujo caminho é armazenado em
    sys._MEIPASS. Em modo de desenvolvimento, o caminho é resolvido
    a partir do diretório raiz do projeto (um nível acima de ``src/``).
    """
    if getattr(sys, "_MEIPASS", None):
        base_path = sys._MEIPASS
    else:
        # Em desenvolvimento: sobe de src/ para a raiz do projeto
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


class PadraoDialog(QDialog):
    """
    Classe base para padronizar os diálogos da aplicação.
    Impede que sejam redimensionáveis pelo usuário e garante
    que não excedam o tamanho da janela principal.
    """

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

    def showEvent(self, event):
        if not hasattr(self, "_padronizado"):
            parent = self.parentWidget()
            if parent:
                # Obtém tamanho atual do diálogo
                w = self.width()
                h = self.height()

                # Obtém limites baseados no pai
                max_w = parent.width()
                max_h = parent.height()

                # Se for maior que o pai, reduz e ajusta
                if w > max_w or h > max_h:
                    w = min(w, max_w)
                    h = min(h, max_h)
                    self.resize(w, h)

                # Fixa o tamanho para o usuário não expandir
                self.setFixedSize(w, h)
            else:
                self.setFixedSize(self.size())

            self._padronizado = True

        super().showEvent(event)
