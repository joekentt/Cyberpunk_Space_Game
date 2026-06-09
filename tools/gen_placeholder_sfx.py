"""
Gera WAVs sintéticos PLACEHOLDER para o AudioManager (ver ADR 009).

Stdlib pura (`wave`, `math`, `struct`, `random`) — sem numpy, sem pygame.
Cria 8 efeitos curtos em `assets/audio/` para o jogo ficar audível sem arte
final. Troque por arte de verdade depois (mesmos nomes de arquivo do
`data/audio.json`).

Uso:
    python tools/gen_placeholder_sfx.py
"""
import os
import math
import wave
import struct
import random

SAMPLE_RATE = 22050
AMP = 0.6  # amplitude máxima (0..1)

_OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "audio"
)


def _write_wav(name, samples):
    """Grava uma lista de floats [-1,1] como WAV mono 16-bit."""
    os.makedirs(_OUT, exist_ok=True)
    path = os.path.join(_OUT, name)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32767)
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))
    return path


def _n(seconds):
    return int(SAMPLE_RATE * seconds)


def _env_decay(i, total, power=2.0):
    """Envelope de decaimento exponencial (1 → 0)."""
    return (1.0 - i / total) ** power


def tone(freq, dur, decay=2.0, wave_fn=math.sin):
    """Tom único com decaimento."""
    total = _n(dur)
    out = []
    for i in range(total):
        t = i / SAMPLE_RATE
        out.append(AMP * _env_decay(i, total, decay) * wave_fn(2 * math.pi * freq * t))
    return out


def sweep(f0, f1, dur, decay=1.5):
    """Sweep linear de frequência (f0 → f1)."""
    total = _n(dur)
    out = []
    for i in range(total):
        t = i / SAMPLE_RATE
        f = f0 + (f1 - f0) * (i / total)
        out.append(AMP * _env_decay(i, total, decay) * math.sin(2 * math.pi * f * t))
    return out


def noise(dur, decay=2.0):
    """Ruído branco com decaimento (impacto/explosão)."""
    total = _n(dur)
    rnd = random.Random(1234)
    out = []
    for i in range(total):
        out.append(AMP * _env_decay(i, total, decay) * (rnd.uniform(-1, 1)))
    return out


def _mix(*tracks):
    """Soma vários tracks (alinha pelo mais longo), com clamp suave."""
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return [max(-1.0, min(1.0, s)) for s in out]


def _seq(*tracks):
    """Concatena tracks em sequência."""
    out = []
    for t in tracks:
        out.extend(t)
    return out


def main():
    # Tiro: bip agudo curto descendo (laser).
    _write_wav("laser_small.wav", sweep(1400, 600, 0.12, decay=2.5))
    # Impacto: ruído curto seco.
    _write_wav("impact.wav", noise(0.10, decay=3.0))
    # Explosão: ruído longo + grave decaindo.
    _write_wav("explosion.wav", _mix(noise(0.55, decay=1.6),
                                     tone(90, 0.55, decay=1.8)))
    # Dock: bip duplo confortável.
    _write_wav("dock.wav", _seq(tone(660, 0.10, decay=1.2),
                                [0.0] * _n(0.04),
                                tone(880, 0.14, decay=1.2)))
    # Boost: sweep ascendente enérgico.
    _write_wav("boost.wav", sweep(300, 1200, 0.30, decay=1.0))
    # Missão concluída: arpejo de duas notas ascendentes.
    _write_wav("mission_ok.wav", _seq(tone(523, 0.14, decay=1.0),
                                      tone(784, 0.26, decay=1.2)))
    # Vitória: fanfarra de 3 notas ascendentes.
    _write_wav("victory.wav", _seq(tone(523, 0.16, decay=0.8),
                                   tone(659, 0.16, decay=0.8),
                                   tone(988, 0.45, decay=1.0)))
    # Blip de UI (pips): muito curto.
    _write_wav("blip.wav", tone(1200, 0.05, decay=2.0))

    print(f"WAVs placeholder gerados em: {_OUT}")
    for f in sorted(os.listdir(_OUT)):
        if f.endswith(".wav"):
            size = os.path.getsize(os.path.join(_OUT, f))
            print(f"  {f:18s} {size:6d} bytes")


if __name__ == "__main__":
    main()
