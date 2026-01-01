from typing import TextIO, List

from models.rdf_builder.writers.prefixes import TURTLE_PREFIXES


class TurtleWriter:
    """Buffered Turtle writer for efficient output"""

    def __init__(self, output: TextIO, buffer_size: int = 8192):
        self.output = output
        self.buffer_size = buffer_size
        self._buffer: List[str] = []
        self._buffer_len = 0

    def write_header(self) -> None:
        self._write(TURTLE_PREFIXES)

    def write(self, text: str) -> None:
        self._buffer.append(text)
        self._buffer_len += len(text)

        if self._buffer_len >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        if self._buffer:
            self.output.write("".join(self._buffer))
            self._buffer = []
            self._buffer_len = 0
            self.output.flush()

    def _write(self, text: str) -> None:
        self.output.write(text)
