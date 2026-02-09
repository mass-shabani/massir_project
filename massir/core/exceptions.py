"""
Framework exception classes.
"""


class FrameworkError(Exception):
    """
    Base exception for the framework.

    All framework-specific exceptions inherit from this class.
    """
    pass


class ModuleLoadError(FrameworkError):
    """
    Exception raised when a module fails to load.

    This exception is raised when there is an error during
    module discovery, instantiation, or loading.
    """
    pass


class DependencyResolutionError(FrameworkError):
    """
    Exception raised when module dependencies cannot be resolved.

    This exception is raised when a module requires a capability
    that is not provided by any other module.
    """
    pass