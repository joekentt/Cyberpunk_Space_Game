"""
Teste headless do AudioManager (ADR 009).

Roda SEM exigir device de som. Valida:
  1. Inicializa sem crashar mesmo com pygame.mixer indisponível (enabled=False).
  2. Emitir cada evento do mapa NÃO levanta exceção (áudio off = no-op).
  3. O mapa carregado de data/audio.json corresponde aos eventos esperados.
  4. Cooldown: dois WEAPON_FIRED em sequência rápida = 1 play; após o cooldown,
     toca de novo (play_fn e time_fn injetados — sem hardware).
  5. Arquivo inexistente no mapa → entrada ignorada, sem crash.
  6. Recriar o AudioManager (novo mundo) após limpar o bus NÃO duplica plays.
  7. Variantes por payload: BOOST_ACTIVATED com model_id conhecido toca o
     boost daquela nave; desconhecido/ausente cai no arquivo padrão.
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import bus
from systems.audio_manager import AudioManager, AUDIO_EVENTS


def main():
    print("=" * 60)
    print("Teste de AudioManager (ADR 009)")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1) Init sem crash com áudio desabilitado
    # ------------------------------------------------------------------
    print("\n[1] Init com áudio desabilitado")
    bus._listeners.clear()
    am = AudioManager(enabled=False)
    assert am.enabled is False
    assert isinstance(am.sounds_cfg, dict) and len(am.sounds_cfg) > 0
    print(f"  ✓ inicializou (enabled=False), {len(am.sounds_cfg)} sons mapeados")

    # ------------------------------------------------------------------
    # 2) Emitir todos os eventos não levanta exceção (no-op com áudio off)
    # ------------------------------------------------------------------
    print("\n[2] Emitir eventos com áudio off = no-op sem exceção")
    for evt in AUDIO_EVENTS:
        bus.emit(evt, {"dummy": True})
    print(f"  ✓ {len(AUDIO_EVENTS)} eventos emitidos sem crash")

    # ------------------------------------------------------------------
    # 3) Mapa carregado corresponde aos eventos esperados
    # ------------------------------------------------------------------
    print("\n[3] Mapa data/audio.json bate com os eventos esperados")
    for evt in AUDIO_EVENTS:
        assert evt in am.sounds_cfg, f"evento {evt} ausente no audio.json"
        assert "file" in am.sounds_cfg[evt], f"{evt} sem 'file'"
    print(f"  ✓ todos os {len(AUDIO_EVENTS)} eventos presentes com 'file'")

    # ------------------------------------------------------------------
    # 4) Cooldown com play_fn e time_fn injetados
    # ------------------------------------------------------------------
    print("\n[4] Cooldown bloqueia plays em sequência rápida")
    bus._listeners.clear()
    clock = {"t": 0.0}
    plays = []
    am4 = AudioManager(
        enabled=False,                       # default play seria no-op; usamos o fake
        play_fn=lambda evt, vol, fname: plays.append((evt, vol, fname)),
        time_fn=lambda: clock["t"],
    )
    cd = float(am4.sounds_cfg["WEAPON_FIRED"].get("cooldown", 0.0))
    assert cd > 0.0, "WEAPON_FIRED deveria ter cooldown para este teste"

    # Dois tiros no mesmo instante → só 1 play
    bus.emit("WEAPON_FIRED", {})
    bus.emit("WEAPON_FIRED", {})
    assert len(plays) == 1, f"esperado 1 play, veio {len(plays)}"
    # Volume = master * volume da entrada
    exp_vol = am4.master_volume * am4.sounds_cfg["WEAPON_FIRED"]["volume"]
    assert abs(plays[0][1] - exp_vol) < 1e-9, plays[0]

    # Avança o relógio além do cooldown → toca de novo
    clock["t"] += cd + 0.001
    bus.emit("WEAPON_FIRED", {})
    assert len(plays) == 2, f"após cooldown deveria tocar de novo: {len(plays)}"
    print(f"  ✓ 2 emits rápidos → 1 play; após {cd:.2f}s → 2º play (vol={plays[0][1]:.3f})")

    # Evento sem cooldown toca sempre
    plays.clear()
    bus.emit("SHIP_DESTROYED", {})
    bus.emit("SHIP_DESTROYED", {})
    assert len(plays) == 2, "SHIP_DESTROYED (sem cooldown) deveria tocar sempre"
    print("  ✓ evento sem cooldown toca a cada emit")

    # ------------------------------------------------------------------
    # 5) Arquivo inexistente no mapa → ignorado, sem crash
    # ------------------------------------------------------------------
    print("\n[5] Arquivo inexistente no mapa é ignorado")
    tmpdir = tempfile.mkdtemp(prefix="audio_test_")
    cfg_path = os.path.join(tmpdir, "audio.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump({
            "master_volume": 1.0,
            "sounds": {
                "WEAPON_FIRED": {"file": "nao_existe_xyz.wav", "volume": 0.5},
            },
        }, f)
    bus._listeners.clear()
    got = []
    # Tenta habilitar (carrega samples); arquivo não existe → _samples vazio.
    am5 = AudioManager(
        audio_dir=tmpdir, config_path=cfg_path,
        enabled=True,                         # força tentativa de load de samples
        play_fn=lambda evt, vol, fname: got.append(evt),
    )
    assert "nao_existe_xyz.wav" not in am5._samples, "sample inexistente não deveria carregar"
    bus.emit("WEAPON_FIRED", {})              # não deve crashar
    print("  ✓ entrada com arquivo ausente ignorada no load; emit sem crash")

    # ------------------------------------------------------------------
    # 6) Recriar após limpar o bus não duplica plays
    # ------------------------------------------------------------------
    print("\n[6] Recriar o mundo (bus limpo) não duplica sons")
    bus._listeners.clear()
    plays2 = []
    AudioManager(enabled=False, play_fn=lambda e, v, f: plays2.append(e))
    bus._listeners.clear()                     # simula _build_world_systems
    AudioManager(enabled=False, play_fn=lambda e, v, f: plays2.append(e))
    bus.emit("DOCKED", {})
    assert len(plays2) == 1, f"esperado 1 play (sem duplicação), veio {len(plays2)}"
    print("  ✓ um único play por evento após recriação")

    # ------------------------------------------------------------------
    # 7) Variantes por payload (identidade de propulsor por nave)
    # ------------------------------------------------------------------
    print("\n[7] Variantes: boost por model_id; fallback no padrão")
    bus._listeners.clear()
    plays3 = []
    am7 = AudioManager(enabled=False,
                       play_fn=lambda e, v, f: plays3.append((e, f)))
    cfg_boost = am7.sounds_cfg["BOOST_ACTIVATED"]
    assert cfg_boost.get("by") == "model_id", "boost deveria variar por model_id"
    variants = cfg_boost["variants"]
    assert len(variants) >= 6, "esperado um boost por nave"

    bus.emit("BOOST_ACTIVATED", {"model_id": "starter_skiff"})
    assert plays3[-1] == ("BOOST_ACTIVATED", variants["starter_skiff"]), plays3[-1]
    bus.emit("BOOST_ACTIVATED", {"model_id": "mule_trader"})
    assert plays3[-1][1] == variants["mule_trader"]
    assert variants["starter_skiff"] != variants["mule_trader"], \
        "cada nave deveria ter um boost próprio"
    # model_id desconhecido/ausente → arquivo padrão
    bus.emit("BOOST_ACTIVATED", {"model_id": "nave_inexistente"})
    assert plays3[-1][1] == cfg_boost["file"], plays3[-1]
    bus.emit("BOOST_ACTIVATED", {})
    assert plays3[-1][1] == cfg_boost["file"], plays3[-1]
    # todos os WAVs de variante existem no assets/audio
    audio_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "assets", "audio")
    for f in list(variants.values()) + [cfg_boost["file"]]:
        assert os.path.isfile(os.path.join(audio_dir, f)), f"falta {f}"
    print(f"  ✓ {len(variants)} variantes mapeadas; fallback OK; WAVs presentes")

    print("\nTeste de áudio: OK")


if __name__ == "__main__":
    main()
