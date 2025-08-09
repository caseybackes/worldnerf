# NeRFStudio + GStreamer WebSocket Rendering

This setup runs a NeRFStudio instance inside Docker with WebSocket control and GStreamer streaming for rendered frames.

## Features
- **NeRFStudio** for scene rendering
- **WebSocket API** for low-latency control (fly-around commands, camera position updates)
- **GStreamer** pipeline for streaming rendered frames (without requiring NVENC)
- CPU and GPU rendering modes
- Web UI client for quick testing

## Prerequisites
- Docker with NVIDIA Container Toolkit installed
- NVIDIA GPU + Drivers (CUDA-compatible)
- Python 3.10+ for local client scripts
- GStreamer installed locally for viewing streams (optional)

## Build the Docker Image
```bash
docker build -t nerfstudio-streaming .
```

## Run the Container
```bash
docker run -it --gpus all --rm   -p 8080:8080 \
  -p 8554:8554 \
  -v $(pwd)/data:/app/data   nerfstudio-streaming
```

## WebSocket API
The container runs a WebSocket server on port **8080**.

### Example Command (Python)
```python
import asyncio
import websockets
import json

async def send_command():
    async with websockets.connect("ws://localhost:8080") as ws:
        cmd = {
            "action": "render_frame",
            "camera": {
                "position": [0, 0, -5],
                "look_at": [0, 0, 0]
            }
        }
        await ws.send(json.dumps(cmd))
        response = await ws.recv()
        print("Response:", response)

asyncio.run(send_command())
```

### Actions
- `render_frame` → Renders one frame from the given camera position.
- `fly_to` → Moves camera to new position over time.

## Streaming with GStreamer
Inside the container, GStreamer sends rendered frames to RTSP:

**View with VLC:**
```bash
vlc rtsp://localhost:8554/stream
```

**View with GStreamer locally:**
```bash
gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/stream latency=0 ! decodebin ! autovideosink
```

## Data Folder
Place training data (images/video) into `./data` before running.

## Stopping the Server
CTRL+C in the container terminal or:
```bash
docker stop <container_id>
```


```bash
docker build -t worldnerf:latest . 

docker run --gpus all -it --rm \
  -p 9001:9001 \
  -p 5000:5000/udp \
  -v $(pwd):/workspace \
  worldnerf:latest /bin/bash
```

Inside the container (start server using ns-render fallback + WS JPEG):
> ensure you have a trained nerfstudio model at /workspace/model (or set --model-dir)
```bash
python3 /workspace/stream_server.py \
--port 9001 --udp-host 127.0.0.1 \
--udp-port 5000 --width 640 --height 480 \
--send-jpeg-ws --use-ns-render
```


### Browser:

Open /workspace/client.html in a browser that can reach your container (for local dev, http://localhost:… with a simple static file server or open the file directly).

Click Connect and Send Test Pose.

### NVENC (optional):

Download NVIDIA Video Codec SDK from NVIDIA developer site and place its files in NVSDK_DIR (e.g., /workspace/NVSDK) — you must accept the SDK license.

Rebuild Docker with --build-arg NVSDK_DIR=/path/to/NVSDK/on/host and uncomment build block in Dockerfile (or mount it and modify Dockerfile as needed).

Ensure GStreamer or FFmpeg in the container exposes nvh264enc (for GStreamer) or h264_nvenc (for FFmpeg). You may instead use FFmpeg from host if container build is hard.

### Low-latency path (future change):

Replace CLI ns-render with an in-process renderer (Instant-NGP/Zip-NeRF bindings) to render directly into memory then encode via NVENC-FFmpeg/GStreamer without file I/O.


### Exammple Gstreamer software encoding pipeline
```bash
gst-launch-1.0 appsrc ! videoconvert ! x264enc \
tune=zerolatency bitrate=2000 \
speed-preset=superfast \
! video/x-h264,profile=baseline \
! h264parse ! mpegtsmux \
! tcpserversink host=0.0.0.0 port=9000
```
