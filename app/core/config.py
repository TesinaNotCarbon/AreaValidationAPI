from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="AreaValidationAPI", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    eth_rpc_url: str = Field(alias="ETH_RPC_URL")
    project_manager_address: str = Field(alias="PROJECT_MANAGER_ADDRESS")
    project_manager_abi: str = Field(alias="PROJECT_MANAGER_ABI")

    pinata_gateway_base_url: str = Field(default="https://gateway.pinata.cloud/ipfs", alias="PINATA_GATEWAY_BASE_URL")
    pinata_jwt: str = Field(alias="PINATA_JWT")

    rpc_timeout_seconds: int = Field(default=10, alias="RPC_TIMEOUT_SECONDS")
    ipfs_timeout_seconds: int = Field(default=20, alias="IPFS_TIMEOUT_SECONDS")
    batch_timeout_seconds: int = Field(default=60, alias="BATCH_TIMEOUT_SECONDS")
    max_concurrent_downloads: int = Field(default=25, alias="MAX_CONCURRENT_DOWNLOADS")
    max_approved_cells: int = Field(default=10000, alias="MAX_APPROVED_CELLS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
