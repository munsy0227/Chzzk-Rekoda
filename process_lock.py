"""OS-owned locks: a crashed process cannot leave a stale ownership flag."""

import os
from pathlib import Path


class FileLock:
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def __enter__(self):
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        self.file = os.fdopen(fd, "r+b")
        try:
            if os.name == "nt":
                import msvcrt

                if self.path.stat().st_size == 0:
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.file.close()
            self.file = None
            raise
        return self

    def __exit__(self, *args):
        if self.file is not None:
            self.file.close()
            self.file = None
