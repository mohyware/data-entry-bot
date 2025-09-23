import os
import time
import sys
import logging
from typing import List, Dict

import requests
from pywinauto.application import Application, ProcessNotFoundError, AppStartError
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


def launch_notepad_with_retry(max_attempts: int = 3, delay_seconds: float = .2) -> Application:

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            app = Application(backend="uia").start("notepad.exe")

            time.sleep(0.1)  # for the new notepad
            app.connect(path="notepad.exe")
            
            logging.info("Notepad launched (attempt %d)", attempt)
            return app
        except AppStartError:
            raise AppStartError
        except (ElementNotFoundError, PywinautoTimeoutError, RuntimeError) as exc:
            last_exc = exc
            logging.warning("Notepad launch failed on attempt %d: %s", attempt, exc)
            time.sleep(delay_seconds)
    raise RuntimeError(f"Failed to launch Notepad after {max_attempts} attempts: {last_exc}")


def type_text_into_notepad(app: Application, text: str) -> None:

    dlg = app.top_window()
    dlg.wait("ready", timeout=3)
    # Focus edit area and type text
    try:
        dlg.set_focus()
        time.sleep(0.1)
        send_keys('^a{DEL}')  # CTRL+A + Delete to clear existing text
        time.sleep(0.1)
        send_keys(text, with_spaces=True, with_newlines=True, pause=0.05) # slow cause the new notepad messes up with the speed
        
    except (ElementNotFoundError, PywinautoTimeoutError) as exc:
        logging.warning("failed to type text into notepad: %s", exc)

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
        send_keys("^+s")  # ^ = Ctrl, + = Shift // work for both new and old notepad
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
    body = post.get("body", "")
    filename = f"post {post_id}.txt"
    full_path = os.path.join(output_dir, filename)

    app = launch_notepad_with_retry()
    try:
        type_text_into_notepad(app, body)
        save_notepad_content(app, full_path)
        logging.info("Saved: %s", full_path)
    finally:
        close_notepad(app)

def close_all_open_notepads() -> None:
    """Close all currently running Notepad windows."""
    try:
        apps = Application(backend="uia").connect(path="notepad.exe")
        if hasattr(apps, 'windows'):
            for dlg in apps.windows():
                try:
                    dlg.close()
                    time.sleep(0.1)  
                except Exception as exc:
                    logging.warning("Failed to close a Notepad window: %s", exc)
    except Exception:
        logging.info("No Notepad running")
        pass

def main() -> int:

    configure_logging()
    try:
        output_dir = ensure_output_dir()
        posts = fetch_posts(limit=10)
        close_all_open_notepads()
        for post in posts:
            try:
                process_post(output_dir, post)
            except AppStartError as exc:
                logging.error("Notepad is not installed or not in the path")
                return 1
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


