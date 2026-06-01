from typing import Mapping, Protocol, Sequence

from .fixtures import COMPANIES, FIXTURE_AS_OF, ROTATION_SIGNALS
from .models import CandidateCompany, RotationSignal


class ResearchProvider(Protocol):
    def companies(self) -> Sequence[CandidateCompany]:
        ...

    def rotation_signals(self) -> Mapping[str, RotationSignal]:
        ...

    def as_of(self) -> str:
        ...


class FixtureResearchProvider:
    """Starter snapshot provider. Replace with a live provider for current research."""

    def companies(self) -> Sequence[CandidateCompany]:
        return COMPANIES

    def rotation_signals(self) -> Mapping[str, RotationSignal]:
        return ROTATION_SIGNALS

    def as_of(self) -> str:
        return FIXTURE_AS_OF
