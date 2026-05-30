"""
InputConfig — mapeamento configurável de ação → tecla (keybindings).

O módulo é PURO (não depende de pygame) para poder ser testado headless.
Armazena cada ação associada a um NOME de tecla no formato do pygame
(`pygame.key.name(code)`), ex: "w", "space", "escape". A conversão
nome ↔ keycode é responsabilidade da camada de input (main_pygame.py).

Persistência: JSON em config/keybinds.json com escrita atômica (arquivo
temporário + os.replace), no mesmo espírito do SaveManager.

Se o arquivo não existir ou estiver corrompido, os padrões são usados —
o input atual nunca quebra por falta de configuração.
"""
import os
import json
from typing import Dict, List


class InputConfig:
    # Ordem das ações = ordem de exibição na tela de configuração.
    # Padrões respeitam o esquema já estabelecido (W/S/A/D/Q/E/ESPAÇO/F/ESC).
    DEFAULTS: Dict[str, str] = {
        "thrust_forward": "w",
        "thrust_back": "s",
        "rotate_left": "a",
        "rotate_right": "d",
        "strafe_left": "q",
        "strafe_right": "e",
        "shoot": "space",
        "dock_toggle": "f",
        "pause": "escape",
    }

    # Rótulos amigáveis para a UI de rebind.
    LABELS: Dict[str, str] = {
        "thrust_forward": "Acelerar (frente)",
        "thrust_back": "Frear / Ré",
        "rotate_left": "Girar à esquerda",
        "rotate_right": "Girar à direita",
        "strafe_left": "Strafe esquerda",
        "strafe_right": "Strafe direita",
        "shoot": "Disparar",
        "dock_toggle": "Acoplar / Desacoplar",
        "pause": "Pausar",
    }

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join("config", "keybinds.json")
        self.path = config_path
        self.bindings: Dict[str, str] = dict(self.DEFAULTS)
        self.load()

    # ---- propriedades ------------------------------------------------

    @property
    def ACTIONS(self) -> List[str]:
        """Lista ordenada de ações (para iterar na UI)."""
        return list(self.DEFAULTS.keys())

    def label(self, action: str) -> str:
        return self.LABELS.get(action, action)

    # ---- acesso ------------------------------------------------------

    def get(self, action: str) -> str:
        """Nome da tecla associada à ação (ou o default, ou '')."""
        return self.bindings.get(action, self.DEFAULTS.get(action, ""))

    def set(self, action: str, key_name: str):
        """Associa uma tecla a uma ação. Ignora ações desconhecidas."""
        if action in self.DEFAULTS and isinstance(key_name, str) and key_name:
            self.bindings[action] = key_name

    def get_action_for_key(self, key_name: str):
        """Retorna a primeira ação ligada a uma tecla, ou None."""
        for action, key in self.bindings.items():
            if key == key_name:
                return action
        return None

    def conflicts(self) -> Dict[str, List[str]]:
        """
        Retorna {tecla: [ações...]} apenas para teclas usadas por MAIS de
        uma ação. Dicionário vazio = sem conflitos.
        """
        seen: Dict[str, List[str]] = {}
        for action, key in self.bindings.items():
            seen.setdefault(key, []).append(action)
        return {key: acts for key, acts in seen.items() if len(acts) > 1}

    def reset_to_defaults(self):
        self.bindings = dict(self.DEFAULTS)

    # ---- persistência ------------------------------------------------

    def load(self) -> Dict[str, str]:
        """
        Carrega de disco, mesclando sobre os padrões. Tolerante a falhas:
        arquivo ausente ou inválido → mantém os padrões.
        """
        self.bindings = dict(self.DEFAULTS)
        if not os.path.exists(self.path):
            return self.bindings
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for action, key in data.items():
                    if action in self.DEFAULTS and isinstance(key, str) and key:
                        self.bindings[action] = key
        except (json.JSONDecodeError, OSError):
            # Configuração corrompida: silenciosamente cai nos padrões.
            self.bindings = dict(self.DEFAULTS)
        return self.bindings

    def save(self):
        """Escreve em disco atomicamente (temp + os.replace)."""
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        tmp_path = self.path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.bindings, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.path)  # substituição atômica
        except OSError as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            print(f"[InputConfig] Erro ao salvar keybinds: {e}")
