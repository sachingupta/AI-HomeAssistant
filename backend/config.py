from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8080/oauth/callback"
    google_refresh_token: str = ""
    drive_folder_id: str = ""
    google_sheet_id: str = ""          # Used when DATA_STORE=sheets
    data_store: str = "sheets"         # "sheets" | "drive" | "mcp"
    family_name: str = "Our Family"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
