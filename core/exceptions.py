class FrameworkError(Exception):
    """Base exception for the framework"""
    pass

class ModuleLoadError(FrameworkError):
    pass

class DependencyResolutionError(FrameworkError):
    pass