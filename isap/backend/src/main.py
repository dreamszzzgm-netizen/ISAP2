import hmac

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.settings import settings
from src.api.routers import organizations, facilities, equipment, substances, persons, regulatory, pmla, corpus, pmla_samples, pmla_stream, scenario_matrix, facility_types, opo

app = FastAPI(
    title="Industrial Safety AI Platform",
    description="Платформа автоматизации промышленной безопасности",
    version="0.1.0",
)

# CORS для React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# API Key auth middleware
class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропускаем preflight OPTIONS — CORS обработает
        if request.method == "OPTIONS":
            return await call_next(request)

        # Пропускаем endpoints без авторизации
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        # Если ключ не настроен — auth отключена (dev mode)
        if not settings.api_key:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Требуется авторизация"})

        token = auth_header[7:]
        if not hmac.compare_digest(token, settings.api_key):
            return JSONResponse(status_code=401, content={"detail": "Неверный ключ доступа"})

        return await call_next(request)


app.add_middleware(ApiKeyMiddleware)

# Роутеры
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(opo.router, prefix="/api/v1/facilities", tags=["opo-details"])
app.include_router(facilities.router, prefix="/api/v1/facilities", tags=["facilities"])
app.include_router(equipment.router, prefix="/api/v1/equipment", tags=["equipment"])
app.include_router(substances.router, prefix="/api/v1/substances", tags=["substances"])
app.include_router(persons.router, prefix="/api/v1/persons", tags=["persons"])
app.include_router(regulatory.router, prefix="/api/v1/regulatory", tags=["regulatory"])
app.include_router(pmla.router, prefix="/api/v1/pmla", tags=["pmla"])
app.include_router(pmla_stream.router, prefix="/api/v1/pmla", tags=["pmla-stream"])
app.include_router(corpus.router, prefix="/api/v1/corpus", tags=["corpus"])
app.include_router(pmla_samples.router, prefix="/api/v1/pmla-samples", tags=["pmla-samples"])
app.include_router(scenario_matrix.router, prefix="/api/v1/scenarios", tags=["scenarios"])
app.include_router(facility_types.router, prefix="/api/v1/facility-types", tags=["facility-types"])


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
