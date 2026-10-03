from datetime import datetime

from app.backtesting.replay.context.models import ContextWindow
from app.backtesting.replay.leakage.exceptions import (
    FutureDataDetectedError,
    InvalidReplayTimestampError,
)

class LeakageGuard:
    """
    Acts as a strict boundary to guarantee that no future market information 
    enters the signal or indicator pipelines.
    """

    @staticmethod
    def validate_context(context: ContextWindow, replay_timestamp: datetime) -> ContextWindow:
        """
        Validates the entire context window against the current replay timestamp.
        
        Args:
            context: The ContextWindow to validate.
            replay_timestamp: The current logical time in the replay engine.
            
        Returns:
            The identical ContextWindow if valid.
            
        Raises:
            FutureDataDetectedError: If any candle in the context has timestamp > replay_timestamp.
            InvalidReplayTimestampError: If replay_timestamp is naive or missing timezone.
        """
        if replay_timestamp.tzinfo is None or replay_timestamp.tzinfo.utcoffset(replay_timestamp) is None:
            raise InvalidReplayTimestampError("Replay timestamp must be timezone-aware.")
            
        if not context.candles:
            return context
            
        # Since ContextWindow guarantees chronological ordering (via HistoricalDataset),
        # we only strictly need to check the last candle. However, for maximum 
        # determinism and to prevent any edge-case injection, we will iterate.
        for candle in context.candles:
            if candle.timestamp > replay_timestamp:
                raise FutureDataDetectedError(
                    f"Leakage Guard triggered: Found future candle at {candle.timestamp} "
                    f"which is strictly greater than replay timestamp {replay_timestamp}."
                )
                
        return context
