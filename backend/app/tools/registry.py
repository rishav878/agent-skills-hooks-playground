from collections import defaultdict

from app.tools.base import BaseTool, RiskLevel, ToolPermission


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._tools_by_risk: dict[RiskLevel, list[BaseTool]] = defaultdict(list)

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.metadata.name] = tool
        self._tools_by_risk[tool.metadata.risk_level].append(tool)

    def get(self, tool_id: str) -> BaseTool | None:
        return self._tools.get(tool_id)

    def get_by_name(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def list_enabled(self) -> list[BaseTool]:
        return [t for t in self._tools.values() if t.metadata.enabled]

    def get_by_risk(self, risk: RiskLevel) -> list[BaseTool]:
        return list(self._tools_by_risk.get(risk, []))

    def get_by_permission(self, permission: ToolPermission) -> list[BaseTool]:
        return [t for t in self._tools.values() if t.metadata.permission == permission]

    def remove(self, tool_id: str) -> bool:
        tool = self._tools.pop(tool_id, None)
        if tool is not None:
            risk_list = self._tools_by_risk.get(tool.metadata.risk_level, [])
            if tool in risk_list:
                risk_list.remove(tool)
            return True
        return False

    def clear(self) -> None:
        self._tools.clear()
        self._tools_by_risk.clear()

    @property
    def count(self) -> int:
        return len(self._tools)
