from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """运行配置，均可用 RDMS_ 前缀环境变量覆盖。"""
    database_url: str = "sqlite:///./rdms.db"
    data_dir: str = "./data"
    jwt_secret: str = "dev-secret-change-me"
    token_expire_hours: int = 24
    chunk_size: int = 5 * 1024 * 1024

    model_config = {"env_prefix": "RDMS_"}


settings = Settings()
