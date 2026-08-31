"""
ANSI color codes and styles for terminal output.

This module provides a comprehensive set of ANSI escape codes including:
- Standard and bright foreground colors (16 colors)
- Standard and bright background colors (16 colors)
- 256-color palette support
- Common named colors
- Text styles (bold, italic, dim, etc.)

Usage:
    from massir.modules.system_logger.core.colors import Colors
    
    # Use constants
    print(f"{Colors.RED}Error{Colors.RESET}")
    
    # Lookup by name
    code = Colors.get_code("bright_cyan")
    
    # Build 256-color code
    code = Colors.ansi_fg(42)  # foreground color 42
    code = Colors.ansi_bg(42)  # background color 42
"""
from typing import Dict, Optional


class Colors:
    """
    ANSI escape codes for terminal styling.
    
    All attributes are class-level constants containing raw ANSI escape sequences.
    """
    
    # =========================================================================
    # Reset and text styles
    # =========================================================================
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'
    
    # =========================================================================
    # Standard Foreground Colors (8 colors) - codes 30-37
    # =========================================================================
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # =========================================================================
    # Bright Foreground Colors (8 colors) - codes 90-97
    # =========================================================================
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # =========================================================================
    # Extended Foreground Colors (8 additional colors) - 256-color palette
    # =========================================================================
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;218m'
    PURPLE = '\033[38;5;141m'
    LIME = '\033[38;5;154m'
    TEAL = '\033[38;5;14m'
    NAVY = '\033[38;5;18m'
    MAROON = '\033[38;5;88m'
    OLIVE = '\033[38;5;58m'
    
    # =========================================================================
    # Default color (uses system default)
    # =========================================================================
    DEFAULT = ''
    
    # =========================================================================
    # Standard Background Colors (8 colors) - codes 40-47
    # =========================================================================
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # =========================================================================
    # Bright Background Colors (8 colors) - codes 100-107
    # =========================================================================
    BG_BRIGHT_BLACK = '\033[100m'
    BG_BRIGHT_RED = '\033[101m'
    BG_BRIGHT_GREEN = '\033[102m'
    BG_BRIGHT_YELLOW = '\033[103m'
    BG_BRIGHT_BLUE = '\033[104m'
    BG_BRIGHT_MAGENTA = '\033[105m'
    BG_BRIGHT_CYAN = '\033[106m'
    BG_BRIGHT_WHITE = '\033[107m'

    # =========================================================================
    # Extended Background Colors (8 additional colors) - 256-color palette
    # =========================================================================
    BG_ORANGE = '\033[48;5;208m'
    BG_PINK = '\033[48;5;218m'
    BG_PURPLE = '\033[48;5;141m'
    BG_LIME = '\033[48;5;154m'
    BG_TEAL = '\033[48;5;14m'
    BG_NAVY = '\033[48;5;18m'
    BG_MAROON = '\033[48;5;88m'
    BG_OLIVE = '\033[48;5;58m'

    # =========================================================================
    # Named color mappings
    # =========================================================================
    _NAME_TO_CODE: Dict[str, str] = {
        # Standard foreground
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        # Bright foreground
        "bright_black": "90",
        "bright_red": "91",
        "bright_green": "92",
        "bright_yellow": "93",
        "bright_blue": "94",
        "bright_magenta": "95",
        "bright_cyan": "96",
        "bright_white": "97",
        # Default
        "default": "",
        # Extended aliases
        "orange": "38;5;208",
        "pink": "38;5;218",
        "purple": "38;5;141",
        "lime": "38;5;154",
        "teal": "38;5;14",
        "navy": "38;5;18",
        "maroon": "38;5;88",
        "olive": "38;5;58",
        "gray": "90",
        "grey": "90",
        "aqua": "36",
        "silver": "37",
    }
    
    _BG_NAME_TO_CODE: Dict[str, str] = {
        # Standard background
        "black": "40",
        "red": "41",
        "green": "42",
        "yellow": "43",
        "blue": "44",
        "magenta": "45",
        "cyan": "46",
        "white": "47",
        # Bright background
        "bright_black": "100",
        "bright_red": "101",
        "bright_green": "102",
        "bright_yellow": "103",
        "bright_blue": "104",
        "bright_magenta": "105",
        "bright_cyan": "106",
        "bright_white": "107",
        # Default
        "default": "",
        # Extended aliases
        "orange": "48;5;208",
        "pink": "48;5;218",
        "purple": "48;5;141",
        "lime": "48;5;154",
        "teal": "48;5;14",
        "navy": "48;5;18",
        "maroon": "48;5;88",
        "olive": "48;5;58",
        "gray": "100",
        "grey": "100",
        "aqua": "46",
        "silver": "47",
    }
    
    @classmethod
    def get_code(cls, name: Optional[str]) -> str:
        """
        Get ANSI foreground color code by name.
        
        Args:
            name: Color name (e.g., "red", "bright_cyan", "green", "default")
            
        Returns:
            ANSI color code string (e.g., "31", "96", "")
        """
        if not name:
            return ""
        return cls._NAME_TO_CODE.get(name.lower(), "37")
    
    @classmethod
    def get_bg_code(cls, name: Optional[str]) -> str:
        """
        Get ANSI background color code by name.
        
        Args:
            name: Color name (e.g., "red", "bright_cyan", "green", "default")
            
        Returns:
            ANSI background color code string (e.g., "41", "106", "")
        """
        if not name:
            return ""
        return cls._BG_NAME_TO_CODE.get(name.lower(), "")
    
    @classmethod
    def ansi_fg(cls, color_id: int) -> str:
        """
        Build ANSI foreground escape code for 256-color palette.
        
        Args:
            color_id: Color index (0-255)
            
        Returns:
            ANSI escape sequence string
        """
        return f"\033[38;5;{color_id}m"
    
    @classmethod
    def ansi_bg(cls, color_id: int) -> str:
        """
        Build ANSI background escape code for 256-color palette.
        
        Args:
            color_id: Color index (0-255)
            
        Returns:
            ANSI escape sequence string
        """
        return f"\033[48;5;{color_id}m"
    
    @classmethod
    def ansi_rgb_fg(cls, r: int, g: int, b: int) -> str:
        """
        Build ANSI foreground escape code for true color (24-bit).
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            
        Returns:
            ANSI escape sequence string
        """
        return f"\033[38;2;{r};{g};{b}m"
    
    @classmethod
    def ansi_rgb_bg(cls, r: int, g: int, b: int) -> str:
        """
        Build ANSI background escape code for true color (24-bit).
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            
        Returns:
            ANSI escape sequence string
        """
        return f"\033[48;2;{r};{g};{b}m"
    
    @classmethod
    def apply(cls, text: str, fg: Optional[str] = None, bg: Optional[str] = None,
              bold: bool = False, italic: bool = False, dim: bool = False,
              underline: bool = False, blink: bool = False, inverse: bool = False) -> str:
        """
        Apply ANSI styling to text.
        
        Args:
            text: Text to style
            fg: Foreground color name or raw ANSI code
            bg: Background color name or raw ANSI code
            bold: Bold text
            italic: Italic text
            dim: Dim text
            underline: Underlined text
            blink: Blinking text
            inverse: Swap foreground/background
            
        Returns:
            Styled text string
        """
        codes = []
        
        if fg:
            if isinstance(fg, str) and fg.startswith('\033['):
                codes.append(fg)
            else:
                codes.append(f"\033[{cls.get_code(fg)}m")
        
        if bg:
            if isinstance(bg, str) and bg.startswith('\033['):
                codes.append(bg)
            else:
                codes.append(f"\033[{cls.get_bg_code(bg)}m")
        
        if bold:
            codes.append('\033[1m')
        if italic:
            codes.append('\033[3m')
        if dim:
            codes.append('\033[2m')
        if underline:
            codes.append('\033[4m')
        if blink:
            codes.append('\033[5m')
        if inverse:
            codes.append('\033[7m')
        
        if codes:
            return "".join(codes) + text + cls.RESET
        return text
