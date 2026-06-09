"""
Fonte única de hostilidade entre facções (ver ADR 008).

Antes, a tabela de pares hostis estava duplicada em
`CombatManager.hostility_table` e `NPCManager.HOSTILITY`. Este módulo é a
**fonte canônica** — puro (sem pygame), testável headless — reutilizado pela
IA dos NPCs e pelo radar (`visual_engine/radar.py`). Não muda comportamento:
o set abaixo é exatamente o que o `NPCManager` já usava.

Convenções:
  - `HOSTILITY` é direcional: `(atacante, alvo)` significa "atacante hostiliza
    o alvo". A IA usa essa direção para decidir agressão.
  - `is_hostile(a, b)` preserva a semântica direcional da IA.
  - `relation(viewer, other)` é **simétrica** (para coloração do radar):
    olha os dois sentidos e devolve "hostile" / "ally" / "neutral".
"""
from typing import Set, Tuple

# Set canônico de pares hostis (atacante, alvo).
HOSTILITY: Set[Tuple[str, str]] = {
    ("Pirates", "United Humans"), ("Pirates", "Independent"), ("Pirates", "Marth"),
    ("Orcs", "United Humans"),
    ("Marth", "Pirates"),
    ("United Humans", "Pirates"),
}


def is_hostile(attacker_faction: str, target_faction: str) -> bool:
    """True se `attacker_faction` hostiliza `target_faction` (direcional)."""
    return (attacker_faction, target_faction) in HOSTILITY


def relation(viewer_faction: str, other_faction: str) -> str:
    """
    Relação **simétrica** entre quem observa e o alvo, para o radar:
      - "ally"    → mesma facção
      - "hostile" → hostil em qualquer sentido
      - "neutral" → nenhum dos acima
    """
    if viewer_faction == other_faction:
        return "ally"
    if (viewer_faction, other_faction) in HOSTILITY or \
       (other_faction, viewer_faction) in HOSTILITY:
        return "hostile"
    return "neutral"
