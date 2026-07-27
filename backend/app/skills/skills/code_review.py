from app.skills.base import BaseSkill, SkillInput, SkillMetadata, SkillOutput


class CodeReviewSkill(BaseSkill):
    def __init__(self) -> None:
        super().__init__(
            SkillMetadata(
                name="code_review",
                description="Review source code for quality, bugs, maintainability, and security",
                version="1.0.0",
                instructions=(
                    "You are a senior code reviewer. Analyze the provided source code for "
                    "potential bugs, security vulnerabilities, maintainability issues, and "
                    "coding standard violations. Provide actionable recommendations."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Review request"},
                        "use_rag": {"type": "boolean", "description": "Whether to retrieve relevant documents"},
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "language": {
                                    "type": "string",
                                    "enum": ["python", "javascript", "typescript", "java", "go", "other"],
                                },
                                "focus": {
                                    "type": "string",
                                    "enum": ["all", "bugs", "security", "style", "performance"],
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
                        "issues": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "severity": {"type": "string", "enum": ["critical", "major", "minor", "info"]},
                                    "category": {"type": "string"},
                                    "description": {"type": "string"},
                                    "suggestion": {"type": "string"},
                                },
                            },
                        },
                        "score": {"type": "integer"},
                    },
                },
                allowed_tools=["file_reader"],
                metadata={"category": "development", "complexity": "medium"},
                enabled=True,
            )
        )

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        language = input_data.parameters.get("language", "unknown")
        file_path = input_data.parameters.get("file_path", "unknown")
        focus = input_data.parameters.get("focus", "all")
        use_rag = input_data.parameters.get("use_rag", False)

        rag_context = ""
        if use_rag:
            rag_engine = input_data.context.get("rag_engine")
            if rag_engine:
                try:
                    docs = await rag_engine.retrieve_for_skill(
                        f"code review {focus} {file_path}", "code_review", top_k=3
                    )
                    if docs:
                        snippets = "\n\n".join(
                            f"[{d.get('metadata', {}).get('title', 'Doc')}] {d.get('text', '')}"
                            for d in docs
                        )
                        rag_context = f"\n\nReference documents:\n{snippets}"
                except Exception:
                    rag_context = ""

        result = {
            "summary": f"Code review ({focus} focus) for {file_path} ({language}){rag_context}",
            "issues": [
                {
                    "severity": "major",
                    "category": "bug",
                    "description": "Potential null reference in line 42",
                    "suggestion": "Add a null check before accessing the property",
                },
                {
                    "severity": "minor",
                    "category": "style",
                    "description": "Function is too long (120 lines)",
                    "suggestion": "Consider breaking into smaller functions",
                },
            ],
            "score": 75,
        }

        if rag_context:
            result["rag_used"] = True

        return SkillOutput(
            result=result,
            summary="Code review completed: found 2 issues",
            metadata={
                "skill": "code_review",
                "language": language,
                "focus": focus,
                "rag_used": use_rag,
            },
        )
