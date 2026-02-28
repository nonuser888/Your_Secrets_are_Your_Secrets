"""
Abelian blockchain store.
Stores encrypted summary payloads in transaction data outputs (OP_RETURN-style).
Requires Abelian node (abec) and wallet (abewallet) or equivalent RPC.
"""
import httpx
from .base import BlockRecord, ChainStore


class AbelianChainStore(ChainStore):
    """
    Store blocks via Abelian JSON-RPC.
    Uses wallet RPC to create transactions with data output (hex payload).
    """

    def __init__(
        self,
        rpc_url: str,
        rpc_user: str,
        rpc_pass: str,
        wallet_rpc_url: str | None = None,
        cert_path: str | None = None,
    ):
        self.rpc_url = rpc_url.rstrip("/")
        self.wallet_url = (wallet_rpc_url or rpc_url).rstrip("/")
        self.auth = (rpc_user, rpc_pass)
        self.cert_path = cert_path

    def _request(self, url: str, method: str, params: list | None = None) -> dict:
        payload = {"jsonrpc": "1.0", "id": "yourSecret", "method": method, "params": params or []}
        verify = self.cert_path if self.cert_path else True
        with httpx.Client(verify=verify, timeout=30.0) as client:
            r = client.post(url, json=payload, auth=self.auth)
            r.raise_for_status()
            data = r.json()
        if "error" in data and data["error"] is not None:
            raise RuntimeError(f"RPC error: {data['error']}")
        return data.get("result")

    def store_block(self, user_id: str, sequence: int, payload_hex: str) -> BlockRecord:
        """
        Store payload in a transaction data output.
        Abelian/abec may support createrawtransaction with {"data": hex} output;
        then sign with wallet and send. Here we call the wallet RPC if available.
        """
        # Try wallet method to create and send a transaction with data
        # Common pattern: createrawtransaction [] [{"data": payload_hex}]
        try:
            result = self._request(
                self.wallet_url,
                "createrawtransaction",
                [[], [{"data": payload_hex}]],
            )
        except Exception as e:
            raise RuntimeError(
                "Abelian wallet RPC (createrawtransaction with data output) failed. "
                "Ensure abewallet is running and supports data outputs. "
                f"Error: {e}"
            ) from e
        raw_tx = result if isinstance(result, str) else result.get("hex")
        if not raw_tx:
            raise RuntimeError("createrawtransaction did not return hex")
        # Sign and send (wallet-specific methods)
        signed = self._request(self.wallet_url, "signrawtransaction", [raw_tx])
        hex_signed = signed.get("hex") if isinstance(signed, dict) else signed
        if not hex_signed:
            raise RuntimeError("signrawtransaction did not return hex")
        tx_id = self._request(self.wallet_url, "sendrawtransaction", [hex_signed])
        block_id = tx_id if isinstance(tx_id, str) else tx_id.get("txid", str(tx_id))
        return BlockRecord(
            block_id=block_id,
            sequence=sequence,
            payload_hex=payload_hex,
            created_at=None,
        )

    def get_blocks(self, user_id: str) -> list[BlockRecord]:
        """
        Retrieve blocks for user. Requires indexing: Abelian does not index by user_id.
        Options: (1) Store block_id list in a separate "index" transaction or
        (2) Use a deterministic address per user and scan transactions.
        For now we use getblockcount + scan (not implemented here without index).
        """
        # Without an index on-chain, we cannot list "all blocks for user_id".
        # In production you would either:
        # - Store an index block that contains list of tx hashes per user, or
        # - Use a tagged output (e.g. first block contains user_id + next tx hash).
        # Return empty; caller can pass known block_ids if you maintain index elsewhere.
        return []

    def get_latest_sequence(self, user_id: str) -> int:
        return -1

    def get_block_by_id(self, block_id: str) -> BlockRecord | None:
        """Fetch transaction by hash and extract data output (hex)."""
        try:
            tx = self._request(self.rpc_url, "getrawtransaction", [block_id, 1])
            if not tx or not isinstance(tx, dict):
                return None
            vout = tx.get("vout") or []
            for out in vout:
                script = out.get("scriptPubKey") or {}
                if script.get("type") == "nulldata" or "hex" in script:
                    data_hex = script.get("hex") or ""
                    if data_hex:
                        return BlockRecord(
                            block_id=block_id,
                            sequence=-1,
                            payload_hex=data_hex,
                            created_at=str(tx.get("time", "")),
                        )
            return None
        except Exception:
            return None
