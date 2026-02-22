# ss-maker

간단한 비디오 스냅샷 생성기입니다. 지정한 폴더(또는 재귀적 하위폴더)에 있는 모든 `*.mp4` 파일을 찾아 각 비디오에 대해 정해진 개수(기본 16)의 스냅샷 이미지를 생성합니다.

주요 동작
- 대상 폴더 내의 모든 `*.mp4` 파일을 검색합니다.
- 각 비디오별로 SHA256 해시(파일의 앞쪽 CHUNK_SIZE 바이트 기준)를 계산하여 `.snapshots/{sha256}` 폴더를 생성합니다.
- OpenCV(`snapshot.py`의 `make_snapshot`)를 사용해 프레임을 추출하여 기본 너비 250px로 리사이즈한 JPG 이미지 16장을 생성합니다.
- 실행 완료 후 대상 폴더에 `snapshots.json` 및 `snapshots.js` 파일을 생성하고, 리포지터리 루트의 `index.html`과 `app.js`를 대상 폴더로 복사합니다.

요구사항
- Python 3.8+
- Python 패키지: `opencv-python`, `pydantic` (간단 설치 예: `pip install opencv-python pydantic`)

사용법
- 현재 리포지터리 루트에서 실행해야 `index.html`과 `app.js`를 대상 폴더로 복사합니다.
- 기본 실행 (Windows / PowerShell 예):

```powershell
python main.py --target C:\path\to\videos
```

- 하위 디렉터리까지 재귀적으로 처리하려면 `--recursive` 옵션을 추가합니다:

```powershell
python main.py --target C:\path\to\videos --recursive
```

출력
- 각 비디오의 부모 폴더에 `.snapshots/{sha256}/` 디렉터리가 생성되고 그 안에 JPG 파일(기본 16장)이 들어갑니다.
- 대상 폴더(명시한 `--target`)에 `snapshots.json` (메타 정보 목록)과 `snapshots.js`(`const videos = ...`)가 생성됩니다.
- 리포지터리 루트의 `index.html` 및 `app.js`가 대상 폴더로 복사됩니다.

동작 참고
- 스냅샷 생성은 내부적으로 OpenCV를 사용합니다(`snapshot.py`).
- 해시 계산은 파일의 앞부분(CHUNK_SIZE = 10MB)만 읽어 수행합니다.
- 병렬처리는 `concurrent.futures.ProcessPoolExecutor`로 최대 4개 프로세스를 사용합니다.
- 이미 `.snapshots/{sha256}` 디렉터리가 존재하면 해당 비디오는 스킵됩니다.

예시 플로우
1. `python main.py --target C:\Users\you\Videos`
2. 각 비디오 파일별로 `.snapshots/{sha256}`에 `1.jpg` ~ `16.jpg` 생성
3. `C:\Users\you\Videos\snapshots.json` 및 `snapshots.js` 생성, `index.html`/`app.js` 복사

문제 해결
- OpenCV 설치 시 바이너리 의존성 문제가 발생하면 플랫폼에 맞는 설치 방법(예: Windows의 경우 `pip install opencv-python`으로 충분함)을 확인하세요.

더 궁금한 점이나 추가 형식(예: 출력 폴더 변경, 이미지 개수 조절 등) 요청 시 알려주세요.