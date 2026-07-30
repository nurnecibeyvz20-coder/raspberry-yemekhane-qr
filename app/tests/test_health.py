from pathlib import Path

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_templates_directory_is_absolute_and_exists():
    from app.deps import templates
    search = templates.env.loader.searchpath[0]
    p = Path(search)
    assert p.is_absolute(), f"templates dir is not absolute: {search}"
    assert p.exists(), f"templates dir does not exist: {search}"

def test_static_directory_is_absolute_and_exists():
    from app.main import app
    mount = next(r for r in app.routes if getattr(r, "name", None) == "static")
    directory = mount.app.directory
    p = Path(directory)
    assert p.is_absolute(), f"static dir is not absolute: {directory}"
    assert p.exists(), f"static dir does not exist: {directory}"
