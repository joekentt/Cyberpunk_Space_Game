"""
AudioManager — consumidor PURO de eventos do EventBus (ver ADR 009).

Nenhum sistema de gameplay conhece áudio: eles já emitem eventos
(`WEAPON_FIRED`, `PROJECTILE_HIT`, `SHIP_DESTROYED`, `DOCKED`,
`BOOST_ACTIVATED`, `MISSION_COMPLETED`, `GAME_COMPLETED`, `PIPS_CHANGED`).
O `AudioManager` apenas mapeia evento → som e toca.

**Tolerante a falhas** (no espírito do `InputConfig`/`balance`): se
`pygame.mixer` não estiver inicializado (CI headless, sem device) ou um arquivo
faltar, o jogo continua **sem som e sem crashar**.

Divisão de responsabilidade (armadilha do mixer):
  - `pygame.mixer.init()` é chamado UMA vez no boot do jogo (`main_pygame`),
    não por mundo.
  - O `AudioManager` é criado por mundo (`_build_world_systems`, ADR 005): só
    carrega os samples e se inscreve no bus. Como o `bus._listeners.clear()`
    roda antes de recriar, não há duplicação de sons ao reiniciar o jogo.

Testabilidade: aceita injeção de `play_fn` (default = tocar de verdade; no
teste = registrar chamadas) e `time_fn` (default = `time.monotonic`), evitando
qualquer dependência de hardware de áudio.
"""
import os
import json
import time
from typing import Any, Callable, Dict, Optional

from core.event_bus import bus

# Eventos de gameplay que o áudio escuta (não conhece nada além disso).
AUDIO_EVENTS = (
    "WEAPON_FIRED",
    "PROJECTILE_HIT",
    "SHIP_DESTROYED",
    "DOCKED",
    "BOOST_ACTIVATED",
    "MISSION_COMPLETED",
    "GAME_COMPLETED",
    "PIPS_CHANGED",
)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_AUDIO_DIR = os.path.join(_BASE, "assets", "audio")
_DEFAULT_CONFIG = os.path.join(_BASE, "data", "audio.json")


class AudioManager:
    def __init__(self,
                 audio_dir: Optional[str] = None,
                 config_path: Optional[str] = None,
                 play_fn: Optional[Callable[[str, float], None]] = None,
                 time_fn: Optional[Callable[[], float]] = None,
                 enabled: Optional[bool] = None):
        self.audio_dir = audio_dir or _DEFAULT_AUDIO_DIR
        self.config_path = config_path or _DEFAULT_CONFIG
        self._time = time_fn or time.monotonic

        self.master_volume: float = 0.8
        self.muted: bool = False
        self.sounds_cfg: Dict[str, Dict[str, Any]] = {}
        self._samples: Dict[str, Any] = {}          # evt -> pygame.mixer.Sound
        self._last_play: Dict[str, float] = {}       # evt -> instante do último play

        self._load_config()

        # `enabled` força o estado (testes). Senão, depende do mixer disponível.
        self.enabled = self._mixer_ready() if enabled is None else enabled
        if self.enabled:
            self._load_samples()

        self._play_fn = play_fn or self._default_play
        self._subscribe()

    # ------------------------------------------------------------------ config
    def _load_config(self):
        """Carrega data/audio.json com tolerância total a falhas."""
        master = 0.8
        sounds: Dict[str, Dict[str, Any]] = {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                master = float(data.get("master_volume", 0.8))
                s = data.get("sounds", {})
                if isinstance(s, dict):
                    sounds = {k: v for k, v in s.items() if isinstance(v, dict)}
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError, TypeError):
            pass
        self.master_volume = master
        self.sounds_cfg = sounds

    # ------------------------------------------------------------------ mixer
    @staticmethod
    def _mixer_ready() -> bool:
        """True se o pygame.mixer estiver inicializado (device disponível)."""
        try:
            import pygame
            return pygame.mixer.get_init() is not None
        except Exception:
            return False

    def _load_samples(self):
        """Pré-carrega os Sounds existentes (latência baixa no play)."""
        try:
            import pygame
        except Exception:
            self.enabled = False
            return
        for evt, cfg in self.sounds_cfg.items():
            fname = cfg.get("file")
            if not fname:
                continue
            path = os.path.join(self.audio_dir, fname)
            if not os.path.isfile(path):
                # Arquivo faltando: ignora esta entrada (sem crash).
                continue
            try:
                self._samples[evt] = pygame.mixer.Sound(path)
            except Exception:
                # Sample corrompido/incompatível: ignora, segue sem som.
                continue

    # ------------------------------------------------------------------ play
    def _default_play(self, evt: str, volume: float):
        """Play real (no-op se desabilitado, mudo ou sem sample)."""
        if not self.enabled or self.muted:
            return
        snd = self._samples.get(evt)
        if snd is None:
            return
        try:
            snd.set_volume(max(0.0, min(1.0, volume)))
            snd.play()
        except Exception:
            pass

    def _handle(self, evt: str):
        """Decide tocar `evt`: respeita cooldown e calcula o volume final."""
        cfg = self.sounds_cfg.get(evt)
        if cfg is None:
            return
        cd = float(cfg.get("cooldown", 0.0) or 0.0)
        now = self._time()
        if cd > 0.0:
            last = self._last_play.get(evt)
            if last is not None and (now - last) < cd:
                return
        self._last_play[evt] = now
        volume = self.master_volume * float(cfg.get("volume", 1.0))
        self._play_fn(evt, volume)

    # ------------------------------------------------------------------ bus
    def _subscribe(self):
        """Inscreve um handler por evento do mapa configurado."""
        for evt in self.sounds_cfg.keys():
            bus.subscribe(evt, self._make_handler(evt))

    def _make_handler(self, evt: str) -> Callable[[Any], None]:
        def handler(_data):
            self._handle(evt)
        return handler

    # ------------------------------------------------------------------ API futura (settings)
    def set_master_volume(self, v: float):
        self.master_volume = max(0.0, min(1.0, float(v)))

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted
