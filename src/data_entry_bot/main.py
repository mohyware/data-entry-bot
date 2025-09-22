import os
import time
import sys
import logging
from typing import List, Dict

import requests
from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import TimeoutError as PywinautoTimeoutError
from pywinauto.keyboard import send_keys


def configure_logging() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def ensure_output_dir() -> str:

    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    output_dir = os.path.join(desktop_dir, "tjm-project")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def fetch_posts(limit: int = 10) -> List[Dict]:

    url = "https://jsonplaceholder.typicode.com/posts"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        posts = response.json()
        return posts[:limit]
    except requests.RequestException as exc:
        logging.error("Failed to fetch posts: %s", exc)
        raise


def build_blog_text(post: Dict) -> str:

    post_id = post.get("id", "")
    title = post.get("title", "Untitled")
    body = post.get("body", "")

    lines = [
        f"Post {post_id}: {title}",
        "by JSONPlaceholder",
        "---",
        body,
        "",
        f"Source: https://jsonplaceholder.typicode.com/posts/{post_id}",
    ]
    return "\n".join(lines)


def launch_notepad_with_retry(max_attempts: int = 3, delay_seconds: float = .2) -> Application:

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            app = Application(backend="uia").start("notepad.exe")
            # Wait for main window
            dlg = app.top_window()
            dlg.wait("ready", timeout=10)
            logging.info("Notepad launched (attempt %d)", attempt)
            return app
        except (ElementNotFoundError, PywinautoTimeoutError, RuntimeError) as exc:
            last_exc = exc
            logging.warning("Notepad launch failed on attempt %d: %s", attempt, exc)
            time.sleep(delay_seconds)
    raise RuntimeError(f"Failed to launch Notepad after {max_attempts} attempts: {last_exc} the app is not installed or not in the path")


def type_text_into_notepad(app: Application, text: str) -> None:

    dlg = app.top_window()
    dlg.wait("ready", timeout=10)
    # Focus edit area and type text
    try:
        edit = dlg.child_window(control_type="Edit").wrapper_object()
        edit.set_edit_text("")
        edit.type_keys(text, with_spaces=True, with_newlines=True, pause=0.01)
    except (ElementNotFoundError, PywinautoTimeoutError) as exc:
        # Fallback to sending keys directly to the window
        logging.warning("Edit control not found, falling back to send_keys: %s", exc)
        dlg.set_focus()
        send_keys(text, with_spaces=True, with_newlines=True, pause=0.01)


def save_notepad_content(app: Application, full_path: str) -> None:

    # Ensure directory exists and old file is removed to avoid overwrite prompts
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass

    # Keystroke-first approach with basic retry for robustness
    def _save_via_keystrokes():
        # 1) Open Save dialog
        send_keys("^s")
        time.sleep(0.5)
        # 2) Type full path and confirm
        send_keys(full_path, with_spaces=True)
        time.sleep(0.5)
        send_keys("{ENTER}")
        # 3) If an overwrite confirmation appears, send Alt+Y (Yes)
        time.sleep(0.5)
        send_keys("%y")
        # 4) Brief wait to allow write to complete
        time.sleep(0.5)

    try:
        _save_via_keystrokes()
    except Exception as exc:
        logging.warning("Keystroke save failed (%s). Retrying once...", exc)
        time.sleep(0.5)
        try:
            _save_via_keystrokes()
        except Exception as exc2:
            logging.error("Keystroke save failed on retry: %s", exc2)
            raise


def close_notepad(app: Application) -> None:
    print("Closing Notepad...")
    try:
        app.window(title_re=".*Notepad.*").close()

    except Exception as exc:
        logging.warning("Failed to close Notepad cleanly: %s", exc)


def process_post(output_dir: str, post: Dict) -> None:

    post_id = post.get("id", "unknown")
    text = build_blog_text(post)
    filename = f"post {post_id}.txt"
    full_path = os.path.join(output_dir, filename)

    app = launch_notepad_with_retry()
    try:
        type_text_into_notepad(app, text)
        save_notepad_content(app, full_path)
        logging.info("Saved: %s", full_path)
    finally:
        close_notepad(app)


def main() -> int:

    configure_logging()
    try:
        output_dir = ensure_output_dir()
        posts = fetch_posts(limit=10)
        for post in posts:
            try:
                process_post(output_dir, post)
            except Exception as exc:
                logging.error("Failed to process post %s: %s", post.get("id"), exc)
                # Continue with next post
                continue
        logging.info("Completed generating %d posts in %s", len(posts), output_dir)
        return 0
    except Exception as exc:
        logging.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())


