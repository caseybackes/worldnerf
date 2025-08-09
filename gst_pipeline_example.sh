#!/bin/bash
# gst_pipeline_example.sh
# Send test video stream via RTP to the NeRF container (default host=nerf in Docker network)

# Allow override via env var
NERF_HOST=${NERF_HOST:-nerf}
NERF_PORT=${NERF_PORT:-5000}

echo "Sending test RTP stream to ${NERF_HOST}:${NERF_PORT}"
echo "Play it with: ffplay -fflags nobuffer -flags low_delay -framedrop -strict experimental rtp://${NERF_HOST}:${NERF_PORT}"

gst-launch-1.0 -v \
  videotestsrc is-live=true \
  ! video/x-raw,format=I420,width=640,height=360,framerate=30/1 \
  ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast \
  ! rtph264pay \
  ! udpsink host=${NERF_HOST} port=${NERF_PORT}
