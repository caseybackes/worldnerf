#!/bin/bash
# Receive RTP H264 stream on this machine
# Usage: ./receiver.sh [PORT] [MODE]
PORT=${1:-5000}
MODE=${2:-display}
DURATION_SEC=10

echo "[GStreamer Test] Receiving RTP H264 on port ${PORT} in mode: ${MODE}"

# Check if we can use a display
if [ "$MODE" = "display" ]; then
    if [ -z "$DISPLAY" ]; then
        echo "[GStreamer Test] No DISPLAY detected — switching to record mode."
        MODE="record"
    fi
fi

case $MODE in
    display)
        if ! gst-launch-1.0 -v \
            udpsrc port=${PORT} \
                caps="application/x-rtp,media=video,encoding-name=H264,payload=96" \
            ! rtph264depay \
            ! avdec_h264 \
            ! ximagesink sync=false; then
            echo "[GStreamer Test] Display failed — falling back to record mode..."
            MODE="record"
            $0 ${PORT} ${MODE}
        fi
        ;;



    record)
        DIR="captures"
        mkdir -p "$DIR"

        echo "[GStreamer Test] Cleaning old capture files..."
        rm -f "$DIR"/*.mp4

        # echo "[GStreamer Test] Pre-flight check for incoming RTP on port ${PORT}..."
        # timeout 2 gst-launch-1.0 -q \
        #     udpsrc port=${PORT} \
        #         caps="application/x-rtp,media=video,encoding-name=H264,payload=96" \
        #     ! rtph264depay ! fakesink

        # if [ $? -ne 0 ]; then
        #     echo "[GStreamer Test] No packets detected — recording aborted."
        #     exit 1
        # fi

        echo "[GStreamer Test] Recording to $DIR in 10-second segments..."
        gst-launch-1.0 -e \
            udpsrc port=${PORT} \
                caps="application/x-rtp,media=video,encoding-name=H264,payload=96" \
            ! rtph264depay \
            ! h264parse \
            ! splitmuxsink muxer=mp4mux location="$DIR/capture_%03d.mp4" max-size-time=10000000000
        ;;




    headless)
        echo "[GStreamer Test] Running in headless mode (discarding video)..."
        gst-launch-1.0 -v \
            udpsrc port=${PORT} \
                caps="application/x-rtp,media=video,encoding-name=H264,payload=96" \
            ! rtph264depay \
            ! fakesink
        ;;
    *)
        echo "Unknown mode: $MODE"
        exit 1
        ;;
esac
