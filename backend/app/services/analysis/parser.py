from dataclasses import dataclass
from typing import Optional

# tree-sitter-languages is optional (doesn't support Python 3.12+)
try:
    import tree_sitter_languages
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class CodeMetrics:
    """Metrics extracted from code analysis."""

    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: list[dict]
    classes: list[dict]
    imports: list[str]
    complexity_estimate: str  # low, medium, high


class CodeParser:
    """
    Code parser for basic code metrics.
    Tree-sitter AST parsing is optional (not available on Python 3.12+).
    """

    def __init__(self):
        self._parsers = {}

    def parse(self, code: str, language: str) -> Optional[dict]:
        """
        Parse code and return AST information.
        Returns None if tree-sitter is not available.
        """
        if not TREE_SITTER_AVAILABLE:
            return None

        lang_key = self._map_language(language)
        try:
            parser = tree_sitter_languages.get_parser(lang_key)
            tree = parser.parse(bytes(code, "utf8"))
            return {
                "root": self._node_to_dict(tree.root_node),
                "has_errors": tree.root_node.has_error,
            }
        except Exception:
            return None

    def _map_language(self, language: str) -> str:
        """Map common language names to tree-sitter names."""
        mapping = {
            "python": "python", "py": "python",
            "javascript": "javascript", "js": "javascript",
            "typescript": "typescript", "ts": "typescript",
            "tsx": "tsx", "jsx": "javascript",
            "java": "java", "go": "go", "golang": "go",
            "rust": "rust", "rs": "rust",
            "c": "c", "cpp": "cpp", "c++": "cpp",
            "csharp": "c_sharp", "cs": "c_sharp",
            "ruby": "ruby", "rb": "ruby", "php": "php",
        }
        return mapping.get(language.lower(), language.lower())

    def _node_to_dict(self, node, depth: int = 0, max_depth: int = 5) -> dict:
        """Convert tree-sitter node to dictionary."""
        if depth >= max_depth:
            return {"type": node.type, "truncated": True}

        result = {
            "type": node.type,
            "start": {"row": node.start_point[0], "col": node.start_point[1]},
            "end": {"row": node.end_point[0], "col": node.end_point[1]},
        }

        if node.child_count > 0:
            result["children"] = [
                self._node_to_dict(child, depth + 1, max_depth)
                for child in node.children
            ]

        return result

    def extract_metrics(self, code: str, language: str) -> CodeMetrics:
        """Extract code metrics from source code (works without tree-sitter)."""
        lines = code.split("\n")
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())

        # Basic heuristics without AST
        functions = []
        classes = []
        imports = []
        comment_lines = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Count comments (basic patterns)
            if stripped.startswith("#") or stripped.startswith("//"):
                comment_lines += 1
            elif stripped.startswith("/*") or stripped.startswith("'''") or stripped.startswith('"""'):
                comment_lines += 1

            # Detect functions (basic patterns)
            if stripped.startswith("def ") or stripped.startswith("function "):
                name = stripped.split("(")[0].split()[-1] if "(" in stripped else "unknown"
                functions.append({"name": name, "start_line": i, "end_line": i})
            elif stripped.startswith("async def "):
                name = stripped.split("(")[0].split()[-1] if "(" in stripped else "unknown"
                functions.append({"name": name, "start_line": i, "end_line": i})

            # Detect classes
            if stripped.startswith("class "):
                name = stripped.split("(")[0].split(":")[0].split()[-1]
                classes.append({"name": name, "start_line": i, "end_line": i})

            # Detect imports
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(f"Line {i}")

        code_lines = total_lines - blank_lines - comment_lines
        complexity = self._estimate_complexity(functions, classes, code_lines)

        return CodeMetrics(
            total_lines=total_lines,
            code_lines=max(0, code_lines),
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            functions=functions,
            classes=classes,
            imports=imports,
            complexity_estimate=complexity,
        )

    def _estimate_complexity(
        self, functions: list, classes: list, code_lines: int
    ) -> str:
        """Estimate code complexity based on metrics."""
        num_functions = len(functions)
        num_classes = len(classes)

        if code_lines < 100 and num_functions < 5 and num_classes < 2:
            return "low"
        elif code_lines < 500 and num_functions < 20 and num_classes < 10:
            return "medium"
        else:
            return "high"
