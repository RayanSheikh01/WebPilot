from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field(..., env="TAVILY_API_KEY")
    webpilot_model: str = Field("claude-sonnet-4-6", env="WEBPILOT_MODEL")
    webpilot_max_seconds: int = Field(300, env="WEBPILOT_MAX_SECONDS")
    webpilot_max_tool_calls: int = Field(40, env="WEBPILOT_MAX_TOOL_CALLS")
    webpilot_max_pages: int = Field(10, env="WEBPILOT_MAX_PAGES")
    webpilot_max_input_tokens: int = Field(200000, env="WEBPILOT_MAX_INPUT_TOKENS")
    webpilot_max_output_tokens: int = Field(20000, env="WEBPILOT_MAX_OUTPUT_TOKENS")
    webpilot_headless: bool = Field(True, env="WEBPILOT_HEADLESS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings():
    return Settings()