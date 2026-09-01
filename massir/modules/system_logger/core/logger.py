"""
Advanced logger implementation with color support and filtering.
"""
import datetime
import os
import re
from typing import List, Optional

from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI
from massir.modules.system_logger.core.colors import Colors
from massir.modules.system_logger.core.defaults import (
    SystemLoggerDefaults,
    get_color_code,
    get_bg_color_code,
)


class AdvancedLogger(CoreLoggerAPI):
    """
    Advanced logger with color support and filtering.
    
    This logger provides enhanced logging capabilities including
    color-coded output, timestamp, and configurable filtering.
    """

    def __init__(self, config_api: CoreConfigAPI):
        """
        Initialize advanced logger.
        
        Args:
            config_api: Configuration API for reading log settings
        """
        self.config = config_api
        if self.config is None:
            self.config = _SystemLoggerFallbackConfig()

    def _get_config_value(self, method_name: str, dict_key: str, default):
        """
        Get value from config, trying method first then dict key.
        
        Args:
            method_name: Name of config method to try first
            dict_key: Dot-notation key for config.get() fallback
            default: Default value if neither method nor key exists
            
        Returns:
            Config value or default
        """
        getter = getattr(self.config, method_name, None)
        if callable(getter):
            return getter()
        if hasattr(self.config, 'get'):
            return self.config.get(dict_key, default)
        return default

    def _should_log(self, level: str, tag: Optional[str] = None) -> bool:
        """
        Check if message should be logged based on config.
        
        Filtering rules:
        1. If show_logs is False, nothing is logged
        2. If tag is in hide_log_tags, message is skipped
        3. If level is in hide_log_levels, message is skipped
        4. Critical levels controlled by show_critical_levels
        5. CORE level hidden when debug_mode is False
        """
        config = self.config
        if not config.show_logs():
            return False
        if tag:
            hidden_tags = config.get_hide_log_tags()
            if isinstance(hidden_tags, list) and tag in hidden_tags:
                return False
        hidden_levels = config.get_hide_log_levels()
        if isinstance(hidden_levels, list):
            if level in hidden_levels:
                return False

        show_critical = self._get_config_value('get_show_critical_levels', 'logs.show_critical_levels', 3)
        if level == "ERROR" and show_critical < 1:
            return False
        if level == "WARNING" and show_critical < 2:
            return False
        if level == "CRITICAL" and show_critical < 3:
            return False

        if not config.is_debug() and level == "CORE":
            return False

        return True

    def _print_formatted(self, kind: str, payload: dict):
        """
        Unified formatting and printing for log and print outputs.
        """
        if not self._should_log(payload.get("level", "INFO"), payload.get("tag")):
            return

        if os.name == 'nt':
            os.system('')

        is_log = kind == "log"

        # Resolve colors with hierarchy
        default_fg = self._get_config_value('get_log_color', 'logs.log_color', 'default')
        default_level_bg = self._get_config_value('get_default_level_bg_color', 'logs.default_level_bg_color', None)
        default_timestamp_bg = self._get_config_value('get_default_timestamp_bg_color', 'logs.default_timestamp_bg_color', None)
        default_tag_bg = self._get_config_value('get_default_tag_bg_color', 'logs.default_tag_bg_color', None)
        default_text_bg = self._get_config_value('get_default_text_bg_color', 'logs.default_text_bg_color', None)

        def _resolve_fg(raw_color, config_key, fallback):
            if raw_color:
                if isinstance(raw_color, str) and raw_color.startswith('\033[') and raw_color.endswith('m'):
                    return raw_color
                return raw_color
            return self._get_config_value(config_key[0], config_key[1], fallback)

        if is_log:
            base_fg = _resolve_fg(payload.get("color"), ('get_log_color', 'logs.log_color'), 'bright_cyan')
            level_colors = {}
            if hasattr(self.config, "get"):
                level_colors = self.config.get("logs.level_colors", {}) or {}
            level = payload.get("level", "INFO")
            default_level_color = self._get_config_value('get_default_level_color', 'logs.default_level_color', base_fg)
            default_timestamp_color = self._get_config_value('get_default_timestamp_color', 'logs.default_timestamp_color', base_fg)
            default_tag_color = self._get_config_value('get_default_tag_color', 'logs.default_tag_color', base_fg)
            default_text_color = self._get_config_value('get_default_text_color', 'logs.default_text_color', base_fg)
            if default_level_color == "default":
                default_level_color = base_fg
            if default_timestamp_color == "default":
                default_timestamp_color = base_fg
            if default_tag_color == "default":
                default_tag_color = base_fg
            if default_text_color == "default":
                default_text_color = base_fg
            resolved_level_color = payload.get("level_color") or level_colors.get(level) or default_level_color
            resolved_timestamp_color = payload.get("timestamp_color") or default_timestamp_color
            resolved_tag_color = payload.get("tag_color") or default_tag_color
            resolved_text_color = payload.get("text_color") or default_text_color
            resolved_level_bg = payload.get("level_bg_color") or payload.get("bg_color") or default_level_bg
            resolved_timestamp_bg = payload.get("timestamp_bg_color") or payload.get("bg_color") or default_timestamp_bg
            resolved_tag_bg = payload.get("tag_bg_color") or payload.get("bg_color") or default_tag_bg
            resolved_text_bg = payload.get("text_bg_color") or payload.get("bg_color") or default_text_bg
        else:
            base_fg = _resolve_fg(payload.get("color"), ('get_print_color', 'logs.print_color'), 'default')
            resolved_level_color = resolved_timestamp_color = resolved_tag_color = resolved_text_color = base_fg
            resolved_level_bg = resolved_timestamp_bg = resolved_tag_bg = resolved_text_bg = (
                payload.get("bg_color") or self._get_config_value('get_default_print_bg_color', 'logs.default_print_bg_color', None)
            )

        # Resolve styles with hierarchy
        style_defaults_prefix = "default_log" if is_log else "default_print"
        default_bold = self._get_config_value(f'get_{style_defaults_prefix}_bold', f'logs.{style_defaults_prefix}_bold', False)
        default_underline = self._get_config_value(f'get_{style_defaults_prefix}_underline', f'logs.{style_defaults_prefix}_underline', False)
        default_italic = self._get_config_value(f'get_{style_defaults_prefix}_italic', f'logs.{style_defaults_prefix}_italic', False)
        default_dim = self._get_config_value(f'get_{style_defaults_prefix}_dim', f'logs.{style_defaults_prefix}_dim', False)
        default_blink = self._get_config_value(f'get_{style_defaults_prefix}_blink', f'logs.{style_defaults_prefix}_blink', False)
        default_inverse = self._get_config_value(f'get_{style_defaults_prefix}_inverse', f'logs.{style_defaults_prefix}_inverse', False)

        bold = payload.get("bold") if payload.get("bold") is not None else default_bold
        underline = payload.get("underline") if payload.get("underline") is not None else default_underline
        italic = payload.get("italic") if payload.get("italic") is not None else default_italic
        dim = payload.get("dim") if payload.get("dim") is not None else default_dim
        blink = payload.get("blink") if payload.get("blink") is not None else default_blink
        inverse = payload.get("inverse") if payload.get("inverse") is not None else default_inverse

        style_codes = []
        if bold:
            style_codes.append("\033[1m")
        if italic:
            style_codes.append("\033[3m")
        if dim:
            style_codes.append("\033[2m")
        if underline:
            style_codes.append("\033[4m")
        if blink:
            style_codes.append("\033[5m")
        if inverse:
            style_codes.append("\033[7m")
        if payload.get("styles"):
            style_codes.extend(payload["styles"])

        def _apply_style(text, fg_color, bg_color=None):
            if isinstance(fg_color, str) and fg_color.startswith('\033[') and fg_color.endswith('m'):
                fg_code = fg_color
            else:
                fg_code_value = get_color_code(fg_color)
                if fg_code_value:
                    fg_code = f"\033[{fg_code_value}m"
                else:
                    fg_code = ""
            codes = []
            if fg_code:
                codes.append(fg_code)
            if bg_color:
                if isinstance(bg_color, str) and bg_color.startswith('\033[') and bg_color.endswith('m'):
                    codes.append(bg_color)
                else:
                    bg_code_value = get_bg_color_code(bg_color)
                    if bg_code_value:
                        codes.append(f"\033[{bg_code_value}m")
            codes.extend(style_codes)
            if codes:
                return "".join(codes) + text + "\033[0m"
            return text

        def _build_ansi(base_fg_color, bg_color=None):
            if isinstance(base_fg_color, str) and base_fg_color.startswith('\033[') and base_fg_color.endswith('m'):
                fg_part = base_fg_color
            else:
                fg_code_value = get_color_code(base_fg_color)
                if fg_code_value:
                    fg_part = f"\033[{fg_code_value}m"
                else:
                    fg_part = ""
            parts = []
            if fg_part:
                parts.append(fg_part)
            if bg_color:
                if isinstance(bg_color, str) and bg_color.startswith('\033[') and bg_color.endswith('m'):
                    parts.append(bg_color)
                else:
                    bg_code_value = get_bg_color_code(bg_color)
                    if bg_code_value:
                        parts.append(f"\033[{bg_code_value}m")
            parts.extend(style_codes)
            return "".join(parts)

        # Build output
        if is_log:
            format_template = payload.get("format_template", "")
            format_kwargs = payload.get("format_kwargs", {})

            class _SafeFormatDict(dict):
                def __missing__(self, key):
                    return ""

            formatted_msg = format_template.format_map(_SafeFormatDict(format_kwargs))

            # First, build the result with all text colored by log_color
            # Then recolor specific parts with their specific colors
            result = ""
            i = 0
            while i < len(format_template):
                if format_template[i] == "{":
                    end = format_template.find("}", i)
                    if end != -1:
                        placeholder = format_template[i:end+1]
                        key = placeholder[1:-1]
                        value = format_kwargs.get(key, "")

                        # Default to log_color for all parts
                        if key == "timestamp":
                            colored = _apply_style(value, resolved_timestamp_color, resolved_timestamp_bg)
                        elif key == "level":
                            colored = _apply_style(value, resolved_level_color, resolved_level_bg)
                        elif key == "tag":
                            colored = _apply_style(value, resolved_tag_color, resolved_tag_bg)
                        elif key == "message":
                            colored = _apply_style(value, resolved_text_color, resolved_text_bg)
                        elif key == "project_name":
                            colored = _apply_style(value, default_fg)
                        else:
                            # Unknown placeholder: color with default log color
                            colored = _apply_style(value, default_fg)

                        result += colored
                        i = end + 1
                        continue
                # Static template text: color with log_color
                result += _apply_style(format_template[i], default_fg)
                i += 1

            if payload.get("prefix"):
                result = payload["prefix"] + result
            if payload.get("suffix"):
                result = result + payload["suffix"]

            print(result)
        else:
            message = payload.get("message") or ""
            if not isinstance(message, str):
                message = repr(message)
            prefix = payload.get("prefix") or ""
            suffix = payload.get("suffix") or ""
            output = f"{prefix}{message}{suffix}"
            ansi = _build_ansi(base_fg, resolved_level_bg)
            if ansi:
                output = ansi + output + Colors.RESET
            print(output, end=payload.get("end") or "\n")

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None,
            color: Optional[str] = None, bg_color: Optional[str] = None,
            level_color: Optional[str] = None, timestamp_color: Optional[str] = None,
            tag_color: Optional[str] = None, text_color: Optional[str] = None,
            timestamp_bg_color: Optional[str] = None,
            level_bg_color: Optional[str] = None,
            tag_bg_color: Optional[str] = None,
            text_bg_color: Optional[str] = None,
            bold: Optional[bool] = None, underline: Optional[bool] = None, italic: Optional[bool] = None,
            dim: Optional[bool] = None, blink: Optional[bool] = None, inverse: Optional[bool] = None,
            prefix: Optional[str] = None, suffix: Optional[str] = None,
            styles: Optional[List[str]] = None):
        """
        Log a message with advanced color and style support.
        """
        template = self.config.get_system_log_template()
        core_default = "[{level}]\t{message}"
        module_default = "{timestamp} | {level}:\t{tag} | {message}"

        if isinstance(template, str) and template != core_default:
            format_template = template
        else:
            format_template = module_default

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        project_name = ""
        if hasattr(self.config, "get_project_name"):
            project_name = self.config.get_project_name()

        format_kwargs = {
            "project_name": project_name,
            "level": level,
            "message": message,
            "tag": tag or "",
            "timestamp": timestamp
        }

        self._print_formatted("log", {
            "level": level,
            "tag": tag,
            "format_template": format_template,
            "format_kwargs": format_kwargs,
            "color": color,
            "bg_color": bg_color,
            "level_color": level_color,
            "timestamp_color": timestamp_color,
            "tag_color": tag_color,
            "text_color": text_color,
            "timestamp_bg_color": timestamp_bg_color,
            "level_bg_color": level_bg_color,
            "tag_bg_color": tag_bg_color,
            "text_bg_color": text_bg_color,
            "bold": bold,
            "underline": underline,
            "italic": italic,
            "dim": dim,
            "blink": blink,
            "inverse": inverse,
            "prefix": prefix,
            "suffix": suffix,
            "styles": styles,
        })

    def print(self,
              message: str,
              level: str = "INFO",
              tag: Optional[str] = None,
              end: str = "\n",
              color: Optional[str] = None,
              bg_color: Optional[str] = None,
              bold: Optional[bool] = None,
              underline: Optional[bool] = None,
              italic: Optional[bool] = None,
              dim: Optional[bool] = None,
              blink: Optional[bool] = None,
              inverse: Optional[bool] = None,
              prefix: Optional[str] = None,
              suffix: Optional[str] = None,
              styles: Optional[List[str]] = None):
        """
        Print raw output with advanced styling options but without log headers.
        """
        self._print_formatted("print", {
            "message": message,
            "level": level,
            "tag": tag,
            "end": end,
            "color": color,
            "bg_color": bg_color,
            "bold": bold,
            "underline": underline,
            "italic": italic,
            "dim": dim,
            "blink": blink,
            "inverse": inverse,
            "prefix": prefix,
            "suffix": suffix,
            "styles": styles,
        })


class _SystemLoggerFallbackConfig:
    """Fallback config based on SystemLoggerDefaults."""
    
    def __init__(self):
        self._defaults = SystemLoggerDefaults()
        hide_log_levels = list(self._defaults.hide_log_levels)
        if not self._defaults.debug_mode and "CORE" not in hide_log_levels:
            hide_log_levels.append("CORE")
        self._hide_log_levels = hide_log_levels

    def get_project_name(self): return "Unknown"
    def get_system_log_template(self): return "[{level}]\t{message}"
    def show_logs(self): return self._defaults.show_logs
    def is_debug(self): return self._defaults.debug_mode
    def get_hide_log_levels(self): return list(self._hide_log_levels)
    def get_hide_log_tags(self): return list(self._defaults.hide_log_tags)
    def get_banner_template(self): return "{project_name}\n"
    def show_banner(self): return self._defaults.show_banner
    def get_log_color(self): return self._defaults.log_color
    def get_print_color(self): return self._defaults.print_color
    def get_banner_color(self): return self._defaults.banner_color
    def get_show_critical_levels(self): return self._defaults.show_critical_levels
    def get(self, key, default=None):
        parts = key.split(".", 1)
        if len(parts) == 2:
            section, name = parts
            if section in ("template", "logs"):
                value = getattr(self._defaults, name, None)
                if value is not None:
                    if isinstance(value, list):
                        return list(value)
                    if isinstance(value, dict):
                        return dict(value)
                    return value
        return default
