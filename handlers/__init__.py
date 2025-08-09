from .core import handle_ping, handle_stop, handle_pose
# from .render import ...
# from .camera import ...
# from .training import ...

handlers = {
    "ping": handle_ping,
    "stop": handle_stop,
    "pose": handle_pose,
    # "render_start": render_start,
    # "camera_move": camera_move,
}

