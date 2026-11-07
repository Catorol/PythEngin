from importlib.metadata import version as pkg_version

from fastapi import FastAPI

from research_graph.api import analytics, creators, ml, products, videos
from research_graph.api.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="TikTok Shop Viral Predictor",
        version=pkg_version("research-graph"),
        description="Сервис прогноза виральности видео TikTok Shop по признакам до публикации.",
    )
    register_error_handlers(app)
    app.include_router(creators.router)
    app.include_router(products.router)
    app.include_router(videos.router)
    app.include_router(ml.router)
    app.include_router(analytics.router)

    @app.get("/health", tags=["system"], summary="Проверка работоспособности")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
