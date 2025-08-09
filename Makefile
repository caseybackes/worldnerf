# GStreamer test streaming
HOST ?= control
PORT ?= 5000

send:
	docker exec -it nerf ./gst_test/sender.sh $(HOST) $(PORT)

recv:
	./gst_test/receiver.sh $(PORT)

help:
	@echo "make send HOST=<host> PORT=<port>  # Send test video from nerf"
	@echo "make recv PORT=<port>               # Receive video locally"


