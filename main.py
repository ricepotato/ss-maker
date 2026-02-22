from dataclasses import dataclass
import hashlib
import os
import json
import logging
import multiprocessing
import shutil
import argparse
import sys
import pathlib
import pydantic
from typing import Generator, List
from snapshot import make_snapshot
from concurrent.futures import ProcessPoolExecutor


log = logging.getLogger("app")
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)
log = logging.getLogger(f"app.{__name__}")

CHUNK_SIZE = 1024 * 1024 * 10


class Target(pydantic.BaseModel):
    files: List[pathlib.Path]
    dirs: List[pathlib.Path]
  


def get_file_hash(filepath):
    with open(filepath, "rb") as f:
        data = f.read(CHUNK_SIZE)
        sha256 = hashlib.sha256()
        sha256.update(data)
        return sha256.hexdigest()


class Snapshot:
    def __init__(self, target: pathlib.Path):
        self.target = target
        self.snapshots: List[str] = []
        self._sha256 = None
        self._snapshot_path = self.target.parent / ".snapshots"

    @property
    def sha256(self):
        if self._sha256 is None:
            self._sha256 = get_file_hash(self.target)
        return self._sha256
    
    def make_snapshot_path(self):
        if not os.path.exists(self._snapshot_path):
            os.makedirs(self._snapshot_path)

    def make(self):
        self.make_snapshot_path()
        out_path = self._snapshot_path / self.sha256
        shot_count = 16
        if not os.path.exists(out_path):
            os.makedirs(out_path)
            snapshot_paths = make_snapshot(str(self.target), out_path=str(out_path), shot_count=shot_count, width=250)
            self.snapshots = snapshot_paths 
        else:
            log.warning("snapshot dir already exists. skip... %s", out_path)
            self.snapshots = get_file_list(out_path, ".jpg")
        return self

    @property
    def name(self) -> str:
        return self.target.stem

    def __str__(self):
        ssc = len(self.snapshots)
        return f"Snapshot({self.target}) - {ssc} snapshots"
    
    def __repr__(self):
        return self.__str__()            
    
    def to_dict(self):
        return {
            "name": self.target.stem,
            "target": self.target.as_posix(),
            "snapshots": self.snapshots,
            "sha256": self.sha256,
            "dirname": self.target.parent.name
        }

def get_file_list(root_path: str, ext: str = None):
    return [os.path.join(root_path, item) for item in os.listdir(root_path)]

def get_target_list(root_path: str, ext: str = None) -> Target:
    files = []
    dirs = []
    for item in os.listdir(root_path):
        item_path = os.path.join(root_path, item)
        if os.path.isdir(item_path):
            dirs.append(pathlib.Path(item_path))
        else:
            _, file_ext = os.path.splitext(item)
            if ext is not None and file_ext.lower() != ext:
                continue
            files.append(pathlib.Path(item_path))
    return Target(files=files, dirs=dirs)


def get_snapshots_filelist(root_path: str) -> Generator[str, None, None]:
    for (path, _, files) in os.walk(root_path):
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext.lower() != ".jpg":
                continue
            yield os.path.join(path, filename)


def make_snapshot_dir(filepath, target_path, sha256) -> str:
    _, name = os.path.split(filepath)
    dir_name, _ = os.path.splitext(name)
    new_dir = os.path.join(target_path, "snapshots", sha256)
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
        log.info("snapshot dir created. %s", new_dir)
    else:
        log.warning("snapshot dir already exists. %s", new_dir)
    return new_dir


def process_snapshot(target: pathlib.Path) -> Snapshot:
    target_path = target.parent
    mp4_filepath = str(target)
    log.info("processing... %s", mp4_filepath)

    res = Snapshot(target)
    snapshot_dir = make_snapshot_dir(mp4_filepath, target_path, res.sha256)

    snapshots = list(get_target_list(snapshot_dir, ".jpg"))
    if len(snapshots) <= 0:
        log.warning("snapshot not exist. %s", snapshot_dir)
        snapshots = make_snapshot(mp4_filepath, out_path=snapshot_dir, width=250)
    res.snapshots = snapshots
    return res


def copy_to_path(filename, dest_path):
    new_path = os.path.join(dest_path, filename)
    shutil.copyfile(filename, new_path)


def dump_jsonfile(snapshots: List[Snapshot], output_path):
    ss_list = [snapshot.to_dict() for snapshot in snapshots if snapshot is not None]
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
    parser.add_argument("--recursive", default=False, action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.target):
        print("path not exists.", args.target)
        sys.exit(1)

    target = get_target_list(args.target, ".mp4")
    snapshot_list = [Snapshot(target) for target in target.files]

    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = []
        for snapshot in snapshot_list:
            future = executor.submit(snapshot.make)
            futures.append(future)

        futures_result = [future.result() for future in futures]

        for result in futures_result:
            results.append(result)

    dump_jsonfile(results, args.target)




if __name__ == "__main__":
    main()
