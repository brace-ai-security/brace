"""Reporters: render a Report as text, JSON, SARIF, Markdown, GitLab SAST, JUnit XML, GitHub step outputs or a
prompt for a coding agent."""
from .agent_prompt import AgentPrompt
from .common import ReportOptions
from .github_output import GithubOutput
from .gitlab_sast import GitlabSast
from .json_out import Json
from .junit import Junit
from .markdown import Markdown
from .sarif import Sarif
from .text import Text

__all__ = ["BUILTIN", "ReportOptions"]
BUILTIN = (Text(), Json(), Sarif(), Markdown(), GitlabSast(), Junit(), GithubOutput(), AgentPrompt())
