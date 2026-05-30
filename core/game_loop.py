import time
from typing import List, Protocol

class System(Protocol):
    """Protocolo que define a interface básica para sistemas do jogo."""
    def update(self, dt: float):
        ...

class GameLoop:
    """
    Controlador central do loop de jogo.
    Gerencia a atualização dos sistemas e o tempo entre frames (dt).
    """
    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps
        self.is_running = False
        self.systems: List[System] = []

    def add_system(self, system: System):
        """Adiciona um sistema ao loop de atualização."""
        self.systems.append(system)

    def start(self):
        """Inicia o loop principal."""
        self.is_running = True
        last_time = time.perf_counter()

        print(f"GameLoop iniciado a {self.target_fps} FPS.")
        
        try:
            while self.is_running:
                current_time = time.perf_counter()
                dt = current_time - last_time
                
                # Simulação de tick fixo (simplificado para o MVP)
                if dt >= self.frame_time:
                    self._update(dt)
                    last_time = current_time
                else:
                    # Pequena pausa para não sobrecarregar a CPU
                    time.sleep(0.001)
        except KeyboardInterrupt:
            self.stop()

    def _update(self, dt: float):
        """Atualiza todos os sistemas registrados."""
        for system in self.systems:
            system.update(dt)

    def stop(self):
        """Para o loop principal."""
        self.is_running = False
        print("GameLoop parado.")
