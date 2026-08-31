from dataclasses import dataclass


@dataclass(frozen=True)
class CollectionResult:
    """
    Result of executing a collection job.
    """

    job: object
    candles_collected: int
    success: bool
    error: str | None = None

    def __post_init__(self) -> None:
        if self.candles_collected < 0:
            raise ValueError(
                "candles_collected must not be negative"
            )

        if self.success and self.error is not None:
            raise ValueError(
                "successful result cannot contain an error"
            )

        if not self.success and self.error is None:
            raise ValueError(
                "failed result must contain an error"
            )