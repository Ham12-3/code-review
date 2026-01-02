import json
from typing import Any, Optional

from anthropic import AsyncAnthropic


class ClaudeClient:
    """Direct Claude API client for code review operations."""

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def analyze_code(
        self,
        code: str,
        language: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> dict[str, Any]:
        """
        Analyze code and return structured feedback.

        Returns a dict with:
        - summary: Overall assessment
        - issues: List of identified issues
        - security_issues: Count of security-related issues
        - quality_score: 0-100 score
        """
        lang_hint = f" (Language: {language})" if language else ""

        system_prompt = """You are an expert code reviewer. Analyze the provided code and return a JSON response with the following structure:
{
    "summary": "Brief overall assessment of the code",
    "quality_score": 0-100,
    "security_issues": number of security-related issues,
    "issues": [
        {
            "line_start": line number where issue starts,
            "line_end": line number where issue ends,
            "severity": "info" | "warning" | "error" | "critical",
            "category": "security" | "performance" | "style" | "bug" | "best-practice",
            "description": "Clear description of the issue",
            "suggestion": "How to fix it (optional)"
        }
    ]
}

Be thorough but practical. Focus on:
1. Security vulnerabilities (SQL injection, XSS, etc.)
2. Bugs and logic errors
3. Performance issues
4. Code quality and maintainability
5. Best practices for the language

Return ONLY valid JSON, no markdown or other formatting."""

        user_prompt = f"Review this code{lang_hint}:\n\n```\n{code}\n```"

        message = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse the response
        response_text = message.content[0].text

        # Strip markdown code blocks if present
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            # Remove opening code block (```json or ```)
            first_newline = cleaned_text.find("\n")
            if first_newline != -1:
                cleaned_text = cleaned_text[first_newline + 1:]
            # Remove closing code block
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3].strip()

        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, return a basic structure
            return {
                "summary": response_text,
                "issues": [],
                "security_issues": 0,
                "quality_score": None,
            }

    async def explain_issue(
        self,
        code: str,
        issue_description: str,
        model: str = "claude-3-5-haiku-20241022",
    ) -> str:
        """Get a detailed explanation of a specific issue."""
        message = await self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""Explain this code issue in detail:

Issue: {issue_description}

Code context:
```
{code}
```

Provide:
1. Why this is a problem
2. Potential consequences
3. How to fix it""",
                }
            ],
        )

        return message.content[0].text

    async def suggest_fix(
        self,
        code: str,
        issue_description: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> str:
        """Generate a code fix for a specific issue."""
        message = await self.client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"""Fix this issue in the code:

Issue: {issue_description}

Original code:
```
{code}
```

Return ONLY the fixed code, no explanations.""",
                }
            ],
        )

        return message.content[0].text

    async def triage_code(
        self,
        code: str,
        model: str = "claude-3-5-haiku-20241022",
    ) -> dict[str, Any]:
        """
        Quick triage to determine if code needs detailed review.
        Uses fast/cheap model for initial assessment.
        """
        message = await self.client.messages.create(
            model=model,
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": f"""Quickly assess this code. Return JSON:
{{"needs_review": true/false, "reason": "brief reason", "complexity": "low"/"medium"/"high"}}

Code:
```
{code[:2000]}
```""",
                }
            ],
        )

        try:
            return json.loads(message.content[0].text)
        except json.JSONDecodeError:
            return {"needs_review": True, "reason": "Could not assess", "complexity": "medium"}
