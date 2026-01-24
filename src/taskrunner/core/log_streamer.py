"""
Log Streamer - Tail -f per file di log.
"""

import time
from pathlib import Path
from typing import Generator, List, Optional
from threading import Event
import os


class LogStreamer:
    """Streaming tail -f per file di log."""

    def __init__(self, log_path: Path, poll_interval: float = 0.1):
        self.log_path = Path(log_path)
        self.poll_interval = poll_interval
        self._stop_event = Event()

    def stream(self, from_line: int = 0) -> Generator[str, None, None]:
        """
        Generator che yielda nuove righe dal file.

        Args:
            from_line: Numero di riga da cui iniziare (0 = inizio)

        Yields:
            Righe di testo senza newline finale
        """
        if not self.log_path.exists():
            return

        with open(self.log_path, 'r', encoding='utf-8') as f:
            # Skip to from_line
            for _ in range(from_line):
                if not f.readline():
                    break

            # Stream new content
            while not self._stop_event.is_set():
                line = f.readline()
                if line:
                    yield line.rstrip()
                else:
                    # No new content, wait
                    time.sleep(self.poll_interval)

    def stop(self):
        """Ferma lo streaming."""
        self._stop_event.set()

    def reset(self):
        """Resetta lo stop event per riutilizzo."""
        self._stop_event.clear()

    @staticmethod
    def tail(log_path: Path, lines: int = 100) -> List[str]:
        """
        Legge le ultime N righe da un file di log.

        Args:
            log_path: Path del file
            lines: Numero di righe da leggere

        Returns:
            Lista delle ultime N righe
        """
        if not log_path.exists():
            return []

        try:
            # Implementazione efficiente per file grandi
            with open(log_path, 'rb') as f:
                # Vai alla fine
                f.seek(0, 2)
                file_size = f.tell()

                if file_size == 0:
                    return []

                # Buffer per leggere a blocchi
                block_size = 8192
                blocks = []
                lines_found = 0
                position = file_size

                while position > 0 and lines_found < lines + 1:
                    # Calcola quanto leggere
                    read_size = min(block_size, position)
                    position -= read_size
                    f.seek(position)
                    block = f.read(read_size)
                    blocks.insert(0, block)
                    lines_found += block.count(b'\n')

                # Unisci e splitta
                content = b''.join(blocks).decode('utf-8', errors='replace')
                all_lines = content.splitlines()

                # Ritorna ultime N
                return all_lines[-lines:] if len(all_lines) > lines else all_lines

        except Exception:
            return []

    @staticmethod
    def get_line_count(log_path: Path) -> int:
        """Conta le righe in un file."""
        if not log_path.exists():
            return 0
        try:
            with open(log_path, 'rb') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
