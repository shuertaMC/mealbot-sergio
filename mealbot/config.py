from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    port: int = 8080
    database_url: str = ""

    mailgun_smtp_login: str = ""
    mailgun_domain: str = ""
    mailgun_api_key: str = ""

    auth0_domain: str = "mealbot.auth0.com"
    auth0_audience: str = "https://mealbot-2.herokuapp.com/"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
