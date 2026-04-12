"""Pipeline exception hierarchy."""


class PipelineError(Exception):
    """Base for all pipeline errors."""


class StageError(PipelineError):
    """Error in a specific pipeline stage."""

    def __init__(self, message: str, stage: str) -> None:
        super().__init__(message)
        self.stage = stage


class AgentError(PipelineError):
    """Error from an LLM agent."""

    def __init__(self, message: str, agent_name: str) -> None:
        super().__init__(message)
        self.agent_name = agent_name


class PersistenceError(PipelineError):
    """Error reading/writing job data."""


class IngestionError(PipelineError):
    """Error extracting PDF content."""
