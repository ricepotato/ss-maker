import os
import json
import logging
import multiprocessing
import shutil
import argparse
import sys
from typing import Generator, List
from snapshot import make_snapshot


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
        return {
            "name": os.path.split(self.mp4_filepath)[-1],
            "target": self.mp4_filepath,
            "snapshots": self.snapshots,
        }


def get_filelist(root_path: str, ext: str = None) -> Generator[str, None, None]:
    for (path, _, files) in os.walk(root_path):
        for filename in files:
            if ext is not None:
                _, file_ext = os.path.splitext(filename)
                if file_ext.lower() != ext:
                    continue
            # yield Snapshot(os.path.join(path, filename))
            yield os.path.join(path, filename)


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
    else:
        log.warning("snapshot dir already exists. %s", new_dir)
    return new_dir


def process_snapshot(arg) -> Snapshot:
    target_path = arg[0]
    mp4_filepath = arg[1]
    log.info("processing... %s", mp4_filepath)
    snapshot_dir = make_snapshot_dir(mp4_filepath, target_path)
    snapshots = list(get_filelist(snapshot_dir, ".jpg"))
    if len(snapshots) <= 0:
        log.warning("snapshot not exist. %s", snapshot_dir)
        snapshots = make_snapshot(mp4_filepath, out_path=snapshot_dir, width=250)
    res = Snapshot(mp4_filepath)
    res.snapshots = snapshots
    return res


def copy_to_path(filename, dest_path):
    new_path = os.path.join(dest_path, filename)
    shutil.copyfile(filename, new_path)


def dump_jsonfile(snapshots: List[Snapshot], output_path):
    ss_list = [snapshot.to_dict() for snapshot in snapshots]
    json_str = json.dumps(ss_list, indent=4)
    json_filepath = os.path.join(output_path, "snapshots.json")
    with open(json_filepath, "w") as f:
        f.write(json_str)
    js_filepath = os.path.join(output_path, "snapshots.js")
    with open(js_filepath, "w") as f:
        f.write(f"const videos={json_str}")

    copy_to_path("index.html", output_path)
    copy_to_path("app.js", output_path)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.target):
        print("path not exists.", args.target)
        sys.exit(1)

    mp4_filelist = get_filelist(args.target, ".mp4")
    args_list = [[args.target, mp4_file] for mp4_file in mp4_filelist]
    p = multiprocessing.Pool(4)
    snapshots = p.map(process_snapshot, args_list)
    dump_jsonfile(snapshots, args.target)


if __name__ == "__main__":
    main()
