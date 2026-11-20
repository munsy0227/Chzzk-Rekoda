# Rust 미디어 검증 실험

`hls_continuity.py:validate_media()`와 같은 판정을 내리는 PyO3 확장이다.
제품 녹화기·설치기·루트 Python 의존성에는 연결하지 않는다.
TS 동기 바이트와 fMP4 박스 경계를 검사하며 영상 전체를 디코딩하는 검사는 아니다.

## 구성

- `src/lib.rs`: 바이트 입력을 빌려 검사하고 실패 시 기존과 같은 메시지의 `ValueError`를 발생시킨다.
- `compare.py`: 현재 Python 함수만 AST로 추출해 고정 사례·생성 입력·파일의 판정을 비교하고,
  Python→Rust 호출을 포함한 성공 경로 벤치마크를 수행한다. 새 테스트 라이브러리는 필요 없다.
- `regression.py`: 임시 `sitecustomize`로 기존 unittest와 Python 자식에 검증기를 주입한다.
  Rust 오류는 기존 `Unavailable(category="invalid_media")`로 변환한다.
  주입 실패는 프로세스를 실패시키며 실행 PID별 호출 수·바이트 수·검사 시간을 집계한다.
  **이 회귀 실행기는 `resource`를 사용하는 Linux/Unix용이다.**
- `Cargo.lock`: 실험 Rust 의존성을 고정한다.

## 실행

저장소 루트에서 Python 3.12, Rust/Cargo 및 FFmpeg가 있는 환경을 사용한다.
실험 당시 Python 3.12.15, Rust 1.100.0, maturin 1.16.0, PyO3 0.30.1을 사용했다.

```sh
uv venv --python 3.12 experiments/rust-media-validator/.venv
uv pip install --python experiments/rust-media-validator/.venv/bin/python maturin==1.16.0
uv export --frozen --no-dev --no-emit-project --output-file /tmp/chzzk-validator-requirements.txt > /dev/null
uv pip install --python experiments/rust-media-validator/.venv/bin/python --require-hashes -r /tmp/chzzk-validator-requirements.txt
experiments/rust-media-validator/.venv/bin/maturin build --release --locked --manifest-path experiments/rust-media-validator/Cargo.toml --interpreter experiments/rust-media-validator/.venv/bin/python --out experiments/rust-media-validator/dist
uv pip install --python experiments/rust-media-validator/.venv/bin/python experiments/rust-media-validator/dist/*.whl
experiments/rust-media-validator/.venv/bin/python experiments/rust-media-validator/compare.py --random-cases 50000 --seconds 20 --output /tmp/chzzk-validator-benchmark.json
experiments/rust-media-validator/.venv/bin/python experiments/rust-media-validator/regression.py --backend python --output /tmp/chzzk-validator-python-regression.json
experiments/rust-media-validator/.venv/bin/python experiments/rust-media-validator/regression.py --backend rust --output /tmp/chzzk-validator-rust-regression.json
```

회귀 검사에는 로컬 HTTP 서버를 열 수 있는 환경이 필요하다.
`compare.py --fixtures DIR`로 `.ts`, `.m4s`, `.mp4` 파일을 추가할 수 있다.
초기화 파일은 `init.mp4`라는 이름을 사용한다. 파일은 메모리에 전부 읽으므로 짧은 조각을 넣는다.
기존 Python이 허용하는 구조를 비교하며 디코딩 가능성까지 보장하지 않는다.

실험에서 사용한 FFmpeg 표본은 다음처럼 생성했다. 새 임시 폴더에서 실행한다.

```sh
mkdir -p /tmp/chzzk-validator-fixtures
ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=30 -f lavfi -i sine=frequency=440:sample_rate=48000 -t 3 -c:v libx264 -threads 1 -preset ultrafast -g 30 -c:a aac -f mpegts /tmp/chzzk-validator-fixtures/sample.ts
ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=30 -f lavfi -i sine=frequency=440:sample_rate=48000 -t 3 -c:v libx264 -threads 1 -preset ultrafast -g 30 -c:a aac -f hls -hls_time 1 -hls_segment_type fmp4 -hls_fmp4_init_filename init.mp4 -hls_segment_filename /tmp/chzzk-validator-fixtures/segment-%d.m4s /tmp/chzzk-validator-fixtures/playlist.m3u8
```

이후 비교 명령에 `--fixtures /tmp/chzzk-validator-fixtures`를 추가한다.

벤치마크는 같은 바이트를 재사용하고 다섯 번의 측정 중앙값을 기록한다.
합성 TS는 188바이트부터 약 8MiB까지, fMP4는 init·큰 본문·작은 박스 다수로 구분한다.
함수 처리 속도와 회귀 검사 전체의 wall/CPU 시간은 서로 다른 지표다.
회귀 검사는 인위적 대기·실패·FFmpeg 인코딩을 포함하므로 실방송 성능 비교로 쓰지 않는다.

## 결과와 범위

측정 결과 및 판정은 [작업 기록](../../.ai/worklogs/2026-11-15-rust-adoption-review.md)에 보존한다.
기본 설치에 Rust를 필수로 넣거나 타 OS용 wheel을 배포하는 작업은 이 실험에 포함하지 않는다.
