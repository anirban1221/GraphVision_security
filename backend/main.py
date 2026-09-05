import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config import HOST, PORT
from backend.stream_engine import StreamEngine

# Global streaming engine instance
engine = StreamEngine()

# Active WebSocket connections
active_connections: list[WebSocket] = []

# Background streaming loop
async def stream_broadcaster():
    print("[Main] Streaming broadcaster loop initiated.")
    while True:
        try:
            if engine.is_playing and active_connections:
                event = engine.step()
                if event:
                    message = json.dumps(event)
                    # Broadcast to all connected clients
                    disconnected = []
                    for conn in active_connections:
                        try:
                            await conn.send_text(message)
                        except Exception:
                            disconnected.append(conn)
                    for d in disconnected:
                        if d in active_connections:
                            active_connections.remove(d)
                else:
                    engine.is_playing = False

                # Dynamic delay based on speed (transactions per second)
                delay = max(0.01, 1.0 / max(0.5, engine.speed))
                await asyncio.sleep(delay)
            else:
                await asyncio.sleep(0.05)
        except Exception as e:
            print(f"[Main] Error in stream_broadcaster: {e}")
            await asyncio.sleep(0.2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Pre-load dataset
    try:
        engine.load_data(nrows=25000)
    except Exception as e:
        print(f"[Main] Warning: Could not pre-load dataset: {e}")

    # 2. Launch background broadcaster inside the running event loop
    broadcaster_task = asyncio.create_task(stream_broadcaster())
    print("[Main] Stream broadcaster background task launched!")

    yield

    # 3. Shutdown
    engine.is_playing = False
    broadcaster_task.cancel()

app = FastAPI(title="GraphVision Security", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Endpoint ---
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"[WebSocket] Client connected. Total clients: {len(active_connections)}")

    # 1. Send Initial State & Existing Graph Snapshot
    init_msg = {
        "type": "INIT_STATE",
        "active_rings": engine.graph_engine.get_active_rings(),
        "attack_profile": None,
        "timeline": engine.sliding_window.get_timeline(),
        "stats": engine.get_status()
    }
    await websocket.send_text(json.dumps(init_msg))

    try:
        while True:
            data_text = await websocket.receive_text()
            cmd = json.loads(data_text)
            action = cmd.get("command")

            if action == "play":
                engine.is_playing = True
                print("[WebSocket] Stream PLAY activated.")
            elif action == "pause":
                engine.is_playing = False
                print("[WebSocket] Stream PAUSED.")
            elif action == "step":
                event = engine.step()
                if event:
                    await websocket.send_text(json.dumps(event))
            elif action == "set_speed":
                engine.speed = float(cmd.get("speed", 5.0))
            elif action == "set_window":
                window_5m = int(cmd.get("window_5m", 300))
                engine.sliding_window.set_window_spans(window_5m, window_5m * 6, 86400)
            elif action == "jump_to_spike":
                # Trigger instant attack profile and step forward
                attack_prof = engine.graph_engine.trigger_peak_attack()
                ev = engine.step()
                if ev:
                    ev["attack_profile"] = attack_prof
                    await websocket.send_text(json.dumps(ev))
            elif action == "reset":
                engine.reset()
                reset_msg = {
                    "type": "RESET_STATE",
                    "attack_profile": None,
                    "stats": engine.get_status()
                }
                await websocket.send_text(json.dumps(reset_msg))

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print(f"[WebSocket] Client disconnected. Remaining: {len(active_connections)}")

# --- REST Endpoints ---
@app.get("/api/status")
def get_status():
    return engine.get_status()

@app.get("/api/attack")
def get_attack():
    return engine.graph_engine.active_attack

@app.get("/api/timeline")
def get_timeline():
    return engine.sliding_window.get_timeline()

# --- Serve Static UI ---
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "Backend running. Place index.html into backend/static/"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
