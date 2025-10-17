import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

APP_ENV = os.getenv("APP_ENV", "production").lower()
base_dir = Path(__file__).resolve().parents[2]          # raiz do projeto

env_file = ".env.test" if APP_ENV == "test" else ".env"
load_dotenv(dotenv_path=base_dir / env_file)

class Settings:
    """
    Configurações da aplicação
    """
    # ---------- Metadados da API ----------
    API_TITLE: str = "NFSe API Headless"
    API_DESCRIPTION: str = "API para emissão de NFSe em segundo plano usando web scraping headless"
    API_VERSION: str = "1.0.0"

    # ---------- Servidor ----------
    HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PY_PORT", "8000"))
    DEBUG: bool = os.getenv("APP_DEBUG", "False").lower() == "true"

    # ---------- Banco de dados ----------
    DB_CONNECTION: str = os.getenv("DB_CONNECTION", "sqlite").lower()
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_DATABASE: str = os.getenv("DB_DATABASE", "database/database.sqlite")
    DB_USERNAME: str = os.getenv("DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))

    # ---------- Playwright ----------
    PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "True").lower() == "true"
    PLAYWRIGHT_TIMEOUT: int = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))

    # ---------- Diretórios ----------
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "downloads")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    # ---------- Helper ----------
    @classmethod
    def get_database_url(cls):
        base_dir = Path(__file__).resolve().parents[2]  # Vai para pasta Root do Projeto
        
        # Se a conexão for sqlite, montar o caminho absoluto, incluindo a subpasta database
        if cls.DB_CONNECTION == "sqlite":
            # O valor de cls.DB_DATABASE deve ser "database/database.sqlite" no .env
            sqlite_path = (base_dir / cls.DB_DATABASE).resolve()
            return f"sqlite:///{sqlite_path.as_posix()}"

        # MySQL / MariaDB
        if cls.DB_CONNECTION in {"mysql", "mariadb"}:
            return (f"mysql+mysqlconnector://{cls.DB_USERNAME}:{cls.DB_PASSWORD}"
                    f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_DATABASE}")

        # PostgreSQL
        if cls.DB_CONNECTION in {"pgsql", "postgres", "postgresql"}:
            return (f"postgresql+psycopg2://{cls.DB_USERNAME}:{cls.DB_PASSWORD}"
                    f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_DATABASE}")

        raise ValueError(f"DB_CONNECTION '{cls.DB_CONNECTION}' não suportado")


# Instância global
settings = Settings()

if __name__ == "__main__": # TESTE
    print(settings.get_database_url())