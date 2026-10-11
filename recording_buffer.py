"""Bounded, session-owned storage of validated media, without request secrets."""

import hashlib
import json
import math
import re
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path


BUFFER_SECONDS = 120.0
BUFFER_BYTES = 256 * 1024 * 1024
OWNED_NAME = re.compile(r"[0-9a-f]{64}\.(?:json|bin)|[0-9a-f]{32}\.part")


class BufferFull(Exception):
    pass


class MediaBuffer:
    """One writer process at a time; the recorder owns the directory lifetime."""

    def __init__(self, directory, live_id, rendition, max_bytes=BUFFER_BYTES,
                 max_seconds=BUFFER_SECONDS):
        self.root = Path(directory)
        if not self.root.is_dir() or self.root.is_symlink():
            raise OSError("Buffer directory unavailable")
        self.live_id, self.rendition = live_id, rendition
        self.max_bytes, self.max_seconds = max_bytes, max_seconds
        self.lock = threading.RLock()
        self.rows = {}
        self.used = 0
        self.cutoff = None
        self.pending_from = None
        self.byte_full = False
        # The previous child has exited before the next child opens the store.
        for path in self.root.iterdir():
            if not OWNED_NAME.fullmatch(path.name) or path.is_symlink():
                continue
            if path.suffix == ".part":
                path.unlink()
            elif path.suffix == ".json":
                try:
                    if path.stat().st_size > 4096:
                        raise ValueError("Oversized metadata")
                    row = json.loads(path.read_text())
                    self.validate_row(row, path.stem)
                    if (row['live_id'], row['rendition']) != (live_id, rendition):
                        raise ValueError("Different recording")
                    payload = self.root / (path.stem + '.bin')
                    if payload.is_symlink() or payload.stat().st_size != row['size']:
                        raise ValueError("Incomplete payload")
                    self.rows[path.stem] = row
                except (ValueError, KeyError, TypeError, OSError):
                    self.remove(path.stem)
        # Drop only our orphan payloads; never scan/delete recording files.
        for path in self.root.iterdir():
            if OWNED_NAME.fullmatch(path.name) and path.suffix == '.bin' and path.stem not in self.rows:
                path.unlink()
        self.used = sum(p.stat().st_size for p in self.root.iterdir()
                        if OWNED_NAME.fullmatch(p.name) and not p.is_symlink())
        while self.used > max_bytes and self.rows:
            self.remove(max(self.rows, key=lambda key: self.rows[key]['at']))

    @staticmethod
    def validate_row(row, key):
        fields = {'version', 'live_id', 'rendition', 'at', 'duration', 'number',
                  'discontinuity', 'discontinuity_id', 'cdn', 'mode', 'init_size',
                  'size', 'sha256', 'key'}
        if (not isinstance(row, dict) or set(row) != fields
                or type(row['version']) is not int or row['version'] != 1):
            raise ValueError("Invalid metadata")
        if (row['key'] != key or not isinstance(row['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', row['sha256'])):
            raise ValueError("Invalid identity")
        if (type(row['live_id']) is not int or not isinstance(row['rendition'], str)
                or len(row['rendition']) > 32 or type(row['number']) is not int
                or row['number'] < 0 or type(row['discontinuity']) is not bool
                or not isinstance(row['cdn'], str) or not isinstance(row['mode'], str)
                or row['cdn'] not in {'korean', 'akamai', 'unknown'}
                or row['mode'] not in {'hls', 'llhls'}):
            raise ValueError("Invalid segment")
        if (row['discontinuity_id'] is not None
                and (type(row['discontinuity_id']) is not int or row['discontinuity_id'] < 0)):
            raise ValueError("Invalid discontinuity")
        if (type(row['duration']) not in (int, float) or not math.isfinite(row['duration'])
                or not 0 < row['duration'] <= BUFFER_SECONDS
                or type(row['size']) is not int or not 0 < row['size'] <= BUFFER_BYTES
                or type(row['init_size']) is not int or not 0 <= row['init_size'] < row['size']
                or not isinstance(row['at'], str) or len(row['at']) > 40
                or datetime.fromisoformat(row['at']).tzinfo is None):
            raise ValueError("Invalid dimensions")

    @staticmethod
    def end(row):
        return datetime.fromisoformat(row['at']) + timedelta(seconds=row['duration'])

    def entries(self):
        with self.lock:
            return sorted(self.rows.values(), key=lambda row: datetime.fromisoformat(row['at']))

    def can_store(self, at, duration):
        with self.lock:
            if at is None or (self.cutoff and at + timedelta(seconds=duration) <= self.cutoff):
                return False
            first = min((datetime.fromisoformat(row['at']) for row in self.rows.values()), default=at)
            if self.pending_from is not None:
                first = min(first, self.pending_from)
            return ((at + timedelta(seconds=duration) - min(first, at)).total_seconds()
                    <= self.max_seconds and self.used < self.max_bytes and not self.byte_full
                    and len(self.rows) < 2048)

    def note_pending(self, at):
        with self.lock:
            if at is not None and (self.cutoff is None or at >= self.cutoff):
                self.pending_from = at if self.pending_from is None else min(self.pending_from, at)

    def store(self, metadata, initialization, media):
        with self.lock:
            at = datetime.fromisoformat(metadata['at'])
            if not self.can_store(at, metadata['duration']):
                raise BufferFull()
            digest = hashlib.sha256(initialization + media).hexdigest()
            key = hashlib.sha256(json.dumps([self.live_id, self.rendition, metadata['at'],
                                            metadata['duration'], metadata['discontinuity_id'],
                                            digest]).encode()).hexdigest()
            if key in self.rows:
                return self.rows[key]
            row = dict(version=1, live_id=self.live_id, rendition=self.rendition,
                       **metadata, size=len(initialization) + len(media),
                       init_size=len(initialization), sha256=digest, key=key)
            self.validate_row(row, key)
            encoded = json.dumps(row).encode()
            reservation = row['size'] + len(encoded)
            if self.used + reservation > self.max_bytes:
                self.byte_full = True
                raise BufferFull()
            self.used += reservation  # Includes files being written.
            part = self.root / (uuid.uuid4().hex + '.part')
            meta_part = self.root / (uuid.uuid4().hex + '.part')
            try:
                with part.open('xb') as output:
                    output.write(initialization)
                    output.write(media)
                with meta_part.open('xb') as output:
                    output.write(encoded)
                part.replace(self.root / (key + '.bin'))
                meta_part.replace(self.root / (key + '.json'))
                self.rows[key] = row
                return row
            except OSError:
                self.used -= reservation
                for path in (part, meta_part, self.root / (key + '.bin'), self.root / (key + '.json')):
                    path.unlink(missing_ok=True)
                raise

    def load(self, row):
        with self.lock:
            self.validate_row(row, row['key'])
            path = self.root / (row['key'] + '.bin')
            if path.is_symlink() or path.stat().st_size != row['size']:
                raise ValueError("Incomplete buffered media")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError("Corrupt buffered media")
            return data[:row['init_size']], data[row['init_size']:]

    def remove(self, key):
        with self.lock:
            self.rows.pop(key, None)
            for suffix in ('.json', '.bin'):
                path = self.root / (key + suffix)
                try:
                    size = path.stat().st_size
                    path.unlink()
                    self.used = max(0, self.used - size)
                    self.byte_full = False
                except FileNotFoundError:
                    pass

    def discard_before(self, end):
        with self.lock:
            self.cutoff = end if self.cutoff is None else max(self.cutoff, end)
            self.pending_from = self.cutoff
            self.byte_full = False
            for key, row in list(self.rows.items()):
                if self.end(row) <= self.cutoff:
                    self.remove(key)
