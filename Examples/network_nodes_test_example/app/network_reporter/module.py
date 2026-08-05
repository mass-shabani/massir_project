"""
Network Reporter Module

Generates a comprehensive report of all system_network test results
during application shutdown. Displays a formatted table showing:
- Test results (pass/fail)
- Network statistics
- Message counts
- Routing information
- Connection events

This module hooks into the shutdown process to display the final report.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from massir.core.interfaces import IModule


class NetworkReporterModule(IModule):
    """
    Reporter module that displays test results during shutdown.
    """
    
    name = "network_reporter"
    
    def __init__(self):
        self.network_api = None
        self.test_results_service = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
    
    async def load(self, context):
        """Load the module."""
        self.network_api = context.services.get("network_api")
        self.test_results_service = context.services.get("test_results_service")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("network_reporter", {})
        
        if self.logger:
            self.logger.log("NetworkReporterModule loaded", tag="reporter")
    
    async def start(self, context):
        """Start the module."""
        if self.logger:
            self.logger.log("NetworkReporter ready", tag="reporter")
    
    async def ready(self, context):
        """Called when all modules are ready."""
        pass
    
    async def stop(self, context):
        """
        Generate and display the final report during shutdown.
        This is called when the application is shutting down.
        """
        if not self._config.get("show_report_on_shutdown", True):
            return
        
        if not self.test_results_service:
            return
        
        # Get test results
        results_data = self.test_results_service.get_test_results()
        
        # Generate report
        await self._generate_report(results_data)
    
    async def _generate_report(self, results_data: Dict):
        """Generate and display the comprehensive test report."""
        if not self.logger:
            return
        
        results = results_data.get("results", {})
        stats = results_data.get("stats", {})
        
        # Report header
        self._print_separator("═", "BRIGHT_CYAN")
        self.logger.print(
            "  📊 COMPREHENSIVE SYSTEM_NETWORK TEST REPORT",
            tag="reporter",
            color=self.colors.BRIGHT_CYAN if self.colors else None,
            bold=True
        )
        self._print_separator("═", "BRIGHT_CYAN")
        
        # Test results table
        await self._print_test_results_table(results)
        
        # Statistics table
        await self._print_statistics_table(stats)
        
        # Network status
        await self._print_network_status()
        
        # Summary
        await self._print_summary(results, stats)
        
        # Footer
        self._print_separator("═", "BRIGHT_CYAN")
        self.logger.print(
            "  ✅ REPORT COMPLETE - SHUTDOWN INITIATED",
            tag="reporter",
            color=self.colors.BRIGHT_GREEN if self.colors else None,
            bold=True
        )
        self._print_separator("═", "BRIGHT_CYAN")
    
    async def _print_test_results_table(self, results: Dict):
        """Print test results in a formatted table."""
        self.logger.print(
            "\n┌─────────────────────────────────────────────────────────────┐",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
        self.logger.print(
            "│  🧪 TEST RESULTS                                            │",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None,
            bold=True
        )
        self.logger.print(
            "├─────────────────────────────────────────────────────────────┤",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
        
        # Table header
        self.logger.print(
            "│  Test Name                    │ Status  │ Details           │",
            tag="reporter",
            color=self.colors.BRIGHT_WHITE if self.colors else None,
            bold=True
        )
        self.logger.print(
            "├─────────────────────────────────────────────────────────────┤",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
        
        # Table rows
        for test_name, result in results.items():
            passed = result.get("passed", False)
            status = "✅ PASS" if passed else "❌ FAIL"
            status_color = self.colors.BRIGHT_GREEN if passed else self.colors.BRIGHT_RED
            
            # Get details
            details = self._get_test_details(test_name, result)
            
            # Format row
            test_name_padded = test_name[:28].ljust(28)
            status_padded = status[:8].ljust(8)
            details_padded = details[:18].ljust(18)
            
            self.logger.print(
                f"│  {test_name_padded} │ {status_padded} │ {details_padded} │",
                tag="reporter",
                color=status_color if self.colors else None
            )
        
        self.logger.print(
            "└─────────────────────────────────────────────────────────────┘",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
    
    def _get_test_details(self, test_name: str, result: Dict) -> str:
        """Get details string for a test result."""
        if test_name == "network_status":
            status = result.get("status", {})
            health = status.get("health_percentage", 0)
            return f"Health: {health:.0f}%"
        
        elif test_name == "direct_messaging":
            is_direct = result.get("is_direct", False)
            return "Direct" if is_direct else "Multi-hop"
        
        elif test_name == "broadcast":
            success_count = result.get("success_count", 0)
            return f"{success_count} peers"
        
        elif test_name == "capability_messaging":
            caps = result.get("capabilities_tested", 0)
            return f"{caps} capabilities"
        
        elif test_name == "routing_table":
            total = result.get("total_routes", 0)
            direct = result.get("direct_routes", 0)
            return f"{direct}/{total} direct"
        
        elif test_name == "multi_hop":
            hops = result.get("hops", 0)
            return f"{hops} hops" if hops > 0 else "N/A"
        
        elif test_name == "envelope_inspection":
            count = result.get("envelopes_received", 0)
            return f"{count} envelopes"
        
        elif test_name == "event_handlers":
            conns = result.get("peer_connections", 0)
            return f"{conns} connections"
        
        return ""
    
    async def _print_statistics_table(self, stats: Dict):
        """Print statistics in a formatted table."""
        self.logger.print(
            "\n┌─────────────────────────────────────────────────────────────┐",
            tag="reporter",
            color=self.colors.BRIGHT_MAGENTA if self.colors else None
        )
        self.logger.print(
            "│  📈 STATISTICS                                              │",
            tag="reporter",
            color=self.colors.BRIGHT_MAGENTA if self.colors else None,
            bold=True
        )
        self.logger.print(
            "├─────────────────────────────────────────────────────────────┤",
            tag="reporter",
            color=self.colors.BRIGHT_MAGENTA if self.colors else None
        )
        
        # Statistics rows
        stat_items = [
            ("Messages Sent", stats.get("messages_sent", 0)),
            ("Messages Received", stats.get("messages_received", 0)),
            ("Broadcasts Sent", stats.get("broadcasts_sent", 0)),
            ("Capability Messages", stats.get("capability_messages_sent", 0)),
            ("Peer Connections", stats.get("peer_connections", 0)),
            ("Peer Disconnections", stats.get("peer_disconnections", 0)),
        ]
        
        for label, value in stat_items:
            label_padded = label[:35].ljust(35)
            value_str = str(value).rjust(10)
            
            self.logger.print(
                f"│  {label_padded} │ {value_str} │",
                tag="reporter",
                color=self.colors.BRIGHT_WHITE if self.colors else None
            )
        
        # Timing info
        start_time = stats.get("test_start_time")
        end_time = stats.get("test_end_time")
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration = (end_dt - start_dt).total_seconds()
                
                self.logger.print(
                    "├─────────────────────────────────────────────────────────────┤",
                    tag="reporter",
                    color=self.colors.BRIGHT_MAGENTA if self.colors else None
                )
                
                duration_str = f"Duration: {duration:.1f}s"
                self.logger.print(
                    f"│  {duration_str:<57} │",
                    tag="reporter",
                    color=self.colors.BRIGHT_CYAN if self.colors else None
                )
            except Exception:
                pass
        
        self.logger.print(
            "└─────────────────────────────────────────────────────────────┘",
            tag="reporter",
            color=self.colors.BRIGHT_MAGENTA if self.colors else None
        )
    
    async def _print_network_status(self):
        """Print current network status."""
        status = self.network_api.get_network_status()
        
        self.logger.print(
            "\n┌─────────────────────────────────────────────────────────────┐",
            tag="reporter",
            color=self.colors.BRIGHT_GREEN if self.colors else None
        )
        self.logger.print(
            "│  🌐 FINAL NETWORK STATUS                                    │",
            tag="reporter",
            color=self.colors.BRIGHT_GREEN if self.colors else None,
            bold=True
        )
        self.logger.print(
            "├─────────────────────────────────────────────────────────────┤",
            tag="reporter",
            color=self.colors.BRIGHT_GREEN if self.colors else None
        )
        
        status_items = [
            ("Self Node", status.self_node_id),
            ("Topology", status.topology),
            ("Total Nodes", str(status.total_nodes)),
            ("Required Peers", str(status.required_peers)),
            ("Connected Peers", str(status.connected_peers)),
            ("Health", f"{status.health_percentage:.1f}%"),
            ("Fully Connected", "Yes" if status.is_fully_connected else "No"),
        ]
        
        for label, value in status_items:
            label_padded = label[:35].ljust(35)
            value_padded = str(value)[:18].ljust(18)
            
            self.logger.print(
                f"│  {label_padded} │ {value_padded} │",
                tag="reporter",
                color=self.colors.BRIGHT_WHITE if self.colors else None
            )
        
        self.logger.print(
            "└─────────────────────────────────────────────────────────────┘",
            tag="reporter",
            color=self.colors.BRIGHT_GREEN if self.colors else None
        )
    
    async def _print_summary(self, results: Dict, stats: Dict):
        """Print summary with pass/fail counts."""
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get("passed"))
        failed_tests = total_tests - passed_tests
        
        self.logger.print(
            "\n┌─────────────────────────────────────────────────────────────┐",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
        self.logger.print(
            "│  📋 SUMMARY                                                 │",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None,
            bold=True
        )
        self.logger.print(
            "├─────────────────────────────────────────────────────────────┤",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
        
        # Pass/Fail summary
        summary_items = [
            ("Total Tests", str(total_tests)),
            ("Passed", f"{passed_tests} ✅"),
            ("Failed", f"{failed_tests} ❌" if failed_tests > 0 else "0 ✅"),
            ("Success Rate", f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A"),
        ]
        
        for label, value in summary_items:
            label_padded = label[:35].ljust(35)
            value_padded = str(value)[:18].ljust(18)
            
            color = None
            if self.colors:
                if "✅" in value:
                    color = self.colors.BRIGHT_GREEN
                elif "❌" in value:
                    color = self.colors.BRIGHT_RED
            
            self.logger.print(
                f"│  {label_padded} │ {value_padded} │",
                tag="reporter",
                color=color
            )
        
        # Overall verdict
        self.logger.print(
            "├─────────────────────────────────────────────────────────────┤",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
        
        if failed_tests == 0:
            verdict = "🎉 ALL TESTS PASSED - SYSTEM_NETWORK FULLY OPERATIONAL"
            verdict_color = self.colors.BRIGHT_GREEN if self.colors else None
        else:
            verdict = f"⚠️  {failed_tests} TEST(S) FAILED - REVIEW REQUIRED"
            verdict_color = self.colors.BRIGHT_YELLOW if self.colors else None
        
        self.logger.print(
            f"│  {verdict:<57} │",
            tag="reporter",
            color=verdict_color,
            bold=True
        )
        
        self.logger.print(
            "└─────────────────────────────────────────────────────────────┘",
            tag="reporter",
            color=self.colors.BRIGHT_YELLOW if self.colors else None
        )
    
    def _print_separator(self, char: str, color_name: str):
        """Print a separator line."""
        if not self.logger:
            return
        
        color = getattr(self.colors, color_name, None) if self.colors else None
        self.logger.print(
            char * 64,
            tag="reporter",
            color=color,
            bold=True
        )
