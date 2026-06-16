from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    greennode_api_key: str
    greennode_api_url: str = "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1/chat/completions"
    greennode_base_url: str = "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
    greennode_model: str = "qwen/qwen3-5-27b"
    greennode_fallback_model: str = "gemma/gemma-4-31b-it"
    sprout_customer_id: str = "2416203"
    airtable_token: str
    airtable_base_id: str
    airtable_table_name: str = "Content Planning"
    teams_webhook_url: str = ""
    zalo_webhook_url: str = ""
    app_env: str = "production"
    log_level: str = "INFO"


settings = Settings()
