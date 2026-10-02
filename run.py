import sys
import argparse
import asyncio
import uvicorn
from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.seed.seeder import seed_database


async def cli_seed(force: bool = False):
    print("Veritabanı tabloları kontrol ediliyor...")
    await init_db()
    async with AsyncSessionLocal() as session:
        print(f"Seed verisi yükleniyor (force={force})...")
        res = await seed_database(session, force=force)
        print("Sonuç:", res)


def main():
    parser = argparse.ArgumentParser(description="VisionQC Backend Runner")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Sunucu host adresi")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Sunucu port numarası")
    parser.add_argument("--seed", action="store_true", help="Demo verilerini yükle")
    parser.add_argument("--force-seed", action="store_true", help="Mevcut verileri silip sıfırdan demo verisi oluştur")
    parser.add_argument("--no-reload", action="store_true", help="Uvicorn auto-reload özelliğini kapat")

    args = parser.parse_args()

    if args.seed or args.force_seed:
        asyncio.run(cli_seed(force=args.force_seed))
    else:
        print(f"🚀 {settings.PROJECT_NAME} başlatılıyor...")
        print(f"📡 Adres: http://{args.host}:{args.port}")
        print(f"📚 Swagger UI: http://localhost:{args.port}/docs")
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=settings.DEBUG and not args.no_reload
        )


if __name__ == "__main__":
    main()
