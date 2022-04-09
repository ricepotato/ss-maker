import os
import json
import logging
import multiprocessing
from typing import Generator, List
from snapshot import make_snapshot

target_path = "E:\\yd"


log = logging.getLogger("app")
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)
log = logging.getLogger(f"app.{__name__}")


class Snapshot:
    def __init__(self, mp4_filepath: str):
        self.mp4_filepath = mp4_filepath
        self.snapshots: List[str] = []

    def __str__(self):
        ssc = len(self.snapshots)
        return f"Snapshot({self.mp4_filepath}) - {ssc} snapshots"

    def to_dict(self):
        return {"target": self.mp4_filepath, "snapshots": self.snapshots}


def get_filelist(root_path: str, ext: str = None) -> Generator[Snapshot, None, None]:
    for (path, _, files) in os.walk(root_path):
        for filename in files:
            if ext is not None:
                _, file_ext = os.path.splitext(filename)
                if file_ext.lower() != ext:
                    continue
            yield Snapshot(os.path.join(path, filename))


def get_snapshots_filelist(root_path: str) -> Generator[str, None, None]:
    for (path, _, files) in os.walk(root_path):
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext.lower() != ".jpg":
                continue
            yield os.path.join(path, filename)


def make_snapshot_dir(filepath, target_path) -> str:
    _, name = os.path.split(filepath)
    dir_name, _ = os.path.splitext(name)
    new_dir = os.path.join(target_path, "snapshots", dir_name)
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
        log.info("snapshot dir created. %s", new_dir)
    return new_dir


def process_snapshot(ss_obj: Snapshot):
    log.info("processing... %s", ss_obj)
    snapshot_dir = make_snapshot_dir(ss_obj.mp4_filepath, target_path)
    snapshots = list(get_filelist(snapshot_dir, ".jpg"))
    if len(snapshots) <= 0:
        log.warning("snapshot not exist. %s", snapshot_dir)
        snapshots = make_snapshot(ss_obj.mp4_filepath, out_path=snapshot_dir, width=250)
    res = Snapshot(ss_obj.mp4_filepath)
    res.snapshots = snapshots
    return res


def dump_jsonfile(snapshots: List[Snapshot], output_path):
    ss_list = [snapshot.to_dict() for snapshot in snapshots]
    json_str = json.dumps(ss_list, indent=4)
    json_filepath = os.path.join(output_path, "snapshots.json")
    with open(json_filepath, "w") as f:
        f.write(json_str)


def main():
    mp4_filelist = get_filelist(target_path, ".mp4")
    p = multiprocessing.Pool(4)
    snapshots = p.map(process_snapshot, mp4_filelist)
    dump_jsonfile(snapshots, target_path)


if __name__ == "__main__":
    main()
