import json
import os
from typing import Any, Dict

class DataLoader:
    """
    Gerenciador de carregamento de dados externos (JSON).
    Permite que o jogo seja configurado sem alterar o código.
    """
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._cache: Dict[str, Any] = {}

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Carrega um arquivo JSON do diretório de dados."""
        if filename in self._cache:
            return self._cache[filename]

        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo de dados não encontrado: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self._cache[filename] = data
            return data

    def clear_cache(self):
        """Limpa o cache de dados carregados."""
        self._cache.clear()
