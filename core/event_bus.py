from collections import defaultdict
from typing import Callable, Any

class EventBus:
    """
    Sistema central de comunicação baseado no padrão Observer.
    Permite o desacoplamento total entre os sistemas de gameplay.
    """
    def __init__(self):
        self._listeners = defaultdict(list)
        self.debug_mode = False

    def subscribe(self, event_type: str, listener: Callable[[Any], None], priority: int = 0):
        """
        Inscreve um listener para um tipo de evento específico.
        Prioridade maior (número maior) é executada primeiro.
        """
        # Armazena como tupla (prioridade, listener)
        self._listeners[event_type].append((priority, listener))
        # Ordena por prioridade decrescente
        self._listeners[event_type].sort(key=lambda x: x[0], reverse=True)

    def unsubscribe(self, event_type: str, listener: Callable[[Any], None]):
        """Remove a inscrição de um listener."""
        self._listeners[event_type] = [l for l in self._listeners[event_type] if l[1] != listener]

    def emit(self, event_type: str, data: Any = None):
        """Emite um evento para todos os listeners inscritos."""
        if self.debug_mode:
            print(f"[EVENT_BUS] {event_type}: {data}")
            
        for _, listener in self._listeners[event_type]:
            try:
                listener(data)
            except Exception as e:
                print(f"[EVENT_BUS] Erro em {event_type}: {e}")

# Instância global para facilitar o acesso (Singleton-like)
bus = EventBus()
