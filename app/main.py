from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, close_db, AsyncSessionLocal
from app.core.exceptions import AppException, app_exception_handler
from app.api.v1.router import api_router
from app.seed.seeder import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama Yaşam Döngüsü (Lifespan):
    1. Başlangıç: Tabloları oluşturur ve boşsa seed verilerini yükler.
    2. Kapanış: Veritabanı motorunu güvenle kapatır.
    """
    await init_db()

    async with AsyncSessionLocal() as session:
        await seed_database(session, force=False)

    yield

    await close_db()


def create_application() -> FastAPI:
    """FastAPI uygulama fabrikası."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "**VisionQC API** - LangGraph Destekli Endüstriyel Kalite Kontrol ve Etiketleme Sistemi.\n\n"
            "### İş Akışı (LangGraph Workflow):\n"
            "1. **Görsel İnceleme (1. Düğüm):** Görselin endüstriyel kalite kontrol ile alakalı olup olmadığını denetler. "
            "Alakasız ise akışı kapatır ve otomatik uyarı mesajı üretir.\n"
            "2. **Kusur Değerlendirme (2. Düğüm):** Alakalı görseller için LLM ile kusur tespiti (`is_product_defect`), "
            "güven skoru (`confidence_score`) ve kusur açıklaması (`defect_description`) üretir.\n"
            "3. **Kullanıcı Onayı ile Etiketleme (Human-in-the-Loop):** Operatör, AI tahminini onaylar (`APPROVED`), "
            "düzeltir (`CORRECTED`) veya reddeder (`REJECTED`)."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS - Tüm yerel frontend geliştirme portlarına ve izinli origin'lere tam erişim
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)

    # Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Kök Dizin"], summary="API Hoşgeldiniz & Durum")
    async def root():
        return {
            "message": "VisionQC - LangGraph Kalite Kontrol ve Etiketleme API çalışıyor.",
            "version": settings.VERSION,
            "docs": "/docs",
            "api_v1": settings.API_V1_STR
        }

    @app.get("/health", tags=["Kök Dizin"], summary="Hızlı Sağlık Kontrolü")
    async def quick_health():
        return {
            "status": "ok",
            "version": settings.VERSION
        }

    return app


app = create_application()
