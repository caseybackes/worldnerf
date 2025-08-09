FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime
ENV DEBIAN_FRONTEND=noninteractive
# Install GStreamer and Python WebSocket deps
RUN apt-get update && apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    python3-pip supervisor && \
    pip install websockets && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy app files
COPY ws_server.py /workspace/ws_server.py
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 9001
EXPOSE 5000/udp

# Start both services
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
