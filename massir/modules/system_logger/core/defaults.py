"""
Default settings for the system logger module.

This module provides the centralized defaults for all logging and printing
configuration, including colors, templates, filtering, and styles.

All defaults are defined in SystemLoggerDefaults dataclass and can be
injected into the project settings via apply_module_defaults().
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from massir.modules.system_logger.core.colors import Colors


@dataclass
class SystemLoggerDefaults:
    """
    Centralized default settings for the system logger module.
    
    All logging and printing defaults are defined here. When the module starts,
    these defaults are injected into the project settings, allowing users to
    override them in app_settings.json or initial_settings.
    """
    # -------------------------------------------------------------------------
    # Colors
    # -------------------------------------------------------------------------
    banner_color: str = "yellow"
    log_color: str = "bright_cyan"
    print_color: str = "yellow"
    
    # Section-specific log colors (fall back to log_color when not set)
    default_level_color: str = "bright_cyan"
    default_timestamp_color: str = "bright_cyan"
    default_tag_color: str = "bright_cyan"
    default_text_color: str = "bright_cyan"
    default_level_bg_color: Optional[str] = None
    default_timestamp_bg_color: Optional[str] = None
    default_tag_bg_color: Optional[str] = None
    default_text_bg_color: Optional[str] = None
    
    # -------------------------------------------------------------------------
    # Logging behavior
    # -------------------------------------------------------------------------
    show_logs: bool = True
    show_banner: bool = True
    hide_log_levels: List[str] = field(default_factory=list)
    hide_log_tags: List[str] = field(default_factory=list)
    debug_mode: bool = False
    show_critical_levels: int = 3
    
    # -------------------------------------------------------------------------
    # Log styles (defaults applied when method params are not provided)
    # -------------------------------------------------------------------------
    default_log_bold: bool = False
    default_log_underline: bool = False
    default_log_italic: bool = False
    default_log_dim: bool = False
    default_log_blink: bool = False
    default_log_inverse: bool = False
    
    # -------------------------------------------------------------------------
    # Print styles (defaults applied when method params are not provided)
    # -------------------------------------------------------------------------
    default_print_bold: bool = False
    default_print_underline: bool = False
    default_print_italic: bool = False
    default_print_dim: bool = False
    default_print_blink: bool = False
    default_print_inverse: bool = False
    
    # -------------------------------------------------------------------------
    # Level colors (maps log level to color name)
    # -------------------------------------------------------------------------
    level_colors: Dict[str, str] = field(default_factory=lambda: {
        "INFO": "bright_cyan",
        "DEBUG": "bright_black",
        "WARNING": "bright_yellow",
        "ERROR": "bright_red",
        "CRITICAL": "bright_red",
        "CORE": "bright_green",
    })

    def to_dict(self) -> dict:
        """
        Convert defaults to a nested dictionary for settings injection.
        
        Returns:
            Dictionary with 'template' and 'logs' sections
        """
        return {
            "template": {
                "banner_color": self.banner_color,
                "log_color": self.log_color,
                "print_color": self.print_color,
                "default_level_color": self.default_level_color,
                "default_timestamp_color": self.default_timestamp_color,
                "default_tag_color": self.default_tag_color,
                "default_text_color": self.default_text_color,
                "default_level_bg_color": self.default_level_bg_color,
                "default_timestamp_bg_color": self.default_timestamp_bg_color,
                "default_tag_bg_color": self.default_tag_bg_color,
                "default_text_bg_color": self.default_text_bg_color,
            },
            "logs": {
                "show_logs": self.show_logs,
                "show_banner": self.show_banner,
                "hide_log_levels": list(self.hide_log_levels),
                "hide_log_tags": list(self.hide_log_tags),
                "debug_mode": self.debug_mode,
                "show_critical_levels": self.show_critical_levels,
                "default_log_bold": self.default_log_bold,
                "default_log_underline": self.default_log_underline,
                "default_log_italic": self.default_log_italic,
                "default_log_dim": self.default_log_dim,
                "default_log_blink": self.default_log_blink,
                "default_log_inverse": self.default_log_inverse,
                "default_print_bold": self.default_print_bold,
                "default_print_underline": self.default_print_underline,
                "default_print_italic": self.default_print_italic,
                "default_print_dim": self.default_print_dim,
                "default_print_blink": self.default_print_blink,
                "default_print_inverse": self.default_print_inverse,
                "level_colors": dict(self.level_colors),
            },
        }


def get_color_code(color_name: Optional[str]) -> str:
    """
    Convert a color name to its ANSI foreground color code.
    
    This function delegates to Colors.get_code() for color lookup.
    
    Args:
        color_name: Color name (e.g., "red", "bright_cyan", "green")
        
    Returns:
        ANSI color code string (e.g., "31", "96")
    """
    return Colors.get_code(color_name)
