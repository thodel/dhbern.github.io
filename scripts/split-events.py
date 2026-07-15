"""Pre-render script: split events into upcoming and past YAML listing files."""

from datetime import date, datetime
from pathlib import Path

import yaml

CONTENT_DIR = Path("content")
OUTPUT_DIR = Path(".")
TODAY = date.today()


def parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a .qmd file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return yaml.safe_load("".join(lines[1:i]))

    return None
DATE_FORMAT = "%Y.%m.%d"  # dotted YYYY.MM.DD is the site-wide date format


def _parse_date(value) -> date | None:
    """Parse a date given as a date object or a YYYY.MM.DD / YYYY-MM-DD string."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for parser in (
            lambda v: datetime.strptime(v, DATE_FORMAT).date(),
            date.fromisoformat,
        ):
            try:
                return parser(value)
            except ValueError:
                continue
    return None


def _format_date(value: date) -> str:
    """Render a date object in the site-wide dotted format."""
    return value.strftime(DATE_FORMAT)


def _flatten_author(author) -> str:
    """Convert author field (string, dict, or list) to a plain string."""
    if isinstance(author, str):
        return author
    if isinstance(author, dict):
        return author.get("name", "")
    if isinstance(author, list):
        names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in author]
        return ", ".join(n for n in names if n)
    return str(author)


def collect_events() -> list[tuple[date, dict]]:
    """Walk content/ for event .qmd files and return (event_date, item) tuples."""
    events: list[tuple[date, dict]] = []
    for qmd in CONTENT_DIR.rglob("*.qmd"):
        fm = parse_frontmatter(qmd)
        if fm is None:
            continue
        categories = fm.get("categories", [])
        if isinstance(categories, str):
            categories = [categories]
        if "Event" not in categories:
            continue

        event_date = _parse_date(fm.get("event-date") or fm.get("date"))
        if event_date is None:
            continue  # Skip events with missing or invalid date format

        # Fall back to the event date when no separate publication date is set
        pub_date = _parse_date(fm.get("date")) or event_date

        # Build path relative to content/ with a POSIX-style .html output path
        rel_path = qmd.relative_to(CONTENT_DIR.parent).with_suffix(".html").as_posix()

        item = {
            "title": fm.get("title", ""),
            "event-date": _format_date(event_date),
            "date": _format_date(pub_date),
            "author": _flatten_author(fm.get("author", "")),
            "location": fm.get("location", ""),
            "categories": categories,
            "path": rel_path,
        }
        if fm.get("subtitle"):
            item["subtitle"] = fm["subtitle"]

        events.append((event_date, item))

    return events


def main() -> None:
    events = collect_events()

    upcoming = sorted(
        [item for d, item in events if d >= TODAY],
        key=lambda x: x["event-date"],
    )
    past = sorted(
        [item for d, item in events if d < TODAY],
        key=lambda x: x["event-date"],
        reverse=True,
    )

    with open(OUTPUT_DIR / "upcoming-events.yml", "w", encoding="utf-8") as f:
        yaml.dump(upcoming, f, default_flow_style=False, allow_unicode=True)

    with open(OUTPUT_DIR / "past-events.yml", "w", encoding="utf-8") as f:
        yaml.dump(past, f, default_flow_style=False, allow_unicode=True)

    print(f"Events split: {len(upcoming)} upcoming, {len(past)} past (as of {TODAY})")


if __name__ == "__main__":
    main()
