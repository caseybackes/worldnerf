let ws = null;
const img = document.getElementById('video');
const btnConnect = document.getElementById('btnConnect');
const btnPose = document.getElementById('btnPose');
const inpW = document.getElementById('w');
const inpH = document.getElementById('h');
const chk = document.getElementById('jpeg');

btnConnect.onclick = () => {
  if (ws && ws.readyState === WebSocket.OPEN) { ws.close(); return; }
  ws = new WebSocket("ws://localhost:9001/");
  ws.onopen = () => { btnConnect.textContent = "Disconnect"; console.log("connected"); };
  ws.onclose = () => { btnConnect.textContent = "Connect"; console.log("closed"); };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.jpeg_b64) {
        img.src = "data:image/jpeg;base64," + msg.jpeg_b64;
      } else {
        console.log("server:", msg);
      }
    } catch(e) {
      console.warn("non-json or large payload", e);
    }
  };
};

btnPose.onclick = () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) { alert("connect first"); return; }
  const w = parseInt(inpW.value||640);
  const h = parseInt(inpH.value||480);
  const pose = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]; // identity
  const msg = { cmd: "pose", pose: pose, camera: {fov:60}, frame_w: w, frame_h: h };
  ws.send(JSON.stringify(msg));
};
