#!/usr/bin/env python3
"""
stream_server.py
WebSocket control server that:
 - accepts camera-pose commands
 - renders a frame (in-process zipnerf-pytorch if available, else ns-render, else synthetic)
 - streams via GStreamer (RTP/UDP) with x264enc
 - optionally returns a JPEG frame via WebSocket (base64) for easy browser display
"""

import asyncio
import argparse
import base64
import json
import logging
import os
import subprocess
import time
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

# websocket lib
import websockets

# try import zipnerf-pytorch rendering API if installed
try:
    # NOTE: API varies by repo; adapt if needed. We'll try to import a plausible module.
    import zipnerf_pytorch as zipnerf_lib
    ZIPNERF_AVAILABLE = True
except Exception:
    ZIPNERF_AVAILABLE = False

# try GStreamer
try:
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
    Gst.init(None)
    GST_AVAILABLE = True
except Exception:
    GST_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stream_server")


class GstPusher:
    """Simple GStreamer appsrc -> x264enc -> RTP/UDP pusher."""
    def __init__(self, width, height, fps=30, udp_host="127.0.0.1", udp_port=5000):
        if not GST_AVAILABLE:
            raise RuntimeError("GStreamer Python bindings not available.")
        self.width = width
        self.height = height
        self.fps = fps
        self.udp_host = udp_host
        self.udp_port = udp_port
        encoder = "x264enc tune=zerolatency bitrate=3000 speed-preset=superfast"
        pipeline = (
            f"appsrc name=src is-live=true block=true format=time "
            f"caps=video/x-raw,format=BGR,width={width},height={height},framerate={fps}/1 "
            f"! videoconvert ! {encoder} ! rtph264pay config-interval=1 pt=96 ! udpsink host={udp_host} port={udp_port} sync=false"
        )
        logger.info("Gst pipeline: %s", pipeline)
        self.pipeline = Gst.parse_launch(pipeline)
        self.appsrc = self.pipeline.get_by_name("src")
        if self.appsrc is None:
            raise RuntimeError("failed to get appsrc")
        self.pipeline.set_state(Gst.State.PLAYING)
        logger.info("GStreamer pipeline playing")

    def push_frame(self, frame: np.ndarray):
        # expect BGR uint8 HxWx3
        assert frame.dtype == np.uint8
        data = frame.tobytes()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        timestamp = int(time.time() * 1e9)
        buf.pts = timestamp
        buf.duration = int(1e9 / self.fps)
        self.appsrc.emit("push-buffer", buf)

    def stop(self):
        try:
            self.pipeline.set_state(Gst.State.NULL)
        except Exception:
            pass


async def handle_ws(ws, path, pusher, args):
    logger.info("client connected: %s", ws.remote_address)
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send(json.dumps({"error": "invalid json"}))
                continue

            cmd = msg.get("cmd")
            if cmd == "pose":
                width = int(msg.get("frame_w", args.width))
                height = int(msg.get("frame_h", args.height))
                pose = msg.get("pose", None)
                camera = msg.get("camera", {})

                frame = render_frame(pose, camera, width, height, args)

                # push to gstreamer if configured
                if pusher:
                    pusher.push_frame(frame)

                # optionally send back JPEG over ws (base64)
                if args.send_jpeg_ws:
                    buf = BytesIO()
                    # convert BGR->RGB for PIL
                    img = Image.fromarray(frame[..., ::-1])
                    img.save(buf, format="JPEG", quality=78)
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                    await ws.send(json.dumps({"status": "ok", "jpeg_b64": b64}))
                else:
                    await ws.send(json.dumps({"status": "ok"}))

            elif cmd == "stop":
                await ws.send(json.dumps({"status": "stopping"}))
                break
            else:
                await ws.send(json.dumps({"error": "unknown command"}))
    except websockets.exceptions.ConnectionClosed:
        logger.info("client disconnected")
    except Exception:
        logger.exception("ws handler error")


def render_frame(pose, camera_params, width, height, args):
    """
    Try render via:
      1. in-process zipnerf-pytorch (if installed and model warmed)
      2. ns-render CLI (Nerfstudio) if model dir given
      3. synthetic fallback
    """
    # 1) in-process zipnerf-pytorch (prototype API usage; adapt to installed package)
    if ZIPNERF_AVAILABLE and args.use_zipnerf:
        try:
            # This is illustrative — match to the actual zipnerf-pytorch API you have.
            # Example: zipnerf_lib.render_from_checkpoint(checkpoint, pose, H, W)
            if hasattr(zipnerf_lib, "render_from_checkpoint"):
                arr = zipnerf_lib.render_from_checkpoint(args.zip_checkpoint, pose, height, width)
                # ensure uint8 BGR
                if arr.dtype != np.uint8:
                    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
                # if arr is RGB convert to BGR
                if arr.shape[2] == 3:
                    arr = arr[..., ::-1]
                return arr
            # else fallback to other API names — user must adapt
        except Exception:
            logger.exception("zipnerf in-process render failed; falling back")

    # 2) Nerfstudio CLI (ns-render) fallback
    if args.use_ns_render and os.path.isdir(args.model_dir):
        try:
            out_path = args.ns_render_tmp
            # This CLI call is illustrative; adjust to your nerfstudio version / flags.
            cmd = [
                "ns-render",
                "--load-config", args.model_dir,
                "--outfile", out_path,
                "--width", str(width),
                "--height", str(height),
            ]
            # If pose/camera require JSON file, write it and adapt flags here.
            logger.info("Calling ns-render: %s", " ".join(cmd))
            subprocess.run(cmd, check=True, timeout=30)
            # read image
            img = Image.open(out_path).convert("RGB")
            arr = np.array(img)[..., ::-1]  # BGR
            return arr
        except Exception:
            logger.exception("ns-render failed; falling back to synthetic")

    # 3) Synthetic fallback (BGR uint8)
    x = np.linspace(0, 255, width, dtype=np.uint8)
    y = np.linspace(0, 255, height, dtype=np.uint8)[:, None]
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[..., 0] = (x[None, :] % 256)  # B
    frame[..., 1] = (y % 256)[:, None]  # G
    frame[..., 2] = ((x[None, :] + y) % 256)  # R
    return frame


async def main(args):
    pusher = None
    if args.udp_host and args.udp_port and GST_AVAILABLE:
        pusher = GstPusher(args.width, args.height, args.fps, args.udp_host, args.udp_port)
    elif args.udp_host and args.udp_port and not GST_AVAILABLE:
        logger.warning("GStreamer not available; RTP/UDP disabled")

    logger.info("Starting WebSocket server on %s:%d", args.host, args.port)
    server = await websockets.serve(lambda ws, path: handle_ws(ws, path, pusher, args), args.host, args.port)
    try:
        await asyncio.Future()
    finally:
        if pusher:
            pusher.stop()
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--udp-host", default="nerf") # compose network 'nerf' 
    parser.add_argument("--udp-port", type=int, default=5000)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--send-jpeg-ws", action="store_true", help="send jpeg frames over websocket (base64)")
    parser.add_argument("--use-ns-render", action="store_true", help="use Nerfstudio CLI (ns-render) to render frames")
    parser.add_argument("--model-dir", default="/workspace/model", help="path to nerfstudio model/config for ns-render")
    parser.add_argument("--ns-render-tmp", default="/workspace/_ns_render_out.png", help="ns-render temporary output")
    parser.add_argument("--use-zipnerf", action="store_true", help="try in-process zipnerf-pytorch rendering")
    parser.add_argument("--zip-checkpoint", default="/workspace/zip_ckpt.pth", help="zipnerf checkpoint path (if applicable)")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("Interrupted")
