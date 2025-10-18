# ebook-tools

## Configuration overview

`ebook-tools.py` reads most defaults from `config.json`, but you can now point the
script at different directories or external services without editing the code.
All relative paths are resolved from the repository directory.

### Directory settings
- **`working_dir`**: Root directory for downloaded covers and other
  long-lived artifacts. Defaults to `output/`.
- **`output_dir`**: Location for generated HTML/PDF/EPUB/audio/video files.
  Defaults to `output/ebook/` inside the working directory.
- **`tmp_dir`**: Scratch space for intermediate assets such as slide images
  and concatenation lists. Defaults to `tmp/`.

You can override any of these via the matching CLI flags (`--working-dir`,
`--output-dir`, `--tmp-dir`) or environment variables (`EBOOK_WORKING_DIR`,
`EBOOK_OUTPUT_DIR`, `EBOOK_TMP_DIR`).

### External tool settings
- **`ffmpeg_path`**: Path to the FFmpeg binary used by `pydub` and the video
  stitching helpers. Defaults to whatever `ffmpeg` is on your `PATH`.
- **`ollama_url`**: Base URL for the Ollama chat endpoint. Defaults to
  `http://localhost:11434/api/chat`.

Both values accept overrides through CLI flags (`--ffmpeg-path`,
`--ollama-url`) or the environment variables `FFMPEG_PATH` and `OLLAMA_URL`.

### Using the settings
- Interactive mode (`python ebook-tools.py -i`) exposes each knob in the
  menu, so you can persist new defaults back into `config.json`.
- In non-interactive mode, CLI flags or environment variables take precedence
  over the JSON values. The script resolves relative paths against the working
  copy and creates directories as needed.
