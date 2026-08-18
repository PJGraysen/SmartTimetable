from enum import Enum


class DayOfWeek(str, Enum):
    """Days used by the school timetable."""

    MONDAY = "MON"
    TUESDAY = "TUE"
    WEDNESDAY = "WED"
    THURSDAY = "THU"
    FRIDAY = "FRI"


class PartOfDay(str, Enum):
    """Major teaching-day divisions."""

    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    OTHER = "OTHER"


class SchedulingRunStatus(str, Enum):
    """Lifecycle state of a scheduling run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SolverStatus(str, Enum):
    """Result returned by the scheduling solver."""

    NOT_STARTED = "NOT_STARTED"
    UNKNOWN = "UNKNOWN"
    FEASIBLE = "FEASIBLE"
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    MODEL_INVALID = "MODEL_INVALID"
    TIME_LIMIT = "TIME_LIMIT"
    FAILED = "FAILED"


class ValidationSeverity(str, Enum):
    """Severity of a timetable validation finding."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationCategory(str, Enum):
    """Categories of timetable validation findings."""

    TEACHER_CLASH = "TEACHER_CLASH"
    GROUP_CLASH = "GROUP_CLASH"
    ROOM_CLASH = "ROOM_CLASH"
    TEACHER_AVAILABILITY = "TEACHER_AVAILABILITY"
    TEACHER_FREE_AFTERNOON = "TEACHER_FREE_AFTERNOON"
    ROOM_AVAILABILITY = "ROOM_AVAILABILITY"
    LESSON_REQUIREMENT = "LESSON_REQUIREMENT"
    PERIOD_AVAILABILITY = "PERIOD_AVAILABILITY"
    MISSING_ASSIGNMENT = "MISSING_ASSIGNMENT"
    INVALID_ASSIGNMENT = "INVALID_ASSIGNMENT"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    VERSION_INTEGRITY = "VERSION_INTEGRITY"
    GENERAL = "GENERAL"