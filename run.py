import socket
from Telegram.web.app import run_web


def _get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable; no packets are sent.
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

if __name__ == "__main__":
    ip = _get_local_ip()
    print(f"Local LAN URL: http://{ip}:5000")
    print("Bind: 0.0.0.0:5000")
    run_web()