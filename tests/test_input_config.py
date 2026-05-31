"""
Teste headless do InputConfig (keybindings).

Valida:
  - padrões quando não há arquivo de config
  - rebind + save persistem entre instâncias (simula reinício do jogo)
  - escrita atômica grava JSON legível
  - detecção de conflitos (duas ações na mesma tecla)
  - reset para padrões
  - tolerância a arquivo ausente/corrompido
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.input_config import InputConfig


def main():
    print("=" * 60)
    print("Teste de InputConfig (keybindings)")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp(prefix="keybinds_test_")
    cfg_path = os.path.join(tmpdir, "config", "keybinds.json")

    # ------------------------------------------------------------------
    # 1) Sem arquivo → padrões
    # ------------------------------------------------------------------
    print("\n[1] Padrões quando não há arquivo")
    cfg = InputConfig(cfg_path)
    assert not os.path.exists(cfg_path), "não deveria criar arquivo só ao carregar"
    assert cfg.get("thrust_forward") == "w"
    assert cfg.get("thrust_back") == "s"
    assert cfg.get("strafe_left") == "q"
    assert cfg.get("strafe_right") == "e"
    assert cfg.get("shoot") == "space"
    assert cfg.get("dock_toggle") == "f"
    assert cfg.get("pause") == "escape"
    print("  todos os padrões corretos (W/S/A/D/Q/E/ESPAÇO/F/ESC)  ✓")

    # ------------------------------------------------------------------
    # 2) Rebind + save persiste em nova instância (simula reiniciar o jogo)
    # ------------------------------------------------------------------
    print("\n[2] Rebind persiste entre execuções")
    cfg.set("thrust_forward", "up")
    cfg.set("shoot", "left ctrl")
    cfg.save()
    assert os.path.exists(cfg_path), "save() deveria criar o arquivo"

    # Nova instância lendo o MESMO arquivo = como reabrir o jogo
    cfg2 = InputConfig(cfg_path)
    assert cfg2.get("thrust_forward") == "up", "rebind não persistiu"
    assert cfg2.get("shoot") == "left ctrl", "rebind não persistiu"
    # ações não alteradas seguem nos padrões
    assert cfg2.get("rotate_left") == "a"
    print("  thrust_forward=up e shoot='left ctrl' persistiram  ✓")
    print("  ações não tocadas seguem nos padrões  ✓")

    # JSON em disco é legível e contém os binds
    with open(cfg_path, encoding="utf-8") as f:
        disk = json.load(f)
    assert disk["thrust_forward"] == "up"
    assert disk["shoot"] == "left ctrl"
    print("  JSON em disco íntegro e legível  ✓")

    # ------------------------------------------------------------------
    # 3) Detecção de conflitos
    # ------------------------------------------------------------------
    print("\n[3] Detecção de conflitos")
    assert cfg2.conflicts() == {}, "não deveria haver conflito ainda"
    cfg2.set("strafe_left", "w")   # 'w' não está em uso (thrust_forward virou 'up')
    assert cfg2.conflicts() == {}, "ainda sem conflito"
    cfg2.set("rotate_left", "d")   # 'd' já é rotate_right → conflito
    conflicts = cfg2.conflicts()
    assert "d" in conflicts, "deveria detectar conflito na tecla 'd'"
    assert set(conflicts["d"]) == {"rotate_left", "rotate_right"}
    print(f"  conflito detectado em 'd': {sorted(conflicts['d'])}  ✓")

    # ------------------------------------------------------------------
    # 4) Reset para padrões
    # ------------------------------------------------------------------
    print("\n[4] Reset para padrões")
    cfg2.reset_to_defaults()
    assert cfg2.get("thrust_forward") == "w"
    assert cfg2.conflicts() == {}
    print("  binds restaurados, sem conflitos  ✓")

    # ------------------------------------------------------------------
    # 5) Arquivo corrompido → cai nos padrões sem crashar
    # ------------------------------------------------------------------
    print("\n[5] Tolerância a arquivo corrompido")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("{ isso não é json válido :::")
    cfg3 = InputConfig(cfg_path)
    assert cfg3.get("thrust_forward") == "w", "deveria cair nos padrões"
    assert cfg3.get("pause") == "escape"
    print("  config corrompida ignorada, padrões aplicados  ✓")

    print("\nTeste de InputConfig: OK")


if __name__ == "__main__":
    main()
