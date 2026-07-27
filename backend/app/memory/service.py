import uuid
from typing import Any

from app.database.repository import Repository


class MemoryService:
    """Long-term memory — persists run summaries scoped by skill."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    async def save_conversation(
        self,
        run_id: str,
        trace_id: str,
        skill_name: str,
        task: str,
        summary: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> dict[str, Any]:
        mem_id = str(uuid.uuid4())
        mem = await self._repo.save_memory(
            memory_id=mem_id,
            run_id=run_id,
            trace_id=trace_id,
            skill_name=skill_name,
            task=task,
            summary=summary,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return {
            "id": mem.id,
            "run_id": mem.run_id,
            "trace_id": mem.trace_id,
            "skill_name": mem.skill_name,
            "task": mem.task,
            "summary": mem.summary,
            "created_at": mem.created_at.isoformat() if mem.created_at else "",
        }

    async def get_memories_by_skill(
        self, skill_name: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        memories = await self._repo.get_memories_by_skill(skill_name, limit=limit)
        return [
            {
                "id": m.id,
                "run_id": m.run_id,
                "trace_id": m.trace_id,
                "skill_name": m.skill_name,
                "task": m.task,
                "summary": m.summary,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in memories
        ]

    async def get_recent_context(self, skill_name: str, top_k: int = 3) -> str:
        """Build a short context string from recent memory for the given skill."""
        memories = await self._repo.get_memories_by_skill(skill_name, limit=top_k)
        if not memories:
            return ""
        lines: list[str] = []
        for m in memories:
            lines.append(f"- Task: {m.task}")
            if m.summary:
                lines.append(f"  Result: {m.summary}")
        return "\n".join(lines)
