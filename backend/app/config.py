from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_PORT: int = 8080
    APP_ENV: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "pomelo"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

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
    DEEPSEEK_TIMEOUT: int = 900
    DEEPSEEK_CONNECT_TIMEOUT: int = 5

    AI_MAX_TOKENS: int = 16384
    AI_QB_MAX_TOKENS: int = 256000
    AI_DOC_MAX_CHARS: int = 5000
    AI_TOTAL_MAX_CHARS: int = 40000
    AI_TEMPERATURE: float = 0.7

    PROMPTS_FILE: str = "config/prompts.yaml"

    TTS_DEFAULT_VOICE: str = "zh-CN-XiaoxiaoNeural"
    TTS_AVAILABLE_VOICES: str = "zh-CN-XiaoxiaoNeural,zh-CN-YunxiNeural,zh-CN-YunjianNeural,zh-CN-XiaoyiNeural,zh-CN-YunyangNeural"
    TTS_FALLBACK_CHARS_PER_SEC: float = 4.5

    READING_SPEED_CHARS_PER_MIN: int = 200

    REGISTRATION_ENABLED: bool = True

    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET: str = ""
    OSS_ENDPOINT_INTERNAL: str = "oss-cn-shanghai-internal.aliyuncs.com"
    OSS_ENDPOINT_PUBLIC: str = "oss-cn-shanghai.aliyuncs.com"
    OSS_VIDEO_PREFIX: str = "videos/"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
