"""The expected layout of a Token Blast "levels" CSV file.

Every file the app loads must have all of these columns. If the game ever adds
or renames a column, update the lists below.
"""

# Text columns: kept as-is.
TEXT_COLUMNS = [
    "participant_id",
    "session_id",
    "model",
    "word",
    "correct_split",
    "result",
]

# Number columns: converted to numbers when loaded.
NUMBER_COLUMNS = [
    "run",
    "level",
    "difficulty",
    "time_in_level_ms",
    "level_points",
    "score",
    "tokens_correct",
    "tokens_wrong_order",
    "tokens_distractor",
    "concept_accuracy",
    "hints_used",
    "feedback_read_ms",
]

# Date/time column (stored in the files as UTC).
TIME_COLUMN = "timestamp"

REQUIRED_COLUMNS = [TIME_COLUMN] + TEXT_COLUMNS + NUMBER_COLUMNS

# Columns offered as filters in the app.
FILTER_COLUMNS = ["model", "difficulty", "level", "run", "result", "participant_id", "session_id"]
