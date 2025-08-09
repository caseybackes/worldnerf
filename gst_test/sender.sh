#!/bin/bash
# Send test pattern from nerf container to a target host:port
# Usage: ./sender.sh <TARGET_HOST> [PORT]
TARGET=${1:-control}
PORT=${2:-5000}

echo "[GStreamer Test] Sending test pattern to ${TARGET}:${PORT}..."
gst-launch-1.0 -v videotestsrc \
    ! video/x-raw,width=640,height=480,framerate=30/1 \
    ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast \
    ! rtph264pay config-interval=1 pt=96 \
    ! udpsink host=${TARGET} port=${PORT}
