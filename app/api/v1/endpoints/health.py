from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


@router.get("", summary="Sistem Sağlık Kontrolü")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Sistemin, veritabanı (NeonDB/SQLite) ve LLM (Google Gemini) bağlantı durumunu doğrular.
    """
    # 1. Veritabanı Kontrolü
    is_postgres = "postgresql" in settings.DATABASE_URL or "postgres" in settings.DATABASE_URL
    is_neondb = "neon.tech" in settings.DATABASE_URL
    if is_neondb:
        db_type = "NeonDB (Serverless PostgreSQL)"
    elif is_postgres:
        db_type = "PostgreSQL"
    else:
        db_type = "SQLite (Yerel Dosya)"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
        db_connected = True
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        db_connected = False

    # 2. LLM / Gemini Kontrolü
    from app.workflows.builders.llm_node_builder import default_llm_builder
    llm_health = default_llm_builder.check_health()

    return {
        "status": "online",
        "database": db_status,
        "database_connected": db_connected,
        "database_engine": db_type,
        "is_neondb": is_neondb,
        "llm": llm_health,
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME
    }
