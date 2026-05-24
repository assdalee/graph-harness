import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from graph_harness.agent.agent import GraphAgent
from graph_harness.app.routes.chat import create_chat_router
from graph_harness.app.routes.health import create_health_router
from graph_harness.app.routes.operations import create_operations_router
from graph_harness.app.routes.runs import create_runs_router
from graph_harness.runs.store import build_run_store
from graph_harness.core.config import Settings, get_settings
from graph_harness.core.errors import AppError
from graph_harness.core.logging import configure_logging, set_request_id
from graph_harness.core.security import build_api_key_dependency
from graph_harness.graph.auth import GraphTokenProvider
from graph_harness.graph.client import GraphClient
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.client import LiteLLMClient
from graph_harness.llm.fake_client import FakeLLMClient
from graph_harness.services.chat_service import ChatService
from graph_harness.services.operations_service import OperationsService
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        client = getattr(app.state, "graph_client", None)
        if client is not None and hasattr(client, "aclose"):
            await client.aclose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Production-oriented AI agent harness for Microsoft Graph.",
        lifespan=lifespan,
    )
    allow_origins = settings.cors_allow_origins or ["*"]
    # The CORS spec forbids credentialed requests against a wildcard origin, and
    # browsers reject the combination. Only enable credentials for explicit origins.
    allow_credentials = settings.cors_allow_credentials and "*" not in allow_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    max_request_bytes = settings.max_request_bytes

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        set_request_id(request_id)

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = 0
            if declared > max_request_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Request body too large.",
                        "code": "request_too_large",
                        "details": {"max_request_bytes": max_request_bytes},
                    },
                    headers={"x-request-id": request_id},
                )

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    catalog = GraphOperationCatalog.default()
    if settings.graph_backend.lower() == "mock":
        graph_client = MockGraphClient()
    else:
        token_provider = GraphTokenProvider(settings)
        graph_client = GraphClient(settings, token_provider)
    registry = GraphToolFactory(graph_client, catalog).build_registry()
    executor = ToolExecutor(registry, settings)
    llm_client = (
        FakeLLMClient(settings)
        if settings.llm_backend.lower() == "fake"
        else LiteLLMClient(settings)
    )
    agent = GraphAgent(
        llm_client=llm_client,
        registry=registry,
        executor=executor,
        settings=settings,
    )

    run_store = build_run_store(settings)

    app.state.settings = settings
    app.state.graph_client = graph_client
    app.state.graph_operation_catalog = catalog
    app.state.tool_registry = registry
    app.state.run_store = run_store
    app.state.chat_service = ChatService(agent, run_store=run_store, settings=settings)
    app.state.operations_service = OperationsService(registry)

    auth_dependency = build_api_key_dependency(settings)
    app.include_router(create_health_router(settings.app_name))
    app.include_router(create_operations_router(auth_dependency))
    app.include_router(create_chat_router(auth_dependency))
    app.include_router(create_runs_router(auth_dependency))

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code, "details": exc.details},
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app


app = create_app()
