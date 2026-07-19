"""
Stream Demo Module

Demonstrates Stream Mode for zero-copy byte passthrough:
- Raw file transfer
- Large data streaming
- Bidirectional byte pipes

OUTPUT STRATEGY:
- logger.print: For stream events (start, progress, complete)
- logger.log: For errors and general info

NOTE: Uses distinct cyan color for stream operations.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List

from massir.core.interfaces import IModule


class StreamDemoModule(IModule):
    """
    Demonstrates Stream Mode (raw bytes) operations.
    """
    
    name = "stream_demo"
    
    def __init__(self):
        self.socket_api = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
    
    async def load(self, context):
        """Load the module."""
        self.socket_api = context.services.get("socket_api")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("stream_demo", {})
        
        # Register service
        context.services.set("stream_service", self)
        
        if self.logger:
            self.logger.log("StreamDemoModule loaded", tag="stream_demo")
    
    async def start(self, context):
        """Start stream demo."""
        if self._config.get("auto_send_on_start", False):
            target = self._config.get("target_peer")
            if target:
                await self.send_test_file(target)
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            # ✅ VISUAL OUTPUT: Ready
            self._print_box(
                title="🌊 STREAM DEMO READY",
                lines=[
                    "Mode: Zero-copy byte passthrough",
                    "Usage: stream_service.send_test_file(peer_id)",
                ],
                color=self.colors.BRIGHT_CYAN if self.colors else None
            )
    
    async def stop(self, context):
        """Stop the module."""
        if self.logger:
            self.logger.log("StreamDemo stopped", tag="stream_demo")
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    async def send_test_file(self, peer_id: str) -> bool:
        """
        Send a test file to a peer using Stream Mode.
        
        Creates a test file if it doesn't exist, then streams it
        chunk by chunk to the target peer.
        """
        # Ensure test file exists
        test_path_str = self._config.get("test_file_path", "test_data.bin")
        test_path = Path(test_path_str)
        
        if not test_path.exists():
            self._create_test_file(test_path, size_mb=1)
        
        file_size = test_path.stat().st_size
        chunk_size = self._config.get("chunk_size_bytes", 8192)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        if self.logger:
            # ✅ VISUAL OUTPUT: Stream start
            self._print_box(
                title=f"🌊 STREAM START: {test_path.name}",
                lines=[
                    f"Target Peer: {peer_id}",
                    f"File Size: {self._format_bytes(file_size)}",
                    f"Chunk Size: {self._format_bytes(chunk_size)}",
                    f"Total Chunks: {total_chunks}",
                ],
                color=self.colors.BRIGHT_CYAN if self.colors else None
            )
        
        # Send header with filename and size
        header = f"FILE:{test_path.name}:{file_size}\n".encode("utf-8")
        success = await self.socket_api.send_bytes(peer_id, header)
        
        if not success:
            if self.logger:
                self.logger.log(
                    f"❌ Failed to send stream header to '{peer_id}'",
                    tag="stream_demo",
                    level="ERROR"
                )
            return False
        
        # Stream the file in chunks
        bytes_sent = 0
        chunks_sent = 0
        last_progress = 0
        
        try:
            with open(test_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    success = await self.socket_api.send_bytes(peer_id, chunk)
                    if not success:
                        if self.logger:
                            self.logger.log(
                                "❌ Failed to send stream chunk",
                                tag="stream_demo",
                                level="ERROR"
                            )
                        return False
                    
                    bytes_sent += len(chunk)
                    chunks_sent += 1
                    
                    # Progress indicator (every 10%)
                    progress = int((chunks_sent / total_chunks) * 100)
                    if progress >= last_progress + 10 and self.logger:
                        self.logger.print(
                            f"   ⏳ Progress: {progress}% ({chunks_sent}/{total_chunks} chunks, "
                            f"{self._format_bytes(bytes_sent)})",
                            tag="stream_demo",
                            text_color=self.colors.BRIGHT_CYAN if self.colors else None
                        )
                        last_progress = progress
            
            # Send end marker
            await self.socket_api.send_bytes(peer_id, b"\nEOF\n")
            
            if self.logger:
                # ✅ VISUAL OUTPUT: Stream complete
                self._print_box(
                    title=f"✅ STREAM COMPLETE: {test_path.name}",
                    lines=[
                        f"Target Peer: {peer_id}",
                        f"Bytes Sent: {self._format_bytes(bytes_sent)}",
                        f"Chunks Sent: {chunks_sent}",
                        f"Status: Success",
                    ],
                    color=self.colors.BRIGHT_GREEN if self.colors else None
                )
            
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.log(
                    f"❌ Stream failed: {e}",
                    tag="stream_demo",
                    level="ERROR"
                )
            return False
    
    def _create_test_file(self, path: Path, size_mb: int = 1):
        """Create a test file with random data."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "wb") as f:
            chunk = os.urandom(1024 * 1024)
            for _ in range(size_mb):
                f.write(chunk)
        
        if self.logger:
            self.logger.log(
                f"Created test file: {path} ({size_mb} MB)",
                tag="stream_demo"
            )
    
    # =========================================================================
    # Visual Helpers
    # =========================================================================
    
    def _print_box(
        self,
        title: str,
        lines: List[str],
        color=None,
        compact: bool = False
    ):
        """Print a visually distinct box for stream events."""
        if not self.logger:
            return
        
        width = 60
        
        if compact:
            separator = "─" * width
            self.logger.print(f"┌{separator}┐", tag="stream_demo", text_color=color)
            self.logger.print(f"│ {title:<{width-2}} │", tag="stream_demo", text_color=color)
            for line in lines:
                if len(line) > width - 4:
                    line = line[:width-7] + "..."
                self.logger.print(f"│   {line:<{width-4}} │", tag="stream_demo", text_color=color)
            self.logger.print(f"└{separator}┘", tag="stream_demo", text_color=color)
        else:
            separator = "═" * width
            self.logger.print(f"╔{separator}╗", tag="stream_demo", text_color=color)
            self.logger.print(f"║  {title:<{width-3}} ║", tag="stream_demo", text_color=color)
            self.logger.print(f"╠{separator}╣", tag="stream_demo", text_color=color)
            for line in lines:
                self.logger.print(f"║  {line:<{width-3}} ║", tag="stream_demo", text_color=color)
            self.logger.print(f"╚{separator}╝", tag="stream_demo", text_color=color)
        
        self.logger.print("", tag="stream_demo")
    
    def _format_bytes(self, size: int) -> str:
        """Format byte size to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"