"""Execution metadata for signals.

Provides a lightweight immutable record attached to generated signals.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class SignalExecutionMetadata:
    """Metadata describing how a signal was produced.

    - ``source``: identifier of the caller (e.g., ``orchestrator`` or ``scheduler``).
    - ``execution_id``: unique id for the generation run, useful for tracing.
    - ``timestamp``: when the metadata was created.
    """

    source: str
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
