#!/usr/bin/env python3
"""iTerm2 RPC: paste text normally; save clipboard images and paste their path.

Key binding: Invoke Script Function -> paste_image_as_path(session_id: id)
Images remain in ~/Pictures/iTermPaste so later conversation turns can read them.
Requires iTerm2's Python runtime and Python API. Does not press Enter.
"""

import asyncio
import datetime
import functools
import os
from pathlib import Path
import subprocess
import tempfile
import traceback

import iterm2

IMAGE_DIR = Path.home() / "Pictures" / "iTermPaste"
# Paste framing, not an image attachment protocol. Intended for the Codex composer.
USE_BRACKETED_PASTE = True
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Pass paths as argv instead of interpolating them into AppleScript source.
CLIPBOARD_SCRIPT = r'''
on run argv
    set pngFile to POSIX file (item 1 of argv)
    set tiffFile to POSIX file (item 2 of argv)
    try
        set imageData to (the clipboard as «class PNGf»)
        my writeData(imageData, pngFile)
        return "png"
    end try
    try
        set imageData to (the clipboard as «class TIFF»)
        my writeData(imageData, tiffFile)
        return "tiff"
    end try
    return "none"
end run

on writeData(imageData, outputFile)
    set fileHandle to open for access outputFile with write permission
    try
        set eof fileHandle to 0
        write imageData to fileHandle
    on error messageText number errorNumber
        try
            close access fileHandle
        end try
        error messageText number errorNumber
    end try
    close access fileHandle
end writeData
'''


async def in_worker(function, *args):
    # Also works with Python runtimes older than 3.9 (no asyncio.to_thread).
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(function, *args))


def clipboard_has_text():
    result = subprocess.run(
        ["/usr/bin/pbpaste", "-Prefer", "txt"],
        capture_output=True, check=True, timeout=5,
    )
    return bool(result.stdout)


def read_clipboard_png():
    with tempfile.TemporaryDirectory(prefix="iterm-img-") as directory:
        png = Path(directory) / "clip.png"
        tiff = Path(directory) / "clip.tiff"
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", CLIPBOARD_SCRIPT, str(png), str(tiff)],
            capture_output=True, text=True, check=True, timeout=15,
        )
        kind = result.stdout.strip()
        if kind == "none":
            return None
        if kind == "tiff":
            subprocess.run(
                ["/usr/bin/sips", "-s", "format", "png", str(tiff), "--out", str(png)],
                capture_output=True, check=True, timeout=15,
            )
        elif kind != "png":
            raise RuntimeError("Unexpected clipboard response: " + kind)
        data = png.read_bytes()
        if not data.startswith(PNG_SIGNATURE):
            raise ValueError("Clipboard conversion did not produce a PNG")
        return data


def save_png(data):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    prefix = "clip-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")
    # Exclusive creation prevents collisions; mkstemp creates the file with mode 0600.
    fd, destination = tempfile.mkstemp(prefix=prefix, suffix=".png", dir=str(IMAGE_DIR))
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
    except BaseException:
        Path(destination).unlink(missing_ok=True)
        raise
    return destination


def paste_payload(path):
    # Quotes keep paths containing spaces together. No newline / automatic submission.
    quoted = '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "\x1b[200~" + quoted + "\x1b[201~" if USE_BRACKETED_PASTE else quoted


async def main(connection):
    print("Connected to iTerm2; loading sessions...", flush=True)
    app = await iterm2.async_get_app(connection)
    lock = asyncio.Lock()

    @iterm2.RPC
    async def paste_image_as_path(session_id=iterm2.Reference("id")):
        async with lock:
            session = app.get_session_by_id(session_id)
            if session is None:
                return
            try:
                if await in_worker(clipboard_has_text):
                    await iterm2.MainMenu.async_select_menu_item(connection, "Paste")
                    return
                data = await in_worker(read_clipboard_png)
                if data is None:
                    await iterm2.MainMenu.async_select_menu_item(connection, "Paste")
                    return
                destination = await in_worker(save_png, data)
                await session.async_send_text(
                    paste_payload(destination), suppress_broadcast=True,
                )
                print("Saved clipboard image: " + destination, flush=True)
            except Exception:
                # Visible in Scripts > Console; never silently disguise a conversion error.
                traceback.print_exc()
                raise

    print("Registering paste_image_as_path...", flush=True)
    await paste_image_as_path.async_register(connection, timeout=60)
    print("Ready: paste_image_as_path(session_id: id)", flush=True)


if __name__ == "__main__":
    print("Starting image paste helper; connecting to iTerm2 Python API...", flush=True)
    iterm2.run_forever(main)
