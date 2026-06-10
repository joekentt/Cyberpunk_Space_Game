"""
Gera WAVs sintéticos PLACEHOLDER para o AudioManager (ver ADR 009).

Stdlib pura (`wave`, `math`, `struct`, `random`) — sem numpy, sem pygame.
Cria os efeitos em `assets/audio/` para o jogo ficar audível sem arte final.
Troque por arte de verdade depois (mesmos nomes de arquivo do `data/audio.json`).

DSP usado (tudo em float, mono, 22050 Hz):
  - `lowpass`: filtro one-pole (ruído branco vira "exaustão" de motor).
  - `softclip`: saturação tanh (dá "grit" de combustão aos harmônicos).
  - `engine_burst`: receita de propulsor — rumble grave com rampa de pitch
    (spool-up), harmônicos saturados, ruído filtrado e um "throb" (LFO de
    amplitude) que imita pulsação de combustão. Cada nave usa parâmetros
    próprios (ver BOOST_VARIANTS) → identidade sonora por propulsor.
  - `laser_shot`: tiro em 3 camadas — transiente de ruído (estalo), corpo
    harmônico com queda EXPONENCIAL de pitch e um sub-thump grave curto.

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


def lowpass(samples, cutoff):
    """Filtro passa-baixa one-pole; cutoff em Hz."""
    a = 1.0 - math.exp(-2.0 * math.pi * cutoff / SAMPLE_RATE)
    y = 0.0
    out = []
    for s in samples:
        y += a * (s - y)
        out.append(y)
    return out


def softclip(samples, drive=2.0):
    """Saturação suave (tanh) — adiciona harmônicos / 'grit'."""
    norm = math.tanh(drive)
    return [math.tanh(s * drive) / norm for s in samples]


def _normalize(samples, peak=1.0):
    m = max((abs(s) for s in samples), default=0.0)
    if m <= 0.0:
        return samples
    k = peak / m
    return [s * k for s in samples]


def engine_burst(f0, f1, dur, noise_cutoff=1800.0, throb_hz=30.0,
                 throb_depth=0.12, grit=2.2, noise_mix=0.5,
                 attack=0.07, seed=7):
    """
    Burst de propulsor com identidade própria:
      - rumble harmônico (fundamental + 3 harmônicos, saturado por `grit`)
        com pitch subindo de f0 → f1 (spool-up);
      - ruído branco filtrado em `noise_cutoff` (exaustão), `noise_mix` do sinal;
      - `throb` = LFO de amplitude (pulsação de combustão);
      - envelope: ataque `attack` s + decaimento natural.
    """
    total = _n(dur)
    rnd = random.Random(seed)

    # Camada tonal: fase acumulada (sem clicks na rampa de pitch)
    tone_out = []
    phase = 0.0
    for i in range(total):
        u = i / total
        f = f0 + (f1 - f0) * u
        phase += 2.0 * math.pi * f / SAMPLE_RATE
        s = (math.sin(phase) + 0.55 * math.sin(2 * phase)
             + 0.32 * math.sin(3 * phase) + 0.22 * math.sin(4 * phase))
        tone_out.append(s / 2.09)
    tone_out = softclip(tone_out, grit)

    # Camada de ruído (exaustão): branco → passa-baixa → renormaliza
    nz = _normalize(lowpass([rnd.uniform(-1, 1) for _ in range(total)],
                            noise_cutoff))

    out = []
    for i in range(total):
        t = i / SAMPLE_RATE
        u = i / total
        env_a = min(1.0, t / attack) if attack > 0 else 1.0
        env_d = (1.0 - u) ** 1.6
        throb = 1.0 + throb_depth * math.sin(2.0 * math.pi * throb_hz * t)
        s = (1.0 - noise_mix) * tone_out[i] + noise_mix * nz[i]
        out.append(AMP * env_a * env_d * throb * s)
    return out


def laser_shot(f0=900.0, f1=210.0, dur=0.16, seed=99):
    """
    Disparo em 3 camadas (menos 'bip de brinquedo'):
      - transiente: 8 ms de ruído (estalo do disparo);
      - corpo: harmônicos saturados com pitch caindo exponencialmente f0 → f1;
      - sub-thump: senóide grave de 50 ms (peso do tiro).
    """
    total = _n(dur)
    rnd = random.Random(seed)
    n_trans = _n(0.008)
    n_thump = _n(0.05)
    out = []
    phase = 0.0
    ratio = f1 / f0
    for i in range(total):
        u = i / total
        f = f0 * (ratio ** u)
        phase += 2.0 * math.pi * f / SAMPLE_RATE
        body = (math.sin(phase) + 0.6 * math.sin(2 * phase)
                + 0.3 * math.sin(3 * phase))
        body = math.tanh(body * 1.8)
        s = body * ((1.0 - u) ** 2.2)
        if i < n_trans:
            s += rnd.uniform(-1, 1) * (1.0 - i / n_trans) * 0.8
        if i < n_thump:
            s += 0.5 * math.sin(2.0 * math.pi * 120.0 * (i / SAMPLE_RATE)) \
                 * (1.0 - i / n_thump)
        out.append(AMP * max(-1.0, min(1.0, s)))
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


# Identidade de propulsor por nave (model_id → parâmetros do engine_burst).
# `boost.wav` é o fallback genérico para naves sem variante mapeada.
BOOST_VARIANTS = {
    # genérico / fallback: motor neutro de porte leve
    "boost.wav": dict(f0=110, f1=190, dur=0.60, noise_cutoff=2000,
                      throb_hz=30, throb_depth=0.10, grit=2.0,
                      noise_mix=0.45, seed=11),
    # Skiff: leve e ágil — spool rápido, exaustão clara
    "boost_skiff.wav": dict(f0=120, f1=210, dur=0.55, noise_cutoff=2600,
                            throb_hz=36, throb_depth=0.08, grit=1.8,
                            noise_mix=0.50, seed=21),
    # Wasp: caça agressivo — rev alto, rasgado (muito grit)
    "boost_wasp.wav": dict(f0=160, f1=290, dur=0.50, noise_cutoff=3200,
                           throb_hz=44, throb_depth=0.14, grit=3.2,
                           noise_mix=0.42, seed=22),
    # Stingray: predador — sibilo brilhante, ataque seco
    "boost_stingray.wav": dict(f0=140, f1=250, dur=0.50, noise_cutoff=3800,
                               throb_hz=40, throb_depth=0.10, grit=2.6,
                               noise_mix=0.58, seed=23, attack=0.04),
    # Mule: cargueiro industrial — grave, lento, pulsação pesada
    "boost_mule.wav": dict(f0=60, f1=95, dur=0.85, noise_cutoff=900,
                           throb_hz=18, throb_depth=0.16, grit=2.4,
                           noise_mix=0.50, seed=24, attack=0.12),
    # Albatross: explorador — spool longo e macio, fundo profundo
    "boost_albatross.wav": dict(f0=80, f1=140, dur=0.90, noise_cutoff=1400,
                                throb_hz=22, throb_depth=0.07, grit=1.6,
                                noise_mix=0.45, seed=25, attack=0.14),
    # Terraformador: utilitário — pulsação lenta e pronunciada (bombas)
    "boost_terraformador.wav": dict(f0=95, f1=150, dur=0.70, noise_cutoff=1600,
                                    throb_hz=14, throb_depth=0.22, grit=2.0,
                                    noise_mix=0.48, seed=26),
}


def main():
    # Tiro: transiente + corpo harmônico descendente + sub-thump.
    _write_wav("laser_small.wav", laser_shot())
    # Impacto: ruído curto seco.
    _write_wav("impact.wav", noise(0.10, decay=3.0))
    # Explosão: ruído longo + grave decaindo.
    _write_wav("explosion.wav", _mix(noise(0.55, decay=1.6),
                                     tone(90, 0.55, decay=1.8)))
    # Dock: bip duplo confortável.
    _write_wav("dock.wav", _seq(tone(660, 0.10, decay=1.2),
                                [0.0] * _n(0.04),
                                tone(880, 0.14, decay=1.2)))
    # Boosts: um por nave + fallback genérico (identidade de propulsor).
    for fname, params in BOOST_VARIANTS.items():
        _write_wav(fname, engine_burst(**params))
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
            print(f"  {f:24s} {size:6d} bytes")


if __name__ == "__main__":
    main()
