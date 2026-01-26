from enum import Enum

class SystemHook(Enum):
    ON_KERNEL_BOOTSTRAP_START = "on_kernel_bootstrap_start"
    ON_KERNEL_BOOTSTRAP_END = "on_kernel_bootstrap_end"
    ON_MODULE_LOADED = "on_module_loaded"
    ON_ERROR = "on_error"