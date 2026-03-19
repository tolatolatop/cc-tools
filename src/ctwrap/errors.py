class CtwrapError(Exception):
    """Base error for ctwrap."""


class ConfigError(CtwrapError):
    """Raised when configuration is invalid."""


class CompileDbError(CtwrapError):
    """Raised when compile_commands.json handling fails."""


class ToolError(CtwrapError):
    """Raised when an external tool is missing or unusable."""
