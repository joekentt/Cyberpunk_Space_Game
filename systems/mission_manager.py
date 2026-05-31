import random
import uuid
from typing import List, Dict, Any
from entities.mission import Mission, MissionStatus
from core.event_bus import bus

class MissionManager:
    """
    Gerencia a geração, progresso e conclusão de missões procedurais.
    """
    def __init__(self):
        self.available_missions: Dict[str, Mission] = {}
        self.active_missions: Dict[str, Mission] = {}
        self.completed_missions: List[str] = []
        
        # Templates de missões (serão carregados via DataLoader no futuro)
        self.templates = []

    def set_templates(self, templates: List[Dict[str, Any]]):
        """Define os templates para geração procedural."""
        self.templates = templates

    def generate_mission(self, faction: str, difficulty: float = 1.0) -> Mission:
        """Gera uma missão procedural baseada em templates e dificuldade."""
        if not self.templates:
            raise ValueError("Nenhum template de missão disponível.")

        template = random.choice(self.templates)
        mission_id = str(uuid.uuid4())[:8]
        
        # Cálculo de recompensa baseado na dificuldade
        base_reward = template.get("base_reward", 1000)
        reward = int(base_reward * difficulty * random.uniform(0.8, 1.2))
        
        mission = Mission(
            id=mission_id,
            title=template["title"].format(faction=faction),
            description=template["description"].format(faction=faction),
            type=template["type"],
            faction=faction,
            reward_credits=reward,
            reputation_impact=template.get("reputation_impact", {}),
            objectives=template.get("objectives", []),
            status=MissionStatus.AVAILABLE
        )
        
        self.available_missions[mission_id] = mission
        bus.emit("MISSION_GENERATED", mission.to_dict())
        return mission

    def accept_mission(self, mission_id: str):
        """Aceita uma missão disponível."""
        if mission_id in self.available_missions:
            mission = self.available_missions.pop(mission_id)
            mission.status = MissionStatus.ACTIVE
            self.active_missions[mission_id] = mission
            bus.emit("MISSION_ACCEPTED", mission.to_dict())

    def update_progress(self, event_type: str, data: Any):
        """
        Atualiza o progresso das missões ativas baseado em eventos do sistema.
        Ex: OnShipDestroyed, OnCargoDelivered.
        """
        to_complete = []
        for m_id, mission in self.active_missions.items():
            # Lógica simplificada de conclusão para o MVP
            # Em um sistema real, verificaríamos os objetivos específicos
            if mission.type == "BOUNTY" and event_type == "ENTITY_REMOVED":
                if data.get("id") == mission.target_entity_id:
                    to_complete.append(m_id)
            
            # Teste manual de conclusão via evento direto
            if event_type == "DEBUG_COMPLETE_MISSION" and data == m_id:
                to_complete.append(m_id)

        for m_id in to_complete:
            self.complete_mission(m_id)

    def record_kill(self, target_faction: str):
        """
        Registra um kill para missões BOUNTY ativas que peçam eliminar
        naves da facção informada. Completa automaticamente quando atingir
        o contador requerido.
        """
        to_complete = []
        for m_id, mission in self.active_missions.items():
            if mission.type != "BOUNTY":
                continue
            kill_obj = next(
                (o for o in mission.objectives if o.get("type") == "KILL"),
                None,
            )
            if kill_obj is None:
                continue
            if kill_obj.get("target_faction") != target_faction:
                continue
            mission.kill_progress += 1
            required = kill_obj.get("count", 1)
            bus.emit("MISSION_PROGRESS", {
                "mission_id": m_id,
                "progress": mission.kill_progress,
                "required": required,
            })
            if mission.kill_progress >= required:
                to_complete.append(m_id)
        for m_id in to_complete:
            self.complete_mission(m_id)

    def complete_mission(self, mission_id: str):
        """Finaliza uma missão com sucesso e emite recompensas."""
        if mission_id in self.active_missions:
            mission = self.active_missions.pop(mission_id)
            mission.status = MissionStatus.COMPLETED
            self.completed_missions.append(mission_id)
            
            # Emite eventos para outros sistemas processarem recompensas
            bus.emit("MISSION_COMPLETED", mission.to_dict())
            bus.emit("ADD_CREDITS", mission.reward_credits)
            bus.emit("UPDATE_REPUTATION", {
                "faction": mission.faction,
                "impact": mission.reputation_impact
            })

    def get_save_data(self) -> Dict[str, Any]:
        """Retorna dados para persistência."""
        return {
            "active": {k: v.to_dict() for k, v in self.active_missions.items()},
            "completed": self.completed_missions
        }

    def load_save_data(self, data: Dict[str, Any]):
        """Carrega dados de um save."""
        self.active_missions = {k: Mission.from_dict(v) for k, v in data.get("active", {}).items()}
        self.completed_missions = data.get("completed", [])
