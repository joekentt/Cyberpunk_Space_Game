"""
Gera WAVs sintéticos PLACEHOLDER para o AudioManager (ver ADR 009).

Stdlib pura (`wave`, `math`, `struct`, `random`) — sem numpy, sem pygame.
Cria os efeitos em `assets/audio/` para o jogo ficar audível sem arte final.
Troque por arte de verdade depois (mesmos nomes de arquivo do `data/audio.json`).

DSP usado (tudo em float, mono, 22050 Hz):
  - `lowpass` / `highpass`: filtros one-pole (shaping espectral).
  - `softclip`: saturação tanh (grit e punch sem clipar).
  - `engine_burst`: propulsor — rumble grave com spool-up de pitch, harmônicos
    saturados, ruído de exaustão filtrado e throb de combustão. Parâmetros por
    nave em BOOST_VARIANTS → identidade sonora por propulsor.
  - `laser_shot`: tiro em 3 camadas — transiente de ruído (estalo), corpo
    harmônico com queda exponencial de pitch, sub-thump grave.
  - `explosion_sfx`: explosão em 4 camadas — shockwave (crack impulsivo de
    banda larga), fireball (ruído de baixa frequência saturado, longo), ring
    (par de ressonâncias metálicas amortecidas) e rumble sub-sonic.
  - `impact_sfx`: colisão metálica — spike impulsivo + anel metálico alto-Q +
    ruído de debris curto.
  - `dock_sfx`: acoplamento de câmara — thud mecânico grave + sibilo hidráulico
    (ruído passa-baixa) + confirmação tonal suave.
  - `mission_sfx` / `victory_sfx`: síntese subtrativa com harmônicos ricos;
    evitam os sinos de vidro do arpejo simples.

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


def highpass(samples, cutoff):
    """Filtro passa-alta one-pole."""
    a = 1.0 - math.exp(-2.0 * math.pi * cutoff / SAMPLE_RATE)
    y, prev_x, prev_y = 0.0, 0.0, 0.0
    out = []
    for s in samples:
        low = prev_y + a * (prev_x - prev_y)
        out.append(s - low)
        prev_x, prev_y = s, low
    return out


def _resonator(freq, dur, decay_tau=0.12, amp=0.5, seed=0):
    """Par de frequências ressonantes (anel metálico amortecido)."""
    total = _n(dur)
    rnd = random.Random(seed)
    env = [math.exp(-i / (SAMPLE_RATE * decay_tau)) for i in range(total)]
    phase = rnd.uniform(0, 2 * math.pi)
    return [amp * env[i] * math.sin(2 * math.pi * freq * i / SAMPLE_RATE + phase)
            for i in range(total)]


def _impulse(n_samples, width=3, seed=5):
    """Spike impulsivo de banda larga (click de impacto)."""
    rnd = random.Random(seed)
    out = [0.0] * n_samples
    for k in range(width):
        idx = min(k, n_samples - 1)
        out[idx] = rnd.uniform(0.6, 1.0) * (1.0 - k / width)
    return out


def explosion_sfx(dur=0.80, seed=42):
    """
    4 camadas:
     1. Shockwave: crack impulsivo de banda larga (primeiros 30 ms).
     2. Fireball: ruído grave saturado, longo e decrescente.
     3. Ring: duas ressonâncias metálicas amortecidas.
     4. Sub-rumble: senóide muito grave (40 Hz) em fade lento.
    """
    total = _n(dur)
    rnd = random.Random(seed)

    # 1. Shockwave: click de alta amplitude + highpass
    n_shock = _n(0.03)
    shock = [0.0] * total
    for i in range(n_shock):
        shock[i] = rnd.uniform(-1, 1) * math.exp(-i / (SAMPLE_RATE * 0.005))
    shock = highpass(shock, 200.0)

    # 2. Fireball: ruído branco → lowpass forte → saturação → envelope longo
    raw = [rnd.uniform(-1, 1) for _ in range(total)]
    fire = lowpass(raw, 350.0)
    fire = softclip(fire, 3.5)
    fire = [fire[i] * math.exp(-i / (SAMPLE_RATE * 0.35)) for i in range(total)]

    # 3. Ring metálico: 2 ressonâncias
    ring1 = _resonator(180, dur, decay_tau=0.18, amp=0.6, seed=1)
    ring2 = _resonator(310, dur, decay_tau=0.10, amp=0.3, seed=2)

    # 4. Sub-rumble 40 Hz
    sub = [0.4 * math.sin(2 * math.pi * 40 * i / SAMPLE_RATE)
           * math.exp(-i / (SAMPLE_RATE * 0.55)) for i in range(total)]

    # mix ponderado
    weights = [0.55, 0.55, 0.7, 0.7]
    layers = [shock, fire, ring1, ring2]
    out = [s * 0.5 for s in sub]
    for w, layer in zip(weights, layers):
        for i, s in enumerate(layer):
            out[i] = out[i] + w * s if i < len(out) else out[i]

    return [AMP * max(-1.0, min(1.0, s)) for s in out]


def impact_sfx(seed=77):
    """
    Colisão metálica em 3 camadas:
     1. Spike impulsivo de banda larga (punch inicial).
     2. Anel metálico alto-Q (frequência de casco).
     3. Debris: ruído branco curtíssimo (raspagem).
    """
    dur = 0.18
    total = _n(dur)
    rnd = random.Random(seed)

    # 1. Spike
    spike = _impulse(total, width=4, seed=seed)
    spike = [s * math.exp(-i / (SAMPLE_RATE * 0.008)) for i, s in enumerate(spike)]

    # 2. Ring: frequência de ressonância de casco metálico
    ring = _resonator(520, dur, decay_tau=0.06, amp=0.7, seed=seed + 1)

    # 3. Debris: ruído alto curto
    n_deb = _n(0.04)
    debris = [rnd.uniform(-1, 1) * math.exp(-i / (SAMPLE_RATE * 0.012))
              for i in range(n_deb)] + [0.0] * (total - n_deb)
    debris = highpass(debris, 1200.0)

    out = []
    for i in range(total):
        s = 0.9 * spike[i] + 0.65 * ring[i] + 0.35 * debris[i]
        out.append(AMP * max(-1.0, min(1.0, s)))
    return out


def dock_sfx(seed=33):
    """
    Acoplamento de câmara em 3 fases:
     1. Thud mecânico grave (impacto de andaime).
     2. Sibilo hidráulico (ruído passa-baixa, 0.4 s).
     3. Bip de confirmação suave (tom curto, não chiante).
    """
    rnd = random.Random(seed)

    # 1. Thud: sub-grave saturado, ataque instantâneo
    n_thud = _n(0.12)
    phase = 0.0
    thud = []
    for i in range(n_thud):
        phase += 2 * math.pi * 65 / SAMPLE_RATE
        s = math.sin(phase) + 0.4 * math.sin(2 * phase)
        s = math.tanh(s * 2.0)
        thud.append(s * math.exp(-i / (SAMPLE_RATE * 0.055)))

    # 2. Sibilo hidráulico
    n_hiss = _n(0.42)
    raw_h = [rnd.uniform(-1, 1) for _ in range(n_hiss)]
    hiss = lowpass(raw_h, 380.0)
    env_h = [math.exp(-i / (SAMPLE_RATE * 0.14)) for i in range(n_hiss)]
    hiss = [hiss[i] * env_h[i] * 0.45 for i in range(n_hiss)]

    # 3. Tom de confirmação: senoide com 3 harmônicos, curtinho
    n_beep = _n(0.18)
    beep = []
    ph = 0.0
    for i in range(n_beep):
        ph += 2 * math.pi * 440 / SAMPLE_RATE
        env_b = (1.0 - i / n_beep) ** 1.5
        beep.append((math.sin(ph) + 0.3 * math.sin(2 * ph)) * 0.4 * env_b)

    # sequência: thud | overlap ligeiro com hiss | beep ao fim do hiss
    total = len(thud) + len(hiss)
    out = [0.0] * total
    for i, s in enumerate(thud):
        out[i] += s
    for i, s in enumerate(hiss):
        out[i + len(thud)] += s
    beep_start = len(thud) + len(hiss) - len(beep)
    for i, s in enumerate(beep):
        idx = beep_start + i
        if idx < total:
            out[idx] += s

    return [AMP * max(-1.0, min(1.0, s)) for s in out]


def _synth_chord(freqs, dur, decay=1.4, drive=1.6):
    """Acorde de síntese subtrativa com harmônicos saturados."""
    total = _n(dur)
    out = [0.0] * total
    for freq in freqs:
        for i in range(total):
            u = i / total
            env = (1.0 - u) ** decay
            s = (math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
                 + 0.5 * math.sin(2 * math.pi * 2 * freq * i / SAMPLE_RATE)
                 + 0.25 * math.sin(2 * math.pi * 3 * freq * i / SAMPLE_RATE))
            out[i] += env * math.tanh(s * drive) / (2.09 * len(freqs))
    return [AMP * s for s in out]


def mission_sfx():
    """
    Confirmação de missão: dois acordes cyberpunk (quinta + oitava),
    com ataque rápido e decaimento amortecido — sem o timbre de sinos do
    arpejo de toms simples.
    """
    silence = [0.0] * _n(0.035)
    c1 = _synth_chord([261.6, 392.0, 523.2], dur=0.22, decay=1.5, drive=1.8)
    c2 = _synth_chord([349.2, 523.2, 698.5], dur=0.38, decay=1.3, drive=1.6)
    return _seq(c1, silence, c2)


def victory_sfx():
    """
    Fanfarra de vitória: 3 acordes ascendentes ricos, com ataque percussivo
    e decaimento modal (não toca como carrilhão).
    """
    gap = [0.0] * _n(0.04)
    c1 = _synth_chord([130.8, 196.0, 261.6], dur=0.20, decay=1.2, drive=2.2)
    c2 = _synth_chord([164.8, 246.9, 329.6], dur=0.22, decay=1.2, drive=2.0)
    c3 = _synth_chord([196.0, 293.7, 392.0, 523.2], dur=0.55, decay=1.0, drive=1.8)
    return _seq(c1, gap, c2, gap, c3)


def _mix(*tracks):
    """Soma vários tracks (alinha pelo mais longo), sem clamp (usa _normalize depois)."""
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
    # Tiro laser: transiente + corpo harmônico descendente + sub-thump.
    _write_wav("laser_small.wav", laser_shot())
    # Impacto: spike metálico + anel + debris (colisão com casco).
    _write_wav("impact.wav", impact_sfx())
    # Explosão: shockwave + fireball + ring + sub-rumble.
    _write_wav("explosion.wav", explosion_sfx())
    # Dock: thud mecânico + sibilo hidráulico + confirmação tonal.
    _write_wav("dock.wav", dock_sfx())
    # Boosts: um por nave + fallback genérico (identidade de propulsor).
    for fname, params in BOOST_VARIANTS.items():
        _write_wav(fname, engine_burst(**params))
    # Missão concluída: dois acordes cyberpunk saturados.
    _write_wav("mission_ok.wav", mission_sfx())
    # Vitória: fanfarra de 3 acordes ascendentes com harmônicos ricos.
    _write_wav("victory.wav", victory_sfx())
    # Blip de UI (pips): muito curto.
    _write_wav("blip.wav", tone(1200, 0.05, decay=2.0))

    print(f"WAVs placeholder gerados em: {_OUT}")
    for f in sorted(os.listdir(_OUT)):
        if f.endswith(".wav"):
            size = os.path.getsize(os.path.join(_OUT, f))
            print(f"  {f:24s} {size:6d} bytes")


if __name__ == "__main__":
    main()
