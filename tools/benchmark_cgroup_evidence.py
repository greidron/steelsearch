"""Observe visible cgroup-v2 ancestors; missing values never mean unlimited."""

from pathlib import Path, PurePosixPath
import re


SETTINGS = ("cpu.max", "cpu.weight", "memory.max", "memory.high", "memory.swap.max",
            "pids.max", "cpuset.cpus.effective", "cpuset.mems.effective", "io.max")
COUNTERS = ("cpu.stat", "memory.events", "memory.events.local", "memory.current",
            "memory.swap.current", "pids.current", "io.stat", "cpu.pressure",
            "memory.pressure", "io.pressure")


def mount_path(value):
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), value)


def read_values(directory, names):
    values = {}
    for name in names:
        try:
            values[name] = {"value": (directory / name).read_text().strip()}
        except OSError as error:
            values[name] = {"value": None, "error": type(error).__name__}
    return values


def observe_cgroup(pid, proc_root=Path("/proc")):
    membership = (proc_root / str(pid) / "cgroup").read_text()
    unified = [line[3:] for line in membership.splitlines() if line.startswith("0::")]
    if len(unified) != 1:
        return {"coverage": "unsupported-cgroup-layout", "membership": membership}, []
    relative = PurePosixPath(unified[0])
    if not relative.is_absolute() or ".." in relative.parts:
        raise ValueError("invalid cgroup membership path")
    mounts = []
    for line in (proc_root / "self" / "mountinfo").read_text().splitlines():
        fields, separator, kind = line.partition(" - ")
        if separator and kind.split()[0] == "cgroup2":
            columns = fields.split()
            if mount_path(columns[3]) == "/":
                mounts.append(Path(mount_path(columns[4])))
    if len(mounts) != 1:
        return {"coverage": "full-root-mount-unavailable", "membership": membership}, []
    root = mounts[0].resolve()
    current = root.joinpath(*relative.parts[1:])
    settings, counters = [], []
    while True:
        # Reject symlink escapes instead of observing unrelated host files.
        if not current.resolve().is_relative_to(root):
            raise ValueError("cgroup path escapes mounted hierarchy")
        label = "/" + str(current.relative_to(root)) if current != root else "/"
        if not current.is_dir():
            raise ValueError("cgroup ancestor disappeared")
        settings.append({"path": label, "settings": read_values(current, SETTINGS)})
        counters.append({"path": label, "counters": read_values(current, COUNTERS)})
        if current == root:
            break
        current = current.parent
    if (proc_root / str(pid) / "cgroup").read_text() != membership:
        raise ValueError("process cgroup changed during observation")
    return {"coverage": "visible-v2-ancestors", "membership": membership, "levels": settings,
            "scope": "visible constraints only; hidden namespace ancestors and effective resource availability unverified"}, counters
