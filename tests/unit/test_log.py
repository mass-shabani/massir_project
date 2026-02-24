"""
Unit tests for log module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from massir.core.log import (
    DefaultLogger,
    _FallbackLogger,
    _FallbackConfig,
    log_internal,
    print_banner
)
from massir.core.core_apis import CoreLoggerAPI


class TestFallbackLogger:
    """Tests for _FallbackLogger class."""
    
    def test_log_basic(self, capsys):
        """Test basic log output."""
        logger = _FallbackLogger()
        
        logger.log("Test message")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_log_with_level(self, capsys):
        """Test log with level."""
        logger = _FallbackLogger()
        
        logger.log("Test message", level="ERROR")
        
        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "Test message" in captured.out
    
    def test_log_with_tag(self, capsys):
        """Test log with tag."""
        logger = _FallbackLogger()
        
        logger.log("Test message", tag="mytag")
        
        captured = capsys.readouterr()
        assert "[mytag]" in captured.out
        assert "Test message" in captured.out
    
    def test_log_with_level_and_tag(self, capsys):
        """Test log with level and tag."""
        logger = _FallbackLogger()
        
        logger.log("Test message", level="WARNING", tag="core")
        
        captured = capsys.readouterr()
        assert "[WARNING]" in captured.out
        assert "[core]" in captured.out
        assert "Test message" in captured.out


class TestFallbackConfig:
    """Tests for _FallbackConfig class."""
    
    def test_get_project_name(self):
        """Test get_project_name returns Massir."""
        config = _FallbackConfig()
        
        assert config.get_project_name() == "Massir"
    
    def test_get_system_log_template(self):
        """Test get_system_log_template."""
        config = _FallbackConfig()
        
        template = config.get_system_log_template()
        assert "{level}" in template
        assert "{message}" in template
    
    def test_get_system_log_color_code(self):
        """Test get_system_log_color_code."""
        config = _FallbackConfig()
        
        assert config.get_system_log_color_code() == "96"
    
    def test_is_debug(self):
        """Test is_debug returns True."""
        config = _FallbackConfig()
        
        assert config.is_debug() == True
    
    def test_show_logs(self):
        """Test show_logs returns True."""
        config = _FallbackConfig()
        
        assert config.show_logs() == True
    
    def test_get_hide_log_levels(self):
        """Test get_hide_log_levels returns empty list."""
        config = _FallbackConfig()
        
        assert config.get_hide_log_levels() == []
    
    def test_get_hide_log_tags(self):
        """Test get_hide_log_tags returns empty list."""
        config = _FallbackConfig()
        
        assert config.get_hide_log_tags() == []
    
    def test_show_banner(self):
        """Test show_banner returns True."""
        config = _FallbackConfig()
        
        assert config.show_banner() == True
    
    def test_get_banner_template(self):
        """Test get_banner_template."""
        config = _FallbackConfig()
        
        assert config.get_banner_template() == "{project_name}\n"
    
    def test_get_banner_color_code(self):
        """Test get_banner_color_code."""
        config = _FallbackConfig()
        
        assert config.get_banner_color_code() == "33"


class TestDefaultLogger:
    """Tests for DefaultLogger class."""
    
    def test_init_with_none_config(self):
        """Test initialization with None config uses fallback."""
        logger = DefaultLogger(None)
        
        assert isinstance(logger.config, _FallbackConfig)
    
    def test_init_with_config(self):
        """Test initialization with config."""
        mock_config = Mock()
        
        logger = DefaultLogger(mock_config)
        
        assert logger.config == mock_config
    
    def test_is_core_logger_api(self):
        """Test DefaultLogger implements CoreLoggerAPI."""
        logger = DefaultLogger(None)
        
        assert isinstance(logger, CoreLoggerAPI)
    
    def test_log_calls_should_log(self):
        """Test log calls _should_log."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.get_hide_log_tags.return_value = []
        mock_config.get_hide_log_levels.return_value = []
        mock_config.is_debug.return_value = True
        mock_config.get_system_log_template.return_value = "[{level}] {message}"
        mock_config.get_system_log_color_code.return_value = "96"
        mock_config.get_project_name.return_value = "Test"
        
        logger = DefaultLogger(mock_config)
        
        logger.log("Test message", level="INFO")
        
        mock_config.show_logs.assert_called()
    
    def test_should_log_returns_true_when_show_logs(self):
        """Test _should_log returns True when show_logs is True."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.get_hide_log_tags.return_value = []
        mock_config.get_hide_log_levels.return_value = []
        mock_config.is_debug.return_value = True
        
        logger = DefaultLogger(mock_config)
        
        assert logger._should_log("INFO") == True
    
    def test_should_log_returns_false_when_hide_logs(self):
        """Test _should_log returns False when show_logs is False."""
        mock_config = Mock()
        mock_config.show_logs.return_value = False
        
        logger = DefaultLogger(mock_config)
        
        assert logger._should_log("INFO") == False
    
    def test_should_log_returns_false_for_hidden_tag(self):
        """Test _should_log returns False for hidden tag."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.get_hide_log_tags.return_value = ["hidden_tag"]
        mock_config.get_hide_log_levels.return_value = []
        mock_config.is_debug.return_value = True
        
        logger = DefaultLogger(mock_config)
        
        assert logger._should_log("INFO", tag="hidden_tag") == False
    
    def test_should_log_returns_false_for_hidden_level(self):
        """Test _should_log returns False for hidden level."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.get_hide_log_tags.return_value = []
        mock_config.get_hide_log_levels.return_value = ["DEBUG"]
        mock_config.is_debug.return_value = True
        
        logger = DefaultLogger(mock_config)
        
        assert logger._should_log("DEBUG") == False
    
    def test_should_log_returns_false_for_critical_in_production(self):
        """Test _should_log returns False for critical levels in production."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.get_hide_log_tags.return_value = []
        mock_config.get_hide_log_levels.return_value = []
        mock_config.is_debug.return_value = False  # Production mode
        
        logger = DefaultLogger(mock_config)
        
        # Critical levels should be hidden in production
        assert logger._should_log("ERROR") == False
        assert logger._should_log("WARNING") == False


class TestLogInternal:
    """Tests for log_internal function."""
    
    def test_log_internal_with_logger(self):
        """Test log_internal with logger API."""
        mock_logger = Mock()
        
        log_internal(None, mock_logger, "Test message", level="INFO", tag="test")
        
        mock_logger.log.assert_called_once()
    
    def test_log_internal_without_logger(self, capsys):
        """Test log_internal without logger API falls back to print."""
        log_internal(None, None, "Test message", level="INFO", tag="test")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_log_internal_passes_correct_args(self):
        """Test log_internal passes correct arguments to logger."""
        mock_logger = Mock()
        
        log_internal(None, mock_logger, "Test message", level="WARNING", tag="core")
        
        mock_logger.log.assert_called_with("Test message", level="WARNING", tag="core")


class TestPrintBanner:
    """Tests for print_banner function."""
    
    def test_print_banner_when_enabled(self, capsys):
        """Test print_banner when enabled."""
        mock_config = Mock()
        mock_config.show_banner.return_value = True
        mock_config.get_banner_template.return_value = "{project_name}\n{project_version}"
        mock_config.get_project_name.return_value = "Test Project"
        mock_config.get_project_version.return_value = "1.0.0"
        mock_config.get_project_info.return_value = "Test Info"
        mock_config.get_banner_color_code.return_value = "33"
        
        print_banner(mock_config)
        
        captured = capsys.readouterr()
        assert "Test Project" in captured.out
        assert "1.0.0" in captured.out
    
    def test_print_banner_when_disabled(self, capsys):
        """Test print_banner when disabled."""
        mock_config = Mock()
        mock_config.show_banner.return_value = False
        
        print_banner(mock_config)
        
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_print_banner_uses_template(self, capsys):
        """Test print_banner uses template from config."""
        mock_config = Mock()
        mock_config.show_banner.return_value = True
        mock_config.get_banner_template.return_value = "CUSTOM: {project_name}"
        mock_config.get_project_name.return_value = "MyProject"
        mock_config.get_project_version.return_value = "2.0"
        mock_config.get_project_info.return_value = "Info"
        mock_config.get_banner_color_code.return_value = "33"
        
        print_banner(mock_config)
        
        captured = capsys.readouterr()
        assert "CUSTOM: MyProject" in captured.out
