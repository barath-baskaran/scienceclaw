"""VM-wide EPI Suite rate gate (<=1 request/s). Any script can import and call wait_turn()
right before each EPI request. Uses an fcntl lock on a file that stores the last request time."""
import fcntl, os, time
LOCK = 'W-TOOL/epi_rate.lock'
MIN_GAP = 1.1  # seconds


def wait_turn():
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        raw = os.read(fd, 64)
        last = float(raw) if raw.strip() else 0.0
        gap = time.time() - last
        if gap < MIN_GAP:
            time.sleep(MIN_GAP - gap)
        os.lseek(fd, 0, 0); os.ftruncate(fd, 0)
        os.write(fd, repr(time.time()).encode())
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
