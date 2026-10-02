from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("visionqc.database")

# Veritabanı motoru yapılandırması
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

connect_args = {}
db_url = settings.DATABASE_URL

if "postgresql" in db_url or "postgres" in db_url:
    # --- NeonDB / PostgreSQL Yapılandırması ---
    # 1. Neon Serverless compute uyuma/uyanma döngüsü için pool_pre_ping hayati önem taşır.
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

    # 2. SSL Yapılandırması:
    # DB_SSL tanımlıysa önceliklidir (True/False).
    # Tanımlı değilse NeonDB veya AWS RDS gibi bulut adreslerinde SSL "require" yapılır.
    # Yerel Postgres veya Docker konteynerlerinde SSL varsayılan olarak devre dışı bırakılır.
    ssl_enabled = False
    if settings.DB_SSL is not None:
        ssl_enabled = settings.DB_SSL
    elif any(cloud_host in db_url for cloud_host in ["neon.tech", "supabase.co", "rds.amazonaws.com"]):
        ssl_enabled = True

    if ssl_enabled:
        connect_args["ssl"] = "require"

    # 3. Neon Connection Pooler (PgBouncer) kullanılıyorsa prepared statements kapatılmalıdır.
    if "-pooler" in db_url or "pooler" in db_url:
        connect_args["prepared_statement_cache_size"] = 0

    engine_kwargs["connect_args"] = connect_args
    logger.info(f"PostgreSQL (asyncpg) bağlantı motoru yapılandırıldı (SSL: {'Aktif' if ssl_enabled else 'Devre Dışı'}).")

elif "sqlite" in db_url:
    # --- Yerel SQLite Yapılandırması ---
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
    logger.info("SQLite bağlantı motoru yapılandırıldı.")

# Asenkron Motor
engine = create_async_engine(db_url, **engine_kwargs)

# Asenkron Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Tüm SQLAlchemy ORM modelleri için temel bildirim sınıfı."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Her HTTP isteği için asenkron veritabanı oturumu sağlayan FastAPI bağımlılığı.
    Hata anında rollback yapar ve bağlantıyı güvenle havuza iade eder.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Veritabanı tablolarını otomatik oluşturur (NeonDB veya SQLite)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Uygulama kapanırken bağlantı havuzunu temizler."""
    await engine.dispose()
