import pygame
import random
from typing import Tuple, List

class Camera:
    def __init__(self, width: int, height: int):
        self.offset = [0, 0]
        self.width = width
        self.height = height

    def follow(self, target_pos: List[float], dt: float):
        """
        Suaviza o movimento da câmera para seguir o alvo.
        """
        lerp_speed = 5.0
        target_offset_x = target_pos[0] - self.width / 2
        target_offset_y = target_pos[1] - self.height / 2
        
        self.offset[0] += (target_offset_x - self.offset[0]) * lerp_speed * dt
        self.offset[1] += (target_offset_y - self.offset[1]) * lerp_speed * dt

class ParallaxBackground:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers = []
        # Camada 1: Estrelas distantes (lentas)
        self.layers.append(self._generate_stars(100, 0.1))
        # Camada 2: Estrelas médias
        self.layers.append(self._generate_stars(50, 0.3))
        # Camada 3: Estrelas próximas (rápidas)
        self.layers.append(self._generate_stars(20, 0.6))

    def _generate_stars(self, count: int, speed: float) -> dict:
        stars = []
        for _ in range(count):
            stars.append({
                "pos": [random.randint(0, self.width), random.randint(0, self.height)],
                "size": random.randint(1, 2)
            })
        return {"stars": stars, "speed": speed}

    def draw(self, screen: pygame.Surface, camera_offset: Tuple[float, float]):
        for layer in self.layers:
            speed = layer["speed"]
            for star in layer["stars"]:
                # Aplica o efeito de parallax
                x = (star["pos"][0] - camera_offset[0] * speed) % self.width
                y = (star["pos"][1] - camera_offset[1] * speed) % self.height
                
                color = (200, 200, 255) if speed > 0.3 else (100, 100, 150)
                pygame.draw.circle(screen, color, (int(x), int(y)), star["size"])
