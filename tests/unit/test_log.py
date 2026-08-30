"""
Unit tests for log module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from massir.core.log import (
    DefaultLogger,
    _FallbackConfig,
    print_banner
)
from massir.core.core_apis import CoreLoggerAPI


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
        mock_config.get_show_critical_levels.return_value = 3
        mock_config.is_debug.return_value = True
        mock_config.get_system_log_template.return_value = "[{level}] {message}"
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
        mock_config.get_show_critical_levels.return_value = 3
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
    
    def test_should_log_returns_false_for_critical_when_disabled(self):
        """Test _should_log returns False for critical levels when show_critical_levels=0."""
        mock_config = Mock()
        mock_config.show_logs.return_value = True
        mock_config.get_hide_log_tags.return_value = []
        mock_config.get_hide_log_levels.return_value = []
        mock_config.is_debug.return_value = False  # Production mode
        mock_config.get_show_critical_levels.return_value = 0
        
        logger = DefaultLogger(mock_config)
        
        # Critical levels should be hidden when show_critical_levels=0
        assert logger._should_log("ERROR") == False
        assert logger._should_log("WARNING") == False
        # CORE should also be hidden in production (debug_mode=False)
        assert logger._should_log("CORE") == False


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
        
        print_banner(mock_config)
        
        captured = capsys.readouterr()
        assert "CUSTOM: MyProject" in captured.out
