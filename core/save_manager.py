import json
import os
import shutil
from typing import Any, Dict, Optional

class SaveManager:
    """
    Gerencia a persistência do estado do jogo.
    Utiliza escrita atômica para evitar corrupção de arquivos.
    """
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def _slot_path(self, slot: int) -> str:
        return os.path.join(self.save_dir, f"save_slot_{slot}.json")

    def save_game(self, slot: int, data: Dict[str, Any]):
        """Salva os dados do jogo em um slot específico de forma atômica."""
        final_path = self._slot_path(slot)
        temp_path = final_path + ".tmp"

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
        path = self._slot_path(slot)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo de save não encontrado: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_saves(self):
        """Lista todos os slots de save disponíveis."""
        return [f for f in os.listdir(self.save_dir) if f.endswith(".json")]

    def delete_save(self, slot: int) -> bool:
        """
        Remove o save do slot, se existir. Retorna True se removeu.
        Slot inexistente ou erro de I/O não crasham (retorna False).
        """
        path = self._slot_path(slot)
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True
        except OSError:
            pass
        return False

    def save_metadata(self, slot: int) -> Optional[Dict[str, Any]]:
        """
        Lê apenas o "cabeçalho" do save para a UI de slots: piloto, créditos,
        progresso e timestamp — SEM aplicar o jogo. Tolerante a falhas e a
        formatos antigos (saves v1/v2 sem `pilot`/`saved_at`/`progression`
        caem nos defaults). Retorna None se o slot estiver vazio ou corrompido.
        """
        path = self._slot_path(slot)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return None
        except (json.JSONDecodeError, OSError):
            return None

        pilot = payload.get("pilot")
        pilot_name = pilot.get("name", "Piloto") if isinstance(pilot, dict) else "Piloto"
        prog = payload.get("progression")
        prog = prog if isinstance(prog, dict) else {}
        return {
            "slot": slot,
            "version": payload.get("version", 1),
            "pilot_name": pilot_name,
            "credits": int(payload.get("credits", 0)),
            "saved_at": payload.get("saved_at"),
            "progress": {
                "bounties_completed": int(prog.get("bounties_completed", 0)),
                "game_completed": bool(prog.get("game_completed", False)),
            },
        }
