from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SystemLoggerDefaults:
    banner_color: str = "yellow"
    log_color: str = "bright_cyan"
    print_color: str = "white"
    show_logs: bool = True
    show_banner: bool = True
    hide_log_levels: List[str] = field(default_factory=list)
    hide_log_tags: List[str] = field(default_factory=list)
    debug_mode: bool = False
    default_log_bold: bool = False
    default_log_underline: bool = False
    default_log_italic: bool = False
    default_log_dim: bool = False
    default_print_bold: bool = False
    default_print_underline: bool = False
    default_print_italic: bool = False
    default_print_dim: bool = False
    level_colors: Dict[str, str] = field(default_factory=lambda: {
        "INFO": "bright_cyan",
        "DEBUG": "bright_black",
        "WARNING": "bright_yellow",
        "ERROR": "bright_red",
        "CRITICAL": "bright_red",
        "CORE": "bright_green",
    })

    def to_dict(self) -> dict:
        return {
            "template": {
                "banner_color": self.banner_color,
                "log_color": self.log_color,
                "print_color": self.print_color,
            },
            "logs": {
                "show_logs": self.show_logs,
                "show_banner": self.show_banner,
                "hide_log_levels": self.hide_log_levels,
                "hide_log_tags": self.hide_log_tags,
                "debug_mode": self.debug_mode,
                "default_log_bold": self.default_log_bold,
                "default_log_underline": self.default_log_underline,
                "default_log_italic": self.default_log_italic,
                "default_log_dim": self.default_log_dim,
                "default_print_bold": self.default_print_bold,
                "default_print_underline": self.default_print_underline,
                "default_print_italic": self.default_print_italic,
                "default_print_dim": self.default_print_dim,
                "level_colors": self.level_colors,
            },
        }


COLOR_NAME_TO_CODE: Dict[str, str] = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}


def get_color_code(color_name: Optional[str]) -> str:
    if not color_name:
        return "37"
    return COLOR_NAME_TO_CODE.get(color_name.lower(), "37")
