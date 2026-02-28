"""Application configuration from environment."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    # Abelian blockchain
    abelian_rpc_url: str = Field("", env="ABELIAN_RPC_URL")
    abelian_rpc_user: str = Field("", env="ABELIAN_RPC_USER")
    abelian_rpc_pass: str = Field("", env="ABELIAN_RPC_PASS")
    abelian_wallet_rpc_url: str = Field("", env="ABELIAN_WALLET_RPC_URL")
    abelian_rpc_cert_path: str = Field("", env="ABELIAN_RPC_CERT_PATH")
    # Local storage (when Abelian not configured)
    local_chain_dir: str = Field("./data/chain", env="LOCAL_CHAIN_DIR")
    secret_key: str = Field("dev-secret-key-change-in-production", env="SECRET_KEY")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
