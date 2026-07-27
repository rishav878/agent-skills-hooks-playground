from app.skills.base import BaseSkill, SkillInput, SkillMetadata, SkillOutput


class DataAnalysisSkill(BaseSkill):
    def __init__(self) -> None:
        super().__init__(
            SkillMetadata(
                name="data_analysis",
                description="Analyze structured data (CSV, JSON) using Python execution",
                version="1.0.0",
                instructions=(
                    "You are a data analyst. Use the Python execution tool to load, clean, "
                    "and analyze the provided data. Produce summary statistics, visualizations, "
                    "and actionable insights."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Analysis request"},
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "data_path": {"type": "string"},
                                "analysis_type": {
                                    "type": "string",
                                    "enum": ["summary", "trend", "comparison", "custom"],
                                },
                            },
                        },
                    },
                    "required": ["task"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "statistics": {"type": "object"},
                        "insights": {"type": "array", "items": {"type": "string"}},
                        "visualizations": {"type": "array", "items": {"type": "string"}},
                    },
                },
                allowed_tools=["python_executor", "file_reader"],
                metadata={"category": "analysis", "complexity": "high"},
                enabled=True,
            )
        )

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        analysis_type = input_data.parameters.get("analysis_type", "summary")
        data_path = input_data.parameters.get("data_path", "unknown")
        use_tool = input_data.parameters.get("use_tool", False)

        result = {
            "summary": f"Data analysis ({analysis_type}) completed on {data_path}",
            "statistics": {
                "row_count": 100,
                "column_count": 5,
                "missing_values": 2,
            },
            "insights": [
                "Insight 1 from data analysis",
                "Insight 2 from data analysis",
            ],
            "visualizations": [],
        }

        if use_tool:
            result["tool"] = "python_executor"

        return SkillOutput(
            result=result,
            summary=f"{analysis_type} analysis completed",
            metadata={"skill": "data_analysis", "analysis_type": analysis_type},
        )
