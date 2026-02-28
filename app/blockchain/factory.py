"""Factory to get the configured chain store (file or Abelian)."""
from config import settings
from .base import ChainStore
from .file_store import FileChainStore
from .abelian import AbelianChainStore


def get_chain_store() -> ChainStore:
    if settings.abelian_rpc_url and settings.abelian_rpc_user:
        return AbelianChainStore(
            rpc_url=settings.abelian_rpc_url,
            rpc_user=settings.abelian_rpc_user,
            rpc_pass=settings.abelian_rpc_pass,
            wallet_rpc_url=settings.abelian_wallet_rpc_url or None,
            cert_path=settings.abelian_rpc_cert_path or None,
        )
    return FileChainStore(base_dir=settings.local_chain_dir)
