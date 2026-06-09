"""
balance — números de balanceamento de combate, data-driven.

Carrega `data/balance.json` uma vez (singleton `balance`) e expõe as seções
`firepower`, `ai` e `shield`. No mesmo espírito do `InputConfig`, é TOLERANTE A
FALHAS: se o arquivo faltar ou estiver corrompido, usa `DEFAULTS` e o jogo nunca
quebra. Chaves ausentes no JSON também caem no default por seção (merge raso).

Permite tuning rápido sem editar código: basta editar `data/balance.json`.
"""
import json
import os
from typing import Any, Dict

# Defaults seguros — espelham data/balance.json. Se o arquivo sumir, o
# balanceamento continua idêntico ao calibrado neste ciclo.
DEFAULTS: Dict[str, Dict[str, Any]] = {
    "firepower": {
        "weight_small": 1.0,
        "weight_medium": 2.0,
        "weight_large": 4.0,
        "exponent": 0.6,
        "fallback": 1.0,
    },
    "ai": {
        "attack_range": 380.0,
        "detection_range": 1000.0,
        "fire_chance_per_tick": 0.022,
        "flee_shield_threshold": 0.0,
        "recover_shield_threshold": 50.0,
    },
    "shield": {
        "base_recharge": 6.0,
    },
    "boost": {
        "force_mult": 2.6,
        "duration": 0.8,
        "cost": 1.0,
        "max_charge": 3.0,
        "recharge_per_s": 0.5,
        "cooldown": 0.4,
    },
}

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "balance.json"
)


class Balance:
    """Container das seções de balanceamento, com merge sobre os defaults."""

    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path
        self.firepower: Dict[str, Any] = {}
        self.ai: Dict[str, Any] = {}
        self.shield: Dict[str, Any] = {}
        self.boost: Dict[str, Any] = {}
        self.load()

    def load(self):
        """(Re)carrega do disco, mesclando sobre os DEFAULTS. Nunca lança."""
        data: Dict[str, Any] = {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {}

        for section, defaults in DEFAULTS.items():
            merged = dict(defaults)
            incoming = data.get(section, {})
            if isinstance(incoming, dict):
                for k, v in incoming.items():
                    if k in merged:  # ignora chaves desconhecidas (ex: _comment)
                        merged[k] = v
            setattr(self, section, merged)


# Singleton global para acesso fácil (como o `bus`).
balance = Balance()
