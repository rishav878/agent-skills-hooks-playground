from app.skills.base import BaseSkill, SkillInput, SkillMetadata, SkillOutput


class ResearchSkill(BaseSkill):
    def __init__(self) -> None:
        super().__init__(
            SkillMetadata(
                name="research",
                description="Research a topic using web search and produce a structured summary",
                version="1.0.0",
                instructions=(
                    "You are a research assistant. Use the web search tool to find information "
                    "on the given topic. Synthesize the findings into a structured summary with "
                    "key findings, sources, and conclusions."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "The research topic or question"},
                        "use_rag": {"type": "boolean", "description": "Whether to retrieve relevant documents"},
                    },
                    "required": ["task"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "key_findings": {"type": "array", "items": {"type": "string"}},
                        "sources": {"type": "array", "items": {"type": "string"}},
                    },
                },
                allowed_tools=["web_search"],
                metadata={"category": "knowledge", "complexity": "medium"},
                enabled=True,
            )
        )

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        topic = input_data.task
        use_rag = input_data.parameters.get("use_rag", False)

        rag_context = ""
        if use_rag:
            rag_engine = input_data.context.get("rag_engine")
            if rag_engine:
                try:
                    docs = await rag_engine.retrieve_for_skill(topic, "research", top_k=3)
                    if docs:
                        snippets = "\n\n".join(
                            f"[{d.get('metadata', {}).get('title', 'Doc')}] {d.get('text', '')}"
                            for d in docs
                        )
                        rag_context = f"\n\nRelevant documents:\n{snippets}"
                except Exception:
                    rag_context = ""

        result = {
            "summary": f"Research summary for: {topic}{rag_context}",
            "key_findings": [
                f"Finding 1 related to {topic}",
                f"Finding 2 related to {topic}",
            ],
            "sources": ["https://example.com/source1", "https://example.com/source2"],
        }

        if rag_context:
            result["rag_used"] = True

        return SkillOutput(
            result=result,
            summary=f"Research completed on: {topic}",
            metadata={"skill": "research", "topic": topic, "rag_used": use_rag},
        )
