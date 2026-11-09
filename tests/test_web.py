import re
from pathlib import Path

from fastapi.testclient import TestClient

WEB_DIR = Path(__file__).resolve().parents[1] / "src" / "research_graph" / "web"


def test_root_redirects_to_ui(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/"


def test_ui_serves_page_and_assets(client: TestClient) -> None:
    page = client.get("/ui/")
    assert page.status_code == 200
    assert "Прогноз виральности" in page.text

    script = client.get("/ui/app.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]

    styles = client.get("/ui/styles.css")
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")


def test_missing_static_file_uses_common_error_format(client: TestClient) -> None:
    response = client.get("/ui/missing.js")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_js_selectors_exist_in_html() -> None:
    """Контракт фронтенда: все id и имена полей, которые использует app.js, есть в HTML."""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")

    used_ids = set(re.findall(r'\$\("#([\w-]+)"\)', script))
    html_ids = set(re.findall(r'id="([\w-]+)"', html))
    assert used_ids <= html_ids, used_ids - html_ids

    used_names = set(re.findall(r"elements\.(\w+)", script))
    html_names = set(re.findall(r'name="(\w+)"', html))
    assert used_names <= html_names, used_names - html_names

    tabs = set(re.findall(r'data-tab="(\w+)"', html))
    panels = set(re.findall(r'data-panel="(\w+)"', html))
    assert tabs == panels


def test_predict_form_fields_are_model_features() -> None:
    from research_graph.ml.features import FEATURES

    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    block = script.split("const NUMBER_FIELDS", 1)[1].split("const ADVICE", 1)[0]
    names = re.findall(r'\["(\w+)", "', block)
    assert names
    assert set(names) <= set(FEATURES)
