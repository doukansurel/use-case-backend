from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.seed.seeder import seed_database

router = APIRouter()


@router.post("", summary="Örnek Verileri Yükle (Seed Data)")
async def run_seed(
    force: bool = Query(False, description="Mevcut verileri temizleyip sıfırdan oluştur"),
    db: AsyncSession = Depends(get_db)
):
    """
    Demo / Use-Case için gerçekçi istasyonlar, denetimler ve kusur verileri oluşturur.
    """
    return await seed_database(db, force=force)
