"""Pipeline core: persistence, events, models, vector indexing, and exceptions."""

from .embedding import embed_batch, embed_text
from .events import Event, EventEmitter, EventType
from .exceptions import (
    AgentError,
    IngestionError,
    PersistenceError,
    PipelineError,
    StageError,
    TopicGateRejectedError,
)
from .models import JobState, JobStatus, PaperEntry
from .persistence import (
    create_job_dir,
    read_events,
    read_status,
    read_yaml,
    write_status,
    write_yaml,
)
from .qdrant import QdrantIndexer, get_indexer
from .quarantine import quarantine_job

__all__ = [
    "AgentError",
    "Event",
    "EventEmitter",
    "EventType",
    "IngestionError",
    "JobState",
    "JobStatus",
    "PaperEntry",
    "PersistenceError",
    "PipelineError",
    "QdrantIndexer",
    "StageError",
    "TopicGateRejectedError",
    "create_job_dir",
    "embed_batch",
    "embed_text",
    "get_indexer",
    "quarantine_job",
    "read_events",
    "read_status",
    "read_yaml",
    "write_status",
    "write_yaml",
]
