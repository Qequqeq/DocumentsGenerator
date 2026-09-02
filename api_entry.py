from contextlib import asynccontextmanager
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from routes import pages
from src.logger import logger, log_error
import webview


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Сервер запущен")
    yield
    logger.info("Сервер остановлен")

app = FastAPI()
app.include_router(pages.router)
templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def error_logging_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        log_error("GLOBAL", e, {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown"
        })
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Внутренняя ошибка сервера. Подробности в логах.",
                "error_type": type(e).__name__
            }
        )