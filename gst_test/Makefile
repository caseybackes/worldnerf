# GStreamer test streaming
HOST ?= $(shell hostname -I | awk '{print $$1}')
PORT ?= 5000
MODE ?= display 
send:
	docker exec -it nerf ./gst_test/sender.sh $(HOST) $(PORT)

recv:
	./receiver.sh $(PORT) $(MODE)

help:
	@echo "make send PORT=<port>             # Send test video to host"
	@echo "make recv PORT=<port> MODE=record  # Receive/record video locally"
