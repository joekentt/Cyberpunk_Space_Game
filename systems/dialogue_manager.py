from core.event_bus import bus
from typing import Dict, Any, List, Optional

class DialogueManager:
    """
    Gerencia diálogos dinâmicos e hooks para integração com IA de voz/LLM.
    """
    def __init__(self):
        self.dialogue_history = []
        self.voice_enabled = False
        self.llm_hook_enabled = False
        
        # Templates de diálogos rápidos (Bark System)
        self.barks = {
            "COMBAT_START": ["Alvo na mira!", "Iniciando protocolo de ataque.", "Você escolheu o dia errado para voar."],
            "SHIELD_LOW": ["Escudos em 20%!", "Energia falhando!", "Não vou aguentar muito mais!"],
            "FLEEING": ["Retirada estratégica!", "Isso não vale o risco.", "Voltarei com reforços!"],
            "MISSION_ACCEPTED": ["Contrato assinado. Vamos ao trabalho.", "Dinheiro fácil. Estou a caminho."],
        }
        
        bus.subscribe("NPC_STATE_CHANGED", self.on_npc_state_changed)
        bus.subscribe("MISSION_ACCEPTED", lambda m: self.play_dialogue("MISSION_ACCEPTED", "Contractor"))

    def on_npc_state_changed(self, data: Dict[str, Any]):
        npc_id = data["npc_id"]
        new_state = data["new_state"]
        
        if new_state == "ATTACK":
            self.play_dialogue("COMBAT_START", f"NPC_{npc_id}")
        elif new_state == "FLEE":
            self.play_dialogue("FLEEING", f"NPC_{npc_id}")

    def play_dialogue(self, category: str, speaker: str, custom_text: Optional[str] = None):
        """
        Executa um diálogo. Se custom_text for fornecido, usa ele (ex: vindo de um LLM).
        Caso contrário, escolhe um bark aleatório da categoria.
        """
        import random
        text = custom_text or random.choice(self.barks.get(category, ["..."]))
        
        dialogue_entry = {
            "speaker": speaker,
            "text": text,
            "category": category
        }
        
        self.dialogue_history.append(dialogue_entry)
        
        # Emite evento para a UI ou sistema de Voz
        bus.emit("DIALOGUE_TRIGGERED", dialogue_entry)
        
        if self.voice_enabled:
            self._trigger_voice_synthesis(text)

    def _trigger_voice_synthesis(self, text: str):
        """Hook para integração futura com APIs de Text-to-Speech."""
        bus.emit("VOICE_SYNTHESIS_REQUESTED", {"text": text})

    def request_llm_response(self, prompt: str, context: Dict[str, Any]):
        """Hook para integração futura com LLMs para diálogos dinâmicos."""
        if self.llm_hook_enabled:
            bus.emit("LLM_DIALOGUE_REQUESTED", {"prompt": prompt, "context": context})
