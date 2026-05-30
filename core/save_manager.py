import json
import os
import shutil
from typing import Dict, Any

class SaveManager:
    """
    Gerencia a persistência do estado do jogo.
    Utiliza escrita atômica para evitar corrupção de arquivos.
    """
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def save_game(self, slot: int, data: Dict[str, Any]):
        """Salva os dados do jogo em um slot específico de forma atômica."""
        filename = f"save_slot_{slot}.json"
        temp_path = os.path.join(self.save_dir, f"{filename}.tmp")
        final_path = os.path.join(self.save_dir, filename)

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            # Substituição atômica
            shutil.move(temp_path, final_path)
            print(f"Jogo salvo com sucesso em: {final_path}")
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"Erro ao salvar o jogo: {e}")

    def load_game(self, slot: int) -> Dict[str, Any]:
        """Carrega os dados do jogo de um slot específico."""
        filename = f"save_slot_{slot}.json"
        path = os.path.join(self.save_dir, filename)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo de save não encontrado: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_saves(self):
        """Lista todos os slots de save disponíveis."""
        return [f for f in os.listdir(self.save_dir) if f.endswith(".json")]
