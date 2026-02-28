"""Abstract blockchain store for encrypted chat summary blocks."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence


@dataclass
class BlockRecord:
    """A single block of encrypted summary data stored on chain."""
    block_id: str  # tx hash or local id
    sequence: int  # order of this block for the user
    payload_hex: str  # encrypted summary (hex)
    created_at: str | None = None  # optional timestamp


class ChainStore(ABC):
    """Store and retrieve encrypted blocks (e.g. on Abelian blockchain)."""

    @abstractmethod
    def store_block(self, user_id: str, sequence: int, payload_hex: str) -> BlockRecord:
        """Store one block of encrypted data. Returns the created record."""
        ...

    @abstractmethod
    def get_blocks(self, user_id: str) -> Sequence[BlockRecord]:
        """Return all blocks for user, ordered by sequence ascending."""
        ...

    @abstractmethod
    def get_latest_sequence(self, user_id: str) -> int:
        """Return the highest sequence number for user, or -1 if none."""
        ...

    def get_block_by_id(self, block_id: str) -> BlockRecord | None:
        """Optional: fetch a single block by id (e.g. tx hash). Default: not supported."""
        return None
