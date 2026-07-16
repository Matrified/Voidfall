"""Quest data model.

Quests are authored data the engine tracks. An objective is a single checkable step; a
quest is complete when all of its objectives are done. Quest progress is driven by engine
events, never by the LLM — the narrator may *describe* progress, but the engine decides it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Objective:
    text: str
    done: bool = False
    # A flag whose truth completes this objective, if event-driven.
    flag: str | None = None


@dataclass(slots=True)
class Quest:
    id: str
    name: str
    objectives: list[Objective] = field(default_factory=list)
    active: bool = True
    completed: bool = False

    def refresh(self, flags: dict[str, bool]) -> bool:
        """Update objective/quest completion from world flags.

        Returns ``True`` if the quest transitioned to completed on this call.
        """
        if self.completed:
            return False
        for objective in self.objectives:
            if objective.flag and flags.get(objective.flag):
                objective.done = True
        if self.objectives and all(o.done for o in self.objectives):
            self.completed = True
            self.active = False
            return True
        return False
