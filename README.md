# Documentation claim auditor

This offline static auditor compares documented claims about the checked capability with Python source evidence. It never executes inspected code.

## Usage

```sh
python3 -m pip install .
video-editing-claim-audit audit . --json
python3 -m video_editing_claim_audit audit . --verbose
```

The optional repository path defaults to the current directory. Use `--ignore PREFIX` repeatedly to exclude paths and `--fail-on medium` to include test-only findings in the failure threshold. Exit status is 0 for PASS, 2 for findings at the selected threshold, and 1 for usage or I/O errors. Use `--version` to show the version.

The findings are:

```text
documented-video-editing-claim-false
documented-no-video-editing-claim-false
```

## Differentiation

The checked operation concerns existing footage. The phrase lists exclude synthetic video creation, stabilising video, recording the screen to a file, still-image capture, webcam capture, resizing still images, live broadcast, and audio-only capture.

They also exclude spreadsheet reading and generation, word-document reading and generation, presentation reading and generation, PDF extraction, generation, merging, splitting, encryption, rotation, form-filling, watermarking, redaction, compression and annotation, table extraction, OCR, document extraction, e-signature, and payment-processing claims.

## Limitations

This phrase can yield a false positive because a roadmap may describe a future capability:

```text
video editing
```

This phrase can yield a false positive because a person or a script editor may be meant:

```text
video editor
```

This phrase can yield a false positive because metadata or a still-image sequence may be meant:

```text
trim video
```

This phrase can yield a false positive because a cut scene or screenplay may be meant:

```text
cut video
```

This phrase can yield a false positive because a still frame or thumbnail may be meant:

```text
crop video
```

This phrase can yield a false positive because a player window may be meant:

```text
resize video
```

This phrase can yield a false positive because a dual display or split-screen layout may be meant:

```text
split video
```

This phrase can yield a false positive because metadata records or playback tracks may be meant:

```text
merge videos
```

- An unrelated `.run()` call can satisfy the final ffmpeg leg when the input and edit legs are present.

- An unrelated object method can satisfy the moviepy method leg when a clip construction is present.

- The moviepy pair does not verify that the method operates on the constructed clip.

- The cv2 route does not verify that frames flow from the reader to the writer.

- The imageio route does not verify that frames flow from the reader to the writer.

- A variable filter name is missed because the ffmpeg filter must be a string constant.

- Filters outside the listed set, such as hflip, drawtext and overlay, are missed.

- A variable filename is missed because the cv2 source must be a string constant.

- A bare library import is not evidence.

- A roadmap, changelog or TODO claim still counts.

- A denial outside the denial list is not recognised, and a matching positive phrase may still count.

- Documents outside the root README and directories named docs are not read.

- Evidence split across modules is missed.

- A locally defined route name shadows the library route, including a thin wrapper.

- Dead code counts as evidence.

- Subprocess commands are not evidence.

- A still-image resize or crop alone is not evidence.

- A webcam read is not evidence, even when its frames are written.

- Audio-only changes are not evidence, even alongside another module.

- A locally defined generic name is shadowed.

- Alias chains the tracer cannot follow are missed.

- Exact phrases are matched without semantic interpretation.

- Implementations in other languages are invisible.

- Runtime-only routes are invisible because code is not executed and the network is not accessed.

- The moviepy construction and method must be in one module.

- The ffmpeg input, edit and output legs must be in one module.

- The cv2 capture, read and writer must be in one module.

- The imageio reader and writer must be in one module.

- A lone clip construction without a method call is not evidence.

- A lone moviepy method call without a clip construction is not evidence.

- A lone ffmpeg input is not evidence.

- A lone ffmpeg filter or concatenation call is not evidence.

- A lone ffmpeg output or run call is not evidence.

- An ffmpeg input and output without an edit leg is not evidence.

- A device-index capture is not evidence.

- A non-video filename is not evidence for the cv2 route.

- A file capture and read without a writer is not evidence.

- A lone cv2 writer is not evidence.

- A lone imageio reader is not evidence.

- A lone imageio writer is not evidence.

- Static matching does not establish whether a detected operation is correct.
