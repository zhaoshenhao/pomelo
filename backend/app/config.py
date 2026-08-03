from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_PORT: int = 8000
    APP_ENV: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "pomelo"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    SESSION_TTL: int = 604800

    CORS_ORIGINS: str = "http://localhost:3000"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"

    DOCS_ROOT: str = "../../storage"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"
    DEEPSEEK_TIMEOUT: int = 300
    DEEPSEEK_CONNECT_TIMEOUT: int = 5
    GRAMMAR_REWRITE_PROMPT: str = (
        "请修正下列文本中的错别字和语法不通顺的地方，"
        "保持原意和Markdown格式（包括标题、列表、表格、代码块等）不变。"
        "只修正语言错误，不要改变内容结构或风格。"
        "只输出修正后的文本，不要添加任何说明。"
    )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
