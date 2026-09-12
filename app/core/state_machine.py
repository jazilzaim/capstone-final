"""
Argus Municipal Data Pipeline State Machine.
Implements the exact UML State Machine specification for asynchronous multi-city query and analytics jobs.
"""
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone
from app.core.exceptions import InvalidStateTransitionError

class JobState(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    FAILED_VALIDATION = "FailedValidation"
    QUEUED = "Queued"
    FETCHING = "Fetching"
    FAILED_EXECUTION = "FailedExecution"
    ANALYZING = "Analyzing"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"
    CANCELLED = "Cancelled"
    FINAL_STATE = "FinalState"

class JobEvent(str, Enum):
    INITIAL = "initial"
    SUBMIT = "submit"
    CANCEL = "cancel"
    VALIDATION_OK = "validationOk"
    VALIDATION_ERROR = "validationError"
    ERROR = "Error"
    WORKER_STARTS = "workerStarts"
    DELETE = "delete"
    SUCCESS = "success"
    FAILURE = "failure"
    ARCHIVE_POLICY = "archivePolicy"
    NOTIFY_USER = "notifyUser"

# Exact transitions as defined in the UML State Diagram:
TRANSITION_MAP: Dict[Tuple[JobState, JobEvent], JobState] = {
    # Draft (Initial)
    (JobState.DRAFT, JobEvent.SUBMIT): JobState.SUBMITTED,
    (JobState.DRAFT, JobEvent.CANCEL): JobState.CANCELLED,

    # Submitted
    (JobState.SUBMITTED, JobEvent.VALIDATION_OK): JobState.QUEUED,
    (JobState.SUBMITTED, JobEvent.VALIDATION_ERROR): JobState.FAILED_VALIDATION,

    # FailedValidation -> Error -> Draft
    (JobState.FAILED_VALIDATION, JobEvent.ERROR): JobState.DRAFT,

    # Queued
    (JobState.QUEUED, JobEvent.WORKER_STARTS): JobState.FETCHING,
    (JobState.QUEUED, JobEvent.CANCEL): JobState.CANCELLED,

    # Fetching
    (JobState.FETCHING, JobEvent.SUCCESS): JobState.ANALYZING,
    (JobState.FETCHING, JobEvent.FAILURE): JobState.FAILED_EXECUTION,
    (JobState.FETCHING, JobEvent.DELETE): JobState.CANCELLED,

    # Analyzing
    (JobState.ANALYZING, JobEvent.SUCCESS): JobState.COMPLETED,
    (JobState.ANALYZING, JobEvent.FAILURE): JobState.FAILED_EXECUTION,
    (JobState.ANALYZING, JobEvent.DELETE): JobState.CANCELLED,

    # FailedExecution -> failure -> Draft (Recovery loop)
    (JobState.FAILED_EXECUTION, JobEvent.FAILURE): JobState.DRAFT,

    # Completed -> archivePolicy -> Archived (Terminal)
    (JobState.COMPLETED, JobEvent.ARCHIVE_POLICY): JobState.ARCHIVED,

    # Cancelled -> notifyUser -> Final State
    (JobState.CANCELLED, JobEvent.NOTIFY_USER): JobState.FINAL_STATE,
}

class JobStateMachine:
    """
    Finite State Machine managing the lifecycle of an Argus data pipeline job.
    Enforces deterministic state transitions and logs an immutable audit trail.
    """
    def __init__(self, initial_state: JobState = JobState.DRAFT, history: Optional[List[Dict[str, Any]]] = None):
        self.state = initial_state if isinstance(initial_state, JobState) else JobState(initial_state)
        self.history: List[Dict[str, Any]] = history or []
        if not self.history:
            self._record_transition(None, self.state, JobEvent.INITIAL, {"info": "Initialized state machine"})

    def _record_transition(
        self,
        from_state: Optional[JobState],
        to_state: JobState,
        event: JobEvent,
        metadata: Optional[Dict[str, Any]] = None
    ):
        entry = {
            "from_state": from_state.value if from_state else None,
            "to_state": to_state.value,
            "event": event.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        self.history.append(entry)

    def can_transition(self, event: JobEvent) -> bool:
        """Check if an event is permitted from the current state without raising an error."""
        return (self.state, event) in TRANSITION_MAP

    def get_allowed_events(self) -> List[JobEvent]:
        """Return all valid events from the current state."""
        return [event for (state, event) in TRANSITION_MAP.keys() if state == self.state]

    def trigger(self, event_input: Any, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        """
        Trigger an event transition.
        Accepts JobEvent enum or string name (e.g. 'submit', 'submit()', 'validationOk').
        """
        # Normalize event name string
        if isinstance(event_input, str):
            clean_name = event_input.strip().replace("()", "")
            # Match enum by value or name (case-insensitive)
            matched_event = None
            for e in JobEvent:
                if e.value.lower() == clean_name.lower() or e.name.lower() == clean_name.lower():
                    matched_event = e
                    break
            if not matched_event:
                raise InvalidStateTransitionError(
                    current_state=self.state.value,
                    event=event_input,
                    allowed_transitions=[(self.state, e.value) for e in self.get_allowed_events()],
                    message=f"Unknown event '{event_input}'."
                )
            event = matched_event
        elif isinstance(event_input, JobEvent):
            event = event_input
        else:
            raise ValueError(f"Invalid event type: {type(event_input)}")

        key = (self.state, event)
        if key not in TRANSITION_MAP:
            allowed = [(self.state, e.value) for e in self.get_allowed_events()]
            raise InvalidStateTransitionError(
                current_state=self.state.value,
                event=event.value,
                allowed_transitions=allowed
            )

        previous_state = self.state
        next_state = TRANSITION_MAP[key]
        self.state = next_state
        self._record_transition(previous_state, next_state, event, metadata)
        return next_state

    # Helper transition shortcuts
    def submit(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.SUBMIT, metadata)

    def validation_ok(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.VALIDATION_OK, metadata)

    def validation_error(self, error_message: str, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        meta = metadata or {}
        meta["error"] = error_message
        return self.trigger(JobEvent.VALIDATION_ERROR, meta)

    def error(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.ERROR, metadata)

    def worker_starts(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.WORKER_STARTS, metadata)

    def success(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.SUCCESS, metadata)

    def failure(self, error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        meta = metadata or {}
        if error_message:
            meta["error"] = error_message
        return self.trigger(JobEvent.FAILURE, meta)

    def cancel(self, reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        meta = metadata or {}
        if reason:
            meta["reason"] = reason
        return self.trigger(JobEvent.CANCEL, meta)

    def delete(self, reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        meta = metadata or {}
        if reason:
            meta["reason"] = reason
        return self.trigger(JobEvent.DELETE, meta)

    def archive_policy(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.ARCHIVE_POLICY, metadata)

    def notify_user(self, metadata: Optional[Dict[str, Any]] = None) -> JobState:
        return self.trigger(JobEvent.NOTIFY_USER, metadata)

    def is_terminal(self) -> bool:
        return self.state in [JobState.ARCHIVED, JobState.FINAL_STATE]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_state": self.state.value,
            "is_terminal": self.is_terminal(),
            "allowed_events": [e.value for e in self.get_allowed_events()],
            "history": self.history
        }
