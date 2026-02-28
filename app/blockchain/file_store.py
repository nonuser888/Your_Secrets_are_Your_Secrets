"""
File-based chain store (simulated blockchain).
Use when Abelian node is not configured; data is stored under LOCAL_CHAIN_DIR per user.
"""
import json
import os
from pathlib import Path
from .base import BlockRecord, ChainStore


class FileChainStore(ChainStore):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: str) -> Path:
        # Sanitize user_id for filesystem
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.base_dir / safe

    def _index_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "index.json"

    def _load_index(self, user_id: str) -> list[dict]:
        path = self._index_path(user_id)
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)

    def _save_index(self, user_id: str, index: list[dict]) -> None:
        self._user_dir(user_id).mkdir(parents=True, exist_ok=True)
        with open(self._index_path(user_id), "w") as f:
            json.dump(index, f, indent=2)

    def store_block(self, user_id: str, sequence: int, payload_hex: str) -> BlockRecord:
        user_dir = self._user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        block_id = f"local_{user_id}_{sequence}"
        block_file = user_dir / f"{sequence}.bin"
        block_file.write_bytes(bytes.fromhex(payload_hex))
        record = BlockRecord(
            block_id=block_id,
            sequence=sequence,
            payload_hex=payload_hex,
            created_at=None,
        )
        index = self._load_index(user_id)
        index.append({
            "block_id": record.block_id,
            "sequence": record.sequence,
            "created_at": record.created_at,
        })
        index.sort(key=lambda x: x["sequence"])
        self._save_index(user_id, index)
        return record

    def get_blocks(self, user_id: str) -> list[BlockRecord]:
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return []
        index = self._load_index(user_id)
        out = []
        for entry in sorted(index, key=lambda x: x["sequence"]):
            seq = entry["sequence"]
            block_file = user_dir / f"{seq}.bin"
            if block_file.exists():
                payload_hex = block_file.read_bytes().hex()
                out.append(BlockRecord(
                    block_id=entry["block_id"],
                    sequence=seq,
                    payload_hex=payload_hex,
                    created_at=entry.get("created_at"),
                ))
        return out

    def get_latest_sequence(self, user_id: str) -> int:
        index = self._load_index(user_id)
        if not index:
            return -1
        return max(e["sequence"] for e in index)
