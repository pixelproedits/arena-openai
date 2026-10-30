"""Private, bounded filesystem operations for Arena (POSIX, Python standard library).

Every path component is opened with O_NOFOLLOW. Artifact paths never pass through
realpath(), which would silently accept a symlink. No operation follows hardlinks.
"""
import contextlib
import fcntl
import os
import secrets
import stat

MAX_BYTES = 16 * 1024 * 1024  # accommodates all 2160 upstream candidates and their state


class UnsafePath(ValueError):
    """A filesystem operation was refused; messages never include file contents."""


def _parts(path):
    path = os.fspath(path)
    if (not isinstance(path, str) or not path.startswith("/") or "\x00" in path
            or any(p in (".", "..") for p in path.split("/"))):
        raise UnsafePath("use an absolute path without traversal components")
    if os.path.normpath(path) != path or path == "/":
        raise UnsafePath("use a canonical absolute file or directory path")
    return path.split("/")[1:]


def _dir(path, create=False, private=False):
    parts = _parts(path)
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(parts):
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        info = os.fstat(fd)
        if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise UnsafePath("Arena directories must be owned by the current user and mode 0700")
        return fd
    except (OSError, ValueError) as exc:
        os.close(fd)
        if isinstance(exc, UnsafePath):
            raise
        raise UnsafePath("unsafe or unavailable directory") from None


def _parent(path, create=False):
    parts = _parts(path)
    parent = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
    if parent == "/":
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    else:
        fd = _dir(parent, create=create)
    return fd, parts[-1]


def _regular(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o022):
        raise UnsafePath("Arena inputs must be owned regular files without hardlinks or shared write access")


def read_text(path, limit=MAX_BYTES):
    parent, name = _parent(path)
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        info = os.fstat(fd)
        _regular(info)
        if info.st_size > limit:
            raise UnsafePath("Arena input exceeds the size limit")
        chunks, size = [], 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - size))
            if not block:
                break
            size += len(block)
            if size > limit:
                raise UnsafePath("Arena input exceeds the size limit")
            chunks.append(block)
        try:
            return b"".join(chunks).decode("utf-8")
        except UnicodeDecodeError:
            raise UnsafePath("Arena input must be UTF-8 text") from None
    except OSError:
        raise UnsafePath("unsafe or unavailable input file") from None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def file_exists(path):
    """Missing is false; unsafe existing paths fail closed instead of looking missing."""
    try:
        parent, name = _parent(path)
    except UnsafePath:
        # A missing parent is normal before prompts create phase directories.
        # lstat cannot follow the final component; it is only used to distinguish
        # absence after _parent has already refused the attempted traversal.
        current = "/"
        for part in _parts(path)[:-1]:
            current = os.path.join(current, part)
            try:
                info = os.lstat(current)
            except FileNotFoundError:
                return False
            if not stat.S_ISDIR(info.st_mode):
                raise UnsafePath("unsafe directory in Arena artifact path")
        raise
    try:
        try:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return False
        _regular(info)
        if info.st_size > MAX_BYTES:
            raise UnsafePath("Arena input exceeds the size limit")
        return info.st_size > 0
    finally:
        os.close(parent)


def make_dirs(path):
    fd = _dir(path, create=True, private=True)
    os.close(fd)


def validate_run(path):
    fd = _dir(path, private=True)
    os.close(fd)
    return path


def create_run(path):
    parent, name = _parent(path, create=True)
    try:
        info = os.fstat(parent)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise UnsafePath("Arena run parent must be owned by the current user and mode 0700")
        # A new name is mandatory: never reuse a directory containing attacker data.
        os.mkdir(name, 0o700, dir_fd=parent)
    except FileExistsError:
        raise UnsafePath("Arena run directory already exists; choose a fresh name") from None
    except OSError:
        raise UnsafePath("could not create private Arena run directory") from None
    finally:
        os.close(parent)
    validate_run(path)


def write_text(path, text, replace=True):
    return write_bytes(path, text.encode("utf-8"), replace=replace)


def write_bytes(path, payload, replace=True):
    if not isinstance(payload, bytes):
        raise UnsafePath("Arena output must be bytes")
    if len(payload) > MAX_BYTES:
        raise UnsafePath("Arena output exceeds the size limit")
    parent, name = _parent(path, create=True)
    temporary = ".arena-write-" + secrets.token_hex(16)
    fd = None
    try:
        try:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            info = None
        if info is not None:
            _regular(info)
            if not replace:
                raise UnsafePath("Arena output already exists")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
        else:
            # Link then unlink provides atomic no-clobber publication; it cannot
            # follow a destination symlink or overwrite a concurrently created file.
            os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.unlink(temporary, dir_fd=parent)
        os.fsync(parent)
    except OSError:
        raise UnsafePath("could not safely write Arena output") from None
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
        os.close(parent)


def quarantine(path):
    # Capture only bounded validated bytes; keep private mode on the copied file.
    text = read_text(path)
    for suffix in range(1000):
        target = path + ".unreadable" + (".%d" % suffix if suffix else "")
        try:
            write_text(target, text, replace=False)
        except UnsafePath:
            if file_exists(target):
                continue
            raise
        parent, name = _parent(path)
        try:
            os.unlink(name, dir_fd=parent)
        finally:
            os.close(parent)
        return target
    raise UnsafePath("too many quarantined verdicts; stop this run")


@contextlib.contextmanager
def lock(path):
    """Serialize state transitions and reservation operations within one run."""
    parent, name = _parent(path)
    fd = None
    try:
        fd = os.open(name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
        _regular(os.fstat(fd))
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except OSError:
        raise UnsafePath("Arena run is locked or the lock file is unsafe") from None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)
