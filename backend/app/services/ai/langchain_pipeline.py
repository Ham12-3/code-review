from typing import Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END


class ReviewState(TypedDict):
    """State for the code review workflow."""

    code: str
    language: str | None
    detected_language: str | None
    security_scan: dict | None
    quality_analysis: dict | None
    final_summary: str | None
    issues: list[dict]
    error: str | None


class CodeReviewPipeline:
    """
    Multi-step code review pipeline using LangGraph.

    Workflow:
    1. Language detection
    2. Security scan (OWASP patterns)
    3. Code quality analysis
    4. Summary generation
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            max_tokens=4096,
        )
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(ReviewState)

        # Add nodes
        workflow.add_node("detect_language", self._detect_language)
        workflow.add_node("security_scan", self._security_scan)
        workflow.add_node("quality_analysis", self._quality_analysis)
        workflow.add_node("generate_summary", self._generate_summary)

        # Define edges
        workflow.set_entry_point("detect_language")
        workflow.add_edge("detect_language", "security_scan")
        workflow.add_edge("security_scan", "quality_analysis")
        workflow.add_edge("quality_analysis", "generate_summary")
        workflow.add_edge("generate_summary", END)

        return workflow.compile()

    async def _detect_language(self, state: ReviewState) -> ReviewState:
        """Detect the programming language if not provided."""
        if state.get("language"):
            state["detected_language"] = state["language"]
            return state

        messages = [
            SystemMessage(
                content="Detect the programming language of this code. Return ONLY the language name, nothing else."
            ),
            HumanMessage(content=f"```\n{state['code'][:1000]}\n```"),
        ]

        response = await self.llm.ainvoke(messages)
        state["detected_language"] = response.content.strip().lower()
        return state

    async def _security_scan(self, state: ReviewState) -> ReviewState:
        """Scan for security vulnerabilities (OWASP patterns)."""
        messages = [
            SystemMessage(
                content="""You are a security expert. Scan this code for security vulnerabilities.
Focus on OWASP Top 10:
- Injection (SQL, Command, etc.)
- Broken Authentication
- Sensitive Data Exposure
- XML External Entities (XXE)
- Broken Access Control
- Security Misconfiguration
- Cross-Site Scripting (XSS)
- Insecure Deserialization
- Using Components with Known Vulnerabilities
- Insufficient Logging & Monitoring

Return JSON:
{
    "vulnerabilities": [
        {"type": "...", "severity": "critical/high/medium/low", "line": N, "description": "..."}
    ],
    "risk_level": "high/medium/low",
    "recommendations": ["..."]
}"""
            ),
            HumanMessage(
                content=f"Language: {state.get('detected_language', 'unknown')}\n\nCode:\n```\n{state['code']}\n```"
            ),
        ]

        response = await self.llm.ainvoke(messages)

        try:
            import json

            state["security_scan"] = json.loads(response.content)
        except json.JSONDecodeError:
            state["security_scan"] = {
                "vulnerabilities": [],
                "risk_level": "unknown",
                "recommendations": [],
            }

        # Add security issues to the issues list
        for vuln in state["security_scan"].get("vulnerabilities", []):
            state["issues"].append(
                {
                    "line_start": vuln.get("line", 1),
                    "line_end": vuln.get("line", 1),
                    "severity": vuln.get("severity", "warning"),
                    "category": "security",
                    "description": f"[{vuln.get('type', 'Security')}] {vuln.get('description', '')}",
                    "suggestion": None,
                }
            )

        return state

    async def _quality_analysis(self, state: ReviewState) -> ReviewState:
        """Analyze code quality, patterns, and best practices."""
        messages = [
            SystemMessage(
                content="""Analyze code quality. Return JSON:
{
    "quality_score": 0-100,
    "issues": [
        {
            "type": "bug/performance/style/best-practice",
            "severity": "error/warning/info",
            "line": N,
            "description": "...",
            "suggestion": "..."
        }
    ],
    "metrics": {
        "complexity": "low/medium/high",
        "maintainability": "poor/fair/good/excellent",
        "test_coverage_hint": "none/partial/likely"
    }
}"""
            ),
            HumanMessage(
                content=f"Language: {state.get('detected_language', 'unknown')}\n\nCode:\n```\n{state['code']}\n```"
            ),
        ]

        response = await self.llm.ainvoke(messages)

        try:
            import json

            state["quality_analysis"] = json.loads(response.content)
        except json.JSONDecodeError:
            state["quality_analysis"] = {"quality_score": None, "issues": [], "metrics": {}}

        # Add quality issues to the issues list
        for issue in state["quality_analysis"].get("issues", []):
            state["issues"].append(
                {
                    "line_start": issue.get("line", 1),
                    "line_end": issue.get("line", 1),
                    "severity": issue.get("severity", "info"),
                    "category": issue.get("type", "style"),
                    "description": issue.get("description", ""),
                    "suggestion": issue.get("suggestion"),
                }
            )

        return state

    async def _generate_summary(self, state: ReviewState) -> ReviewState:
        """Generate final summary combining all analyses."""
        security = state.get("security_scan", {})
        quality = state.get("quality_analysis", {})

        context = f"""
Security Analysis:
- Risk Level: {security.get('risk_level', 'unknown')}
- Vulnerabilities Found: {len(security.get('vulnerabilities', []))}

Quality Analysis:
- Quality Score: {quality.get('quality_score', 'N/A')}
- Issues Found: {len(quality.get('issues', []))}
- Complexity: {quality.get('metrics', {}).get('complexity', 'unknown')}
- Maintainability: {quality.get('metrics', {}).get('maintainability', 'unknown')}

Total Issues: {len(state['issues'])}
"""

        messages = [
            SystemMessage(
                content="Write a concise 2-3 sentence summary of this code review. Highlight the most important findings and overall assessment."
            ),
            HumanMessage(content=context),
        ]

        response = await self.llm.ainvoke(messages)
        state["final_summary"] = response.content.strip()

        return state

    async def run(
        self, code: str, language: str | None = None
    ) -> dict[str, Any]:
        """
        Run the full review pipeline.

        Returns:
            dict with summary, issues, security_issues count, and quality_score
        """
        initial_state: ReviewState = {
            "code": code,
            "language": language,
            "detected_language": None,
            "security_scan": None,
            "quality_analysis": None,
            "final_summary": None,
            "issues": [],
            "error": None,
        }

        result = await self.workflow.ainvoke(initial_state)

        security_count = len(
            result.get("security_scan", {}).get("vulnerabilities", [])
        )
        quality_score = result.get("quality_analysis", {}).get("quality_score")

        return {
            "summary": result.get("final_summary", "Analysis complete"),
            "issues": result.get("issues", []),
            "security_issues": security_count,
            "quality_score": quality_score,
            "detected_language": result.get("detected_language"),
            "security_scan": result.get("security_scan"),
            "quality_analysis": result.get("quality_analysis"),
        }
