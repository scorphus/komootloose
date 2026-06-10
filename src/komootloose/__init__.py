"""Export komoot tours as GPX from the command line.

Usage:
    komootloose TOUR [TOUR ...]
    komootloose 123456
    komootloose https://www.komoot.com/tour/123456
    komootloose https://www.komoot.com/smarttour/123456 -o route.gpx

TOUR is a numeric tour ID or a komoot tour/smarttour URL.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.komoot.de/v007/tours"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
SET_PROPS_RE = re.compile(r'kmtBoot\.setProps\("((?:[^"\\]|\\.)*)"\)')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def coords_to_gpx(coords):
    points = "\n".join(
        f'<rtept lat="{c["lat"]}" lon="{c["lng"]}"><ele>{c["alt"]}</ele></rtept>'
        for c in coords
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<gpx version="1.1" creator="komootloose" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata></metadata>
  <rte>
  {points}
  </rte>
</gpx>"""


def sanitize_filename(name):
    return re.sub(r"\s+", " ", re.sub(r'[<>:"/\\|?*]+', "", name)).strip()


def tour_from_api(tour_id, share_token=None):
    query = f"?share_token={share_token}" if share_token else ""
    tour = json.loads(fetch(f"{API_BASE}/{tour_id}{query}"))
    coords = json.loads(fetch(f"{API_BASE}/{tour_id}/coordinates{query}"))
    return tour.get("name", "route"), coords["items"]


def tour_from_page(url):
    html = fetch(url)
    match = SET_PROPS_RE.search(html)
    if not match:
        raise ValueError(f"could not find tour data in page: {url}")
    data = json.loads(json.loads(f'"{match.group(1)}"'))
    tour = data["page"]["_embedded"]["tour"]
    return tour.get("name", "route"), tour["_embedded"]["coordinates"]["items"]


def export(target):
    if re.fullmatch(r"\d+", target):
        return tour_from_api(target)
    match = re.search(r"/tour/(\d+)", target)
    if match:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(target).query)
        share_token = query.get("share_token", [None])[0]
        return tour_from_api(match.group(1), share_token)
    if "://" in target:
        return tour_from_page(target)
    raise ValueError(f"not a tour ID or komoot URL: {target}")


def main():
    parser = argparse.ArgumentParser(
        description="Export public komoot tours as GPX files."
    )
    parser.add_argument(
        "tours", nargs="+", metavar="TOUR", help="tour ID or komoot tour/smarttour URL"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output file ('-' for stdout); default is '<tour name>.gpx'",
    )
    args = parser.parse_args()

    if args.output and len(args.tours) > 1:
        parser.error("-o/--output only works with a single tour")

    status = 0
    for target in args.tours:
        try:
            name, coords = export(target)
        except (urllib.error.URLError, ValueError, KeyError) as err:
            print(f"error: {target}: {err}", file=sys.stderr)
            status = 1
            continue
        gpx = coords_to_gpx(coords)
        if args.output == "-":
            print(gpx)
        else:
            filename = args.output or sanitize_filename(name) + ".gpx"
            with open(filename, "w", encoding="utf-8") as fp:
                fp.write(gpx)
            print(f"{target} -> {filename}")
    return status


if __name__ == "__main__":
    sys.exit(main())
