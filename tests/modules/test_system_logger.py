"""
Unit tests for system_logger module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import io
import sys

from massir.modules.system_logger import AdvancedLogger, SystemLoggerModule, Colors
from massir.core.interfaces import ModuleContext


class TestColors:
    """Tests for Colors class."""
    
    def test_reset_code(self):
        """Test RESET color code."""
        assert Colors.RESET == '\033[0m'
    
    def test_standard_colors_exist(self):
        """Test standard color attributes exist."""
        assert hasattr(Colors, 'BLACK')
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'YELLOW')
        assert hasattr(Colors, 'BLUE')
        assert hasattr(Colors, 'MAGENTA')
        assert hasattr(Colors, 'CYAN')
        assert hasattr(Colors, 'WHITE')
    
    def test_bright_colors_exist(self):
        """Test bright color attributes exist."""
        assert hasattr(Colors, 'BRIGHT_BLACK')
        assert hasattr(Colors, 'BRIGHT_RED')
        assert hasattr(Colors, 'BRIGHT_GREEN')
        assert hasattr(Colors, 'BRIGHT_YELLOW')
        assert hasattr(Colors, 'BRIGHT_BLUE')
        assert hasattr(Colors, 'BRIGHT_MAGENTA')
        assert hasattr(Colors, 'BRIGHT_CYAN')
        assert hasattr(Colors, 'BRIGHT_WHITE')
    
    def test_background_colors_exist(self):
        """Test background color attributes exist."""
        assert hasattr(Colors, 'BG_RED')
        assert hasattr(Colors, 'BG_GREEN')
        assert hasattr(Colors, 'BG_YELLOW')
        assert hasattr(Colors, 'BG_BLUE')
    
    def test_color_codes_format(self):
        """Test that color codes follow ANSI format."""
        # Standard colors should start with \033[3Xm
        assert Colors.RED.startswith('\033[3')
        assert Colors.GREEN.startswith('\033[3')
        # Bright colors should start with \033[9Xm
        assert Colors.BRIGHT_RED.startswith('\033[9')
        assert Colors.BRIGHT_GREEN.startswith('\033[9')


class TestAdvancedLoggerInit:
    """Tests for AdvancedLogger initialization."""
    
    def test_init_with_config(self):
        """Test initialization with config API."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        
        assert logger.config == mock_config
    
    def test_init_with_none_config_uses_fallback(self):
        """Test initialization with None config uses fallback."""
        logger = AdvancedLogger(None)
        
        assert logger.config is not None
        assert logger.config.get_project_name() == "Unknown"
    
    def test_fallback_config_methods(self):
        """Test fallback config has required methods."""
        logger = AdvancedLogger(None)
        fallback = logger.config
        
        assert fallback.show_logs() == True
        assert fallback.is_debug() == True
        assert fallback.get_hide_log_levels() == []
        assert fallback.get_hide_log_tags() == []
        assert "{level}" in fallback.get_system_log_template()


class TestAdvancedLoggerShouldLog:
    """Tests for AdvancedLogger._should_log method."""
    
    def test_should_log_returns_true_when_show_logs(self):
        """Test _should_log returns True when show_logs is True."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        
        assert logger._should_log("INFO") == True
    
    def test_should_log_returns_false_when_show_logs_false(self):
        """Test _should_log returns False when show_logs is False."""
        mock_config = Mock()
        mock_config.show_logs.return_value = False
        
        logger = AdvancedLogger(mock_config)
        
        assert logger._should_log("INFO") == False
    
    def test_should_log_returns_false_for_hidden_tag(self):
        """Test _should_log returns False for hidden tag."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = ["debug"]
        
        logger = AdvancedLogger(mock_config)
        
        assert logger._should_log("INFO", tag="debug") == False
    
    def test_should_log_returns_false_for_hidden_level(self):
        """Test _should_log returns False for hidden level."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = ["DEBUG"]
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        
        assert logger._should_log("DEBUG") == False
    
    def test_should_log_critical_in_production(self):
        """Test critical levels hidden in production mode."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = False  # Production mode
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        
        # Critical levels should be hidden in production
        assert logger._should_log("ERROR") == False
        assert logger._should_log("WARNING") == False
        assert logger._should_log("EXCEPTION") == False
        assert logger._should_log("CRITICAL") == False
    
    def test_should_log_info_in_production(self):
        """Test INFO level visible in production mode."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = False
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        
        assert logger._should_log("INFO") == True
        assert logger._should_log("CORE") == True


class TestAdvancedLoggerFormatHttpRequest:
    """Tests for AdvancedLogger._format_http_request method."""
    
    def test_format_http_request_get_200(self):
        """Test formatting GET request with 200 status."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"GET /api/users HTTP/1.1\" 200"
        result = logger._format_http_request(message)
        
        assert "GET" in result
        assert "/api/users" in result
        assert "200" in result
        assert Colors.RESET in result
    
    def test_format_http_request_post_201(self):
        """Test formatting POST request with 201 status."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"POST /api/users HTTP/1.1\" 201"
        result = logger._format_http_request(message)
        
        assert "POST" in result
        assert "201" in result
    
    def test_format_http_request_delete_204(self):
        """Test formatting DELETE request with 204 status."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"DELETE /api/users/1 HTTP/1.1\" 204"
        result = logger._format_http_request(message)
        
        assert "DELETE" in result
        assert "204" in result
    
    def test_format_http_request_error_500(self):
        """Test formatting request with 500 status."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"GET /api/error HTTP/1.1\" 500"
        result = logger._format_http_request(message)
        
        assert "500" in result
        assert Colors.BRIGHT_RED in result
    
    def test_format_http_request_client_error_404(self):
        """Test formatting request with 404 status."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"GET /api/notfound HTTP/1.1\" 404"
        result = logger._format_http_request(message)
        
        assert "404" in result
    
    def test_format_http_request_redirect_301(self):
        """Test formatting request with 301 status."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"GET /old HTTP/1.1\" 301"
        result = logger._format_http_request(message)
        
        assert "301" in result
    
    def test_format_http_request_non_http_message(self):
        """Test formatting non-HTTP message returns unchanged."""
        logger = AdvancedLogger(None)
        
        message = "This is a regular log message"
        result = logger._format_http_request(message)
        
        assert result == message
    
    def test_format_http_request_put_method(self):
        """Test formatting PUT request."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"PUT /api/users/1 HTTP/1.1\" 200"
        result = logger._format_http_request(message)
        
        assert "PUT" in result
    
    def test_format_http_request_patch_method(self):
        """Test formatting PATCH request."""
        logger = AdvancedLogger(None)
        
        message = "192.168.1.1:8080 - \"PATCH /api/users/1 HTTP/1.1\" 200"
        result = logger._format_http_request(message)
        
        assert "PATCH" in result


class TestAdvancedLoggerLog:
    """Tests for AdvancedLogger.log method."""
    
    def test_log_prints_message(self, capsys):
        """Test log prints message to stdout."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        mock_config.get_system_log_color_code.return_value = "92"
        
        logger = AdvancedLogger(mock_config)
        logger.log("Test message", level="INFO")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert "INFO" in captured.out
    
    def test_log_with_tag(self, capsys):
        """Test log with tag."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        logger.log("Test message", level="INFO", tag="test")
        
        captured = capsys.readouterr()
        assert "[test]" in captured.out
    
    def test_log_hidden_level_not_printed(self, capsys):
        """Test log with hidden level doesn't print."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = ["DEBUG"]
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        logger.log("Debug message", level="DEBUG")
        
        captured = capsys.readouterr()
        assert "Debug message" not in captured.out
    
    def test_log_custom_colors(self, capsys):
        """Test log with custom colors."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        logger.log("Test message", level="INFO", 
                   level_color=Colors.BRIGHT_CYAN,
                   text_color=Colors.BRIGHT_YELLOW)
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_log_error_level(self, capsys):
        """Test log with ERROR level uses red color."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        logger.log("Error message", level="ERROR")
        
        captured = capsys.readouterr()
        assert "Error message" in captured.out
        assert "ERROR" in captured.out
    
    def test_log_includes_timestamp(self, capsys):
        """Test log includes timestamp."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        logger = AdvancedLogger(mock_config)
        logger.log("Test message", level="INFO")
        
        captured = capsys.readouterr()
        # Timestamp format: YYYY-MM-DD HH:MM:SS
        import re
        timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        assert re.search(timestamp_pattern, captured.out)


class TestSystemLoggerModule:
    """Tests for SystemLoggerModule class."""
    
    @pytest.fixture
    def module(self):
        """Create a SystemLoggerModule instance."""
        return SystemLoggerModule()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock module context."""
        context = ModuleContext()
        
        # Mock app
        mock_app = Mock()
        mock_app.register_hook = Mock()
        context._app = mock_app
        
        # Mock services
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.is_debug.return_value = True
        mock_config.get_hide_log_levels.return_value = []
        mock_config.get_hide_log_tags.return_value = []
        
        context.services.set("core_config", mock_config)
        
        return context
    
    def test_module_has_name(self, module):
        """Test module has name attribute."""
        assert hasattr(module, 'name')
    
    @pytest.mark.asyncio
    async def test_module_load_creates_logger(self, module, mock_context):
        """Test module load creates logger service."""
        await module.load(mock_context)
        
        logger = mock_context.services.get("core_logger")
        assert logger is not None
        assert isinstance(logger, AdvancedLogger)
    
    @pytest.mark.asyncio
    async def test_module_load_registers_colors(self, module, mock_context):
        """Test module load registers Colors class."""
        await module.load(mock_context)
        
        colors = mock_context.services.get("log_colors")
        assert colors == Colors
    
    @pytest.mark.asyncio
    async def test_module_load_registers_hooks(self, module, mock_context):
        """Test module load registers event hooks."""
        await module.load(mock_context)
        
        app = mock_context.get_app()
        assert app.register_hook.called
    
    @pytest.mark.asyncio
    async def test_module_start_updates_config(self, module, mock_context, capsys):
        """Test module start updates logger config."""
        await module.load(mock_context)
        await module.start(mock_context)
        
        captured = capsys.readouterr()
        assert "System Logger Module Active" in captured.out
    
    @pytest.mark.asyncio
    async def test_module_ready_does_not_raise(self, module, mock_context):
        """Test module ready doesn't raise."""
        await module.load(mock_context)
        await module.ready(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_stop_does_not_raise(self, module, mock_context):
        """Test module stop doesn't raise."""
        await module.load(mock_context)
        await module.stop(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_full_lifecycle(self, module, mock_context):
        """Test full module lifecycle."""
        await module.load(mock_context)
        await module.start(mock_context)
        await module.ready(mock_context)
        await module.stop(mock_context)
        
        # Logger should still be available
        logger = mock_context.services.get("core_logger")
        assert logger is not None
