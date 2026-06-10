import json

import pytest

import komootloose

COORDS = [
    {"lat": 52.1, "lng": 9.9, "alt": 153.8, "t": 0},
    {"lat": 52.2, "lng": 9.8, "alt": 154.2, "t": 4000},
]


def fake_fetch(responses):
    def fetch(url):
        for fragment, body in responses.items():
            if fragment in url:
                return body
        raise AssertionError(f"unexpected fetch: {url}")

    return fetch


def test_coords_to_gpx():
    gpx = komootloose.coords_to_gpx(COORDS)
    assert gpx.startswith('<?xml version="1.0"')
    assert 'creator="komootloose"' in gpx
    assert '<rtept lat="52.1" lon="9.9"><ele>153.8</ele></rtept>' in gpx
    assert gpx.count("<rtept") == 2


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Simple Tour", "Simple Tour"),
        ('a<>:"/\\|?*b', "ab"),
        ("  spaced \t out  ", "spaced out"),
    ],
)
def test_sanitize_filename(name, expected):
    assert komootloose.sanitize_filename(name) == expected


def test_export_by_id(monkeypatch):
    monkeypatch.setattr(
        komootloose,
        "fetch",
        fake_fetch(
            {
                "/coordinates": json.dumps({"items": COORDS}),
                "/tours/123456": json.dumps({"name": "My Tour"}),
            }
        ),
    )
    name, coords = komootloose.export("123456")
    assert name == "My Tour"
    assert coords == COORDS


def test_export_by_url_forwards_share_token(monkeypatch):
    urls = []

    def fetch(url):
        urls.append(url)
        if "/coordinates" in url:
            return json.dumps({"items": COORDS})
        return json.dumps({"name": "Shared Tour"})

    monkeypatch.setattr(komootloose, "fetch", fetch)
    name, _ = komootloose.export(
        "https://www.komoot.com/tour/42?ref=itd&share_token=abc123"
    )
    assert name == "Shared Tour"
    assert urls == [
        "https://api.komoot.de/v007/tours/42?share_token=abc123",
        "https://api.komoot.de/v007/tours/42/coordinates?share_token=abc123",
    ]


def test_export_by_url_without_share_token(monkeypatch):
    urls = []

    def fetch(url):
        urls.append(url)
        if "/coordinates" in url:
            return json.dumps({"items": COORDS})
        return json.dumps({"name": "Public Tour"})

    monkeypatch.setattr(komootloose, "fetch", fetch)
    komootloose.export("https://www.komoot.com/tour/42")
    assert urls == [
        "https://api.komoot.de/v007/tours/42",
        "https://api.komoot.de/v007/tours/42/coordinates",
    ]


def test_export_smarttour_url_parses_page(monkeypatch):
    page_data = {
        "page": {"_embedded": {"tour": {"name": "Smart Tour", "_embedded": {"coordinates": {"items": COORDS}}}}}
    }
    escaped = json.dumps(json.dumps(page_data))[1:-1]
    html = f'<script>kmtBoot.setProps("{escaped}");</script>'
    monkeypatch.setattr(komootloose, "fetch", lambda url: html)
    name, coords = komootloose.export("https://www.komoot.com/smarttour/99")
    assert name == "Smart Tour"
    assert coords == COORDS


def test_export_page_without_data_raises(monkeypatch):
    monkeypatch.setattr(komootloose, "fetch", lambda url: "<html></html>")
    with pytest.raises(ValueError, match="could not find tour data"):
        komootloose.export("https://www.komoot.com/smarttour/99")


def test_export_rejects_garbage():
    with pytest.raises(ValueError, match="not a tour ID or komoot URL"):
        komootloose.export("notatour")


def test_main_writes_file(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        komootloose,
        "fetch",
        fake_fetch(
            {
                "/coordinates": json.dumps({"items": COORDS}),
                "/tours/1": json.dumps({"name": "My: Tour?"}),
            }
        ),
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["komootloose", "1"])
    assert komootloose.main() == 0
    out = tmp_path / "My Tour.gpx"
    assert out.exists()
    assert "<rtept" in out.read_text()


def test_main_stdout(monkeypatch, capsys):
    monkeypatch.setattr(
        komootloose,
        "fetch",
        fake_fetch(
            {
                "/coordinates": json.dumps({"items": COORDS}),
                "/tours/1": json.dumps({"name": "My Tour"}),
            }
        ),
    )
    monkeypatch.setattr("sys.argv", ["komootloose", "1", "-o", "-"])
    assert komootloose.main() == 0
    assert capsys.readouterr().out.startswith('<?xml version="1.0"')


def test_main_reports_errors(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["komootloose", "notatour"])
    assert komootloose.main() == 1
    assert "not a tour ID" in capsys.readouterr().err


def test_main_rejects_output_with_multiple_tours(monkeypatch):
    monkeypatch.setattr("sys.argv", ["komootloose", "1", "2", "-o", "x.gpx"])
    with pytest.raises(SystemExit):
        komootloose.main()
