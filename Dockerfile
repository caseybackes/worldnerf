# Dockerfile - Nerf prototype with GStreamer + WS control (no NVENC)
FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04
#FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn-runtime

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-lc"]

# --------- System deps ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git wget curl ca-certificates \
    python3 python3-dev python3-pip python3-venv \
    ffmpeg \
    libgl1 libglib2.0-0 libsm6 libxext6 \
    pkg-config yasm nasm \
    gstreamer1.0-tools gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav \
    gir1.2-gstreamer-1.0 python3-gi python3-gi-cairo \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# --------- PyTorch (CUDA 12.1 wheels compatible with 12.8 host) ----------
RUN pip install "torch>=2.2.0" torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# --------- Nerfstudio + optional zipnerf-pytorch ----------
RUN pip install nerfstudio
# Optional: PyTorch Zip-NeRF implementation (useful for in-process rendering)
RUN pip install git+https://github.com/SuLvXiangXin/zipnerf-pytorch.git || true

# --------- Common python deps ----------
RUN pip install opencv-python-headless imageio[ffmpeg] pillow numpy websockets aiohttp tqdm

# --------- Copy runtime files ----------
WORKDIR /workspace
COPY stream_server.py /workspace/stream_server.py
COPY client.html /workspace/client.html
COPY client.js /workspace/client.js
COPY gst_pipeline_example.sh /workspace/gst_pipeline_example.sh
RUN chmod +x /workspace/gst_pipeline_example.sh

# --------- Expose ports ----------
# WebSocket control
EXPOSE 9001       
# RTP/UDP example
EXPOSE 5000/udp    

# --------- Default CMD ----------
#CMD ["./gst_pipeline_example.sh"]
CMD ["sh", "-c", "gst-launch-1.0 -v videotestsrc is-live=true ! video/x-raw,format=I420,width=640,height=360,framerate=30/1 ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay ! udpsink host=0.0.0.0 port=5000"]


# view stream locally on vlc
# ffplay -fflags nobuffer -flags low_delay -framedrop \
#    -strict experimental rtp://127.0.0.1:5000
