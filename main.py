from dataclasses import dataclass
import hashlib
import os
import json
import logging
import multiprocessing
from collections import defaultdict
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
HASH_CACHE_FILENAME = ".hash_cache.json"
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}


class Target(pydantic.BaseModel):
    files: List[pathlib.Path]
    dirs: List[pathlib.Path]


def get_file_hash(filepath):
    with open(filepath, "rb") as f:
        data = f.read(CHUNK_SIZE)
        sha256 = hashlib.sha256()
        sha256.update(data)
        return sha256.hexdigest()


def load_hash_cache(cache_dir: pathlib.Path) -> dict:
    cache_path = cache_dir / HASH_CACHE_FILENAME
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_hash_cache(cache_dir: pathlib.Path, cache: dict):
    cache_path = cache_dir / HASH_CACHE_FILENAME
    with open(cache_path, "w") as f:
        json.dump(cache, f)


class Snapshot:
    def __init__(self, target: pathlib.Path):
        self.target = target
        self.snapshots: List[str] = []
        self._sha256 = None
        self._snapshot_path = self.target.parent / ".snapshots"
        self._cache_entry: dict = None  # 캐시 미스 시 메인 프로세스에서 저장할 엔트리

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

        # stat 기반 캐시 조회 — 파일 내용을 읽지 않고 sha256 복원 시도
        cache = load_hash_cache(self._snapshot_path)
        key = self.target.name
        stat = self.target.stat()
        entry = cache.get(key)
        cache_hit = (
            entry is not None
            and entry.get("size") == stat.st_size
            and entry.get("mtime") == stat.st_mtime
        )

        if cache_hit:
            self._sha256 = entry["sha256"]
            out_path = self._snapshot_path / self._sha256
            if out_path.exists():
                log.info("cache hit, skip: %s", self.target.name)
                self.snapshots = get_file_list(out_path, ".jpg")
                return self

        # 캐시 미스: sha256 계산 후 스냅샷 생성
        out_path = self._snapshot_path / self.sha256
        shot_count = 16
        if not out_path.exists():
            os.makedirs(out_path, exist_ok=True)
            self.snapshots = make_snapshot(str(self.target), out_path=str(out_path), shot_count=shot_count, width=250)
        else:
            log.warning("snapshot dir already exists. skip... %s", out_path)
            self.snapshots = get_file_list(out_path, ".jpg")

        # 캐시 엔트리 저장은 메인 프로세스에서 일괄 처리
        self._cache_entry = {"size": stat.st_size, "mtime": stat.st_mtime, "sha256": self.sha256}

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
            "kind": "video",
            "name": self.target.stem,
            "target": self.target.as_posix(),
            "snapshots": self.snapshots,
            "sha256": self.sha256,
            "dirname": self.target.parent.name
        }

class ImageFile:
    def __init__(self, target: pathlib.Path):
        self.target = target
        self._sha256 = None
        self._snapshot_path = self.target.parent / ".snapshots"
        self._cache_entry: dict = None

    @property
    def sha256(self):
        if self._sha256 is None:
            self._sha256 = get_file_hash(self.target)
        return self._sha256

    def make(self):
        os.makedirs(self._snapshot_path, exist_ok=True)
        cache = load_hash_cache(self._snapshot_path)
        key = self.target.name
        stat = self.target.stat()
        entry = cache.get(key)
        cache_hit = (
            entry is not None
            and entry.get("size") == stat.st_size
            and entry.get("mtime") == stat.st_mtime
        )
        if cache_hit:
            self._sha256 = entry["sha256"]
            log.info("cache hit (image): %s", self.target.name)
        else:
            self._cache_entry = {"size": stat.st_size, "mtime": stat.st_mtime, "sha256": self.sha256}
        return self

    def to_dict(self):
        return {
            "kind": "image",
            "name": self.target.stem,
            "target": self.target.as_posix(),
            "sha256": self.sha256,
            "dirname": self.target.parent.name
        }


def get_file_list(root_path: str, ext: str = None):
    return [os.path.join(root_path, item) for item in os.listdir(root_path)]

def scan_dir(root_path: str, ext: str = None) -> Target:
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

    snapshots = list(scan_dir(snapshot_dir, ".jpg"))
    if len(snapshots) <= 0:
        log.warning("snapshot not exist. %s", snapshot_dir)
        snapshots = make_snapshot(mp4_filepath, out_path=snapshot_dir, width=250)
    res.snapshots = snapshots
    return res


def copy_to_path(filename, dest_path):
    new_path = os.path.join(dest_path, filename)
    shutil.copyfile(filename, new_path)


def find_image_files(root: pathlib.Path, recursive: bool = False) -> List[pathlib.Path]:
    target = scan_dir(root)
    image_files = [f for f in target.files if f.suffix.lower() in IMAGE_EXTENSIONS]

    if not recursive:
        return image_files

    for dir_item in target.dirs:
        if dir_item.name == ".snapshots":
            continue
        image_files.extend(find_image_files(dir_item, recursive=True))

    return image_files


def build_tree(snapshots: List[Snapshot], root: pathlib.Path) -> dict:
    tree: dict = {"type": "dir", "name": root.name, "children": []}
    for snapshot in snapshots:
        if snapshot is None:
            continue
        try:
            rel_path = snapshot.target.relative_to(root)
        except ValueError:
            rel_path = pathlib.Path(snapshot.target.name)
        parts = rel_path.parts
        node = tree
        for part in parts[:-1]:
            existing = next(
                (c for c in node["children"] if c.get("type") == "dir" and c["name"] == part),
                None,
            )
            if existing is None:
                existing = {"type": "dir", "name": part, "children": []}
                node["children"].append(existing)
            node = existing
        node["children"].append({"type": "file", **snapshot.to_dict()})
    return tree


def dump_jsonfile(snapshots: List[Snapshot], output_path, root_path: pathlib.Path):
    tree = build_tree(snapshots, root_path)
    json_str = json.dumps(tree, indent=4, ensure_ascii=False)
    json_filepath = os.path.join(output_path, "snapshots.json")
    with open(json_filepath, "w", encoding="utf-8") as f:
        f.write(json_str)
    js_filepath = os.path.join(output_path, "snapshots.js")
    with open(js_filepath, "w", encoding="utf-8") as f:
        f.write(f"const videos={json_str}")

    copy_to_path("index.html", output_path)
    copy_to_path("app.js", output_path)


def find_mp4_files(root: pathlib.Path, recursive: bool = False) -> List[pathlib.Path]:
    target = scan_dir(root, ".mp4")

    if not recursive:
        return target.files

    files = target.files
    for dir_item in target.dirs:
        if dir_item.name == ".snapshots":
            continue
        log.info("recursive dir: %s", dir_item)
        files.extend(find_mp4_files(dir_item, recursive=True))

    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--recursive", default=False, action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.target):
        log.warning("path not exists. %s", args.target)
        sys.exit(1)

    root_path = pathlib.Path(args.target)

    # 동영상 처리 (병렬)
    files = find_mp4_files(root_path, recursive=args.recursive)
    snapshot_list = [Snapshot(target) for target in files]

    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(s.make) for s in snapshot_list]
        for future in futures:
            results.append(future.result())

    # 이미지 처리 (순차)
    image_files = find_image_files(root_path, recursive=args.recursive)
    image_results = [ImageFile(target).make() for target in image_files]
    log.info("found %d image files", len(image_results))

    all_results = results + image_results

    # 캐시 엔트리를 snapshot_path 기준으로 그룹핑해서 한 번에 저장
    cache_updates = defaultdict(dict)
    for result in all_results:
        if result is not None and result._cache_entry is not None:
            cache_updates[result._snapshot_path][result.target.name] = result._cache_entry

    for snapshot_path, entries in cache_updates.items():
        cache = load_hash_cache(snapshot_path)
        cache.update(entries)
        save_hash_cache(snapshot_path, cache)

    dump_jsonfile(all_results, args.target, root_path)




if __name__ == "__main__":
    main()
