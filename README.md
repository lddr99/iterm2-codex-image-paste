# iTerm2 Image Paste for Codex

Use **Cmd+V** in iTerm2 to save a clipboard image as a PNG and paste its full path into Codex CLI. Text continues to use iTerm2's native paste.

## The problem

Codex has a separate **Ctrl+V** image shortcut, but this is not an equivalent macOS experience. **Cmd+V is the standard paste shortcut on macOS**, so users naturally assume image input is unsupported or broken when it silently does nothing.

The expected workflow is simple: take a screenshot with **Control+Shift+Command+4**, return to Codex, and press **Cmd+V**. Having to discover a separate image shortcut interrupts that workflow.

Related discussions in the Codex repository:

- [#24322: Codex TUI should support image paste via Cmd-V / terminal paste, not only Ctrl-V](https://github.com/openai/codex/issues/24322)
- [#19143: Support pasting images directly into Codex CLI](https://github.com/openai/codex/issues/19143)

## How this script solves it

Bind Cmd+V to an iTerm2 Python API function. The function saves clipboard images locally and pastes their paths into the active terminal session:

```text
Cmd+V
  ├─ Clipboard contains text → iTerm2 native Paste
  └─ No text
       ├─ Image → Read PNG, or convert TIFF to PNG
       │          → Save to ~/Pictures/iTermPaste
       │          → Paste the quoted absolute file path
       └─ No image → iTerm2 native Paste
```

For example, the Codex input receives:

```text
"/Users/your-name/Pictures/iTermPaste/clip-20261118-171500-abcd1234.png"
```

Add a request such as "Read this image and explain the UI issue," then submit. Codex can open the saved file using its local image-reading tools.

This gives text and screenshots the same macOS paste shortcut while using a local file path for image input.

This script can also be used with other CLI coding agents, such as Cursor CLI, by saving clipboard images locally and pasting their file paths with the standard macOS Cmd+V shortcut. The agent must support reading local image files.

## Features

- Reads clipboard PNG images and converts TIFF using macOS's built-in `sips`.
- Saves images in `~/Pictures/iTermPaste` with unique filenames and `0600` file permissions.
- Pastes a quoted absolute path without automatically submitting the prompt.
- Prioritizes text when the clipboard contains both text and an image.
- Requires no `pngpaste` or additional image-processing packages.

## Requirements

- macOS and iTerm2 with the iTerm2 Python Runtime installed.
- **Settings → General → Magic → Enable Python API** enabled.
- A local Codex CLI session with permission to read the saved files and access to image-reading tools.

## Installation

1. In the iTerm2 menu bar at the top of the screen, select **Scripts → Manage → Install Python Runtime**. If that item is unavailable, **New Python Script** can prompt you to install the runtime.
2. From this repository's directory, run:

   ```bash
   mkdir -p "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch"
   cp paste_image_as_path.py "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/"
   ```

   If your installation uses a custom support directory, use **Scripts → Manage → Reveal Scripts in Finder** to locate the actual Scripts directory and place the file in its `AutoLaunch` subdirectory.

3. Launch the script once:

   ```bash
   /Applications/iTerm.app/Contents/Resources/it2run "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/paste_image_as_path.py"
   ```

   Adjust the script path if you installed it in a custom directory. `AutoLaunch` is a directory for startup scripts; you do not need to find a menu item with that name. Future iTerm2 launches start the script automatically.

4. Open **Scripts → Manage → Console** and check for:

   ```text
   Ready: paste_image_as_path(session_id: id)
   ```

5. Open **Settings → Keys → Key Bindings → +** and configure:

   | Field | Value |
   | --- | --- |
   | Keyboard Shortcut | Cmd+V (or Cmd+Option+V for a separate binding) |
   | Action | Invoke Script Function |
   | Function | `paste_image_as_path(session_id: id)` |

   Use **Keys → Key Bindings**. The **Shortcuts** settings page manages Actions and Snippets separately.

## Usage

1. Press **Control+Shift+Command+4** and select an area to copy a screenshot to the clipboard.
2. Return to the Codex CLI input and press **Cmd+V**, or your configured shortcut.
3. Add your instructions after the pasted image path, then submit.

Bracketed paste marks the text as a paste operation; it does not turn a path into an image attachment. It is enabled by default through `USE_BRACKETED_PASTE` in the script.

## Updating and uninstalling

After editing the script in this repository, copy it to the installation directory again. Stop the old instance in Console before launching the updated version.

To uninstall, remove the key binding, stop the script in Console, and remove `paste_image_as_path.py` from the installation directory. Keep any saved images that ongoing conversations still need.

## Troubleshooting and limitations

- **`DUPLICATE_SERVER_ORIGINATED_RPC`**: Another instance has already registered the same function. Stop all instances of this script in Console, then launch only one. Do not manually launch it again after AutoLaunch has started it.
- **No `Ready` message**: Inspect the last Console message or traceback and confirm the Python API is enabled.
- **SSH / remote Codex**: The pasted path belongs to your Mac. A remote session cannot read it directly; this script does not upload files.
- **Image retention**: Saved screenshots are not automatically deleted. Clean up `~/Pictures/iTermPaste` when the files are no longer needed.
- **Mixed clipboard content**: Text takes priority; the script does not paste an image alongside it.

## References

- [iTerm2 Python API: Running a Script](https://iterm2.com/python-api/tutorial/running.html)
- [iTerm2 Python API: RPC Registration](https://iterm2.com/python-api/registration.html)
