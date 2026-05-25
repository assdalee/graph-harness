import asyncio
from collections.abc import Callable

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from graph_harness.api_models.chat import (
    AgentTraceEvent,
    ChatRequest,
    ChatResponse,
    StreamDoneEvent,
    StreamErrorEvent,
    StreamResultEvent,
    StreamTraceEvent,
)
from graph_harness.app.dependencies import get_chat_service
from graph_harness.services.chat_service import ChatService


def create_chat_router(auth_dependency: Callable) -> APIRouter:
    router = APIRouter(prefix="/v1/graph", tags=["graph"], dependencies=[Depends(auth_dependency)])

    @router.post("/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        service: ChatService = Depends(get_chat_service),
    ) -> ChatResponse:
        return await service.chat(request)

    @router.post("/chat/stream")
    async def chat_stream(
        request: ChatRequest,
        service: ChatService = Depends(get_chat_service),
    ) -> StreamingResponse:
        async def events():
            queue: asyncio.Queue[AgentTraceEvent] = asyncio.Queue()

            def on_event(event: AgentTraceEvent) -> None:
                queue.put_nowait(event)

            task = asyncio.create_task(service.chat(request, on_event=on_event))
            try:
                while True:
                    getter = asyncio.ensure_future(queue.get())
                    done, _pending = await asyncio.wait(
                        {getter, task}, return_when=asyncio.FIRST_COMPLETED
                    )
                    if getter in done:
                        event = getter.result()
                        yield _sse(StreamTraceEvent(event="trace", data=event))
                        continue

                    getter.cancel()
                    # The run finished; flush any trace events still buffered.
                    while not queue.empty():
                        yield _sse(StreamTraceEvent(event="trace", data=queue.get_nowait()))
                    response = task.result()
                    yield _sse(StreamResultEvent(event="result", data=response))
                    yield _sse(StreamDoneEvent(event="done"))
                    return
            except Exception as exc:
                if not task.done():
                    task.cancel()
                yield _sse(StreamErrorEvent(event="error", detail=str(exc)))

        return StreamingResponse(events(), media_type="text/event-stream")

    return router


def _sse(model) -> str:
    return f"data: {model.model_dump_json()}\n\n"
