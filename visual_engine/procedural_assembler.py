"""
ProceduralShipAssembler
-----------------------
Orquestra a geração de sprites de naves:
  1. Pega paleta da facção (PaletteManager)
  2. Gera imagem PIL via SpriteGenerator
  3. Cacheia o resultado por (class, faction, seed)
  4. Opcionalmente converte para pygame.Surface se pygame estiver disponível

Funciona em modo "headless" (sem pygame) para testes e geração de assets;
e em modo "live" dentro do main_pygame.py.
"""

from PIL import Image
from visual_engine.palette_manager import PaletteManager
from visual_engine.sprite_generator import SpriteGenerator


class ProceduralShipAssembler:
    def __init__(self):
        self.palette_mgr = PaletteManager()
        self.sprite_gen = SpriteGenerator()
        self._pil_cache = {}
        self._surface_cache = {}

    # -- Modo headless: retorna PIL.Image -------------------------------

    def get_ship_image(self, ship_entity, seed: int = 0) -> Image.Image:
        """Retorna a imagem PIL (RGBA) do sprite da nave."""
        cache_key = self._cache_key(ship_entity, seed)
        if cache_key in self._pil_cache:
            return self._pil_cache[cache_key]

        palette = self.palette_mgr.get_palette(getattr(ship_entity, "faction", "Independent"))
        img = self.sprite_gen.generate_ship_sprite(
            ship_class=ship_entity.ship_class,
            palette=palette,
            seed=seed,
            model_id=getattr(ship_entity, "model_id", None),
        )
        self._pil_cache[cache_key] = img
        return img

    # -- Modo live (pygame): retorna Surface ----------------------------

    def get_ship_sprite(self, ship_entity, seed: int = 0):
        """
        Retorna um pygame.Surface pronto para renderizar.
        Lança ImportError se pygame não estiver disponível.
        """
        cache_key = self._cache_key(ship_entity, seed)
        if cache_key in self._surface_cache:
            return self._surface_cache[cache_key]

        import pygame  # importado preguiçosamente para permitir uso headless
        pil_img = self.get_ship_image(ship_entity, seed)

        mode = pil_img.mode
        size = pil_img.size
        data = pil_img.tobytes()
        surface = pygame.image.fromstring(data, size, mode).convert_alpha()

        self._surface_cache[cache_key] = surface
        return surface

    # -- Cache key ------------------------------------------------------

    def _cache_key(self, ship_entity, seed: int):
        return (
            getattr(ship_entity, "model_id", None) or getattr(ship_entity, "ship_class", "Small"),
            getattr(ship_entity, "faction", "Independent"),
            seed,
        )

    def clear_cache(self):
        self._pil_cache.clear()
        self._surface_cache.clear()
