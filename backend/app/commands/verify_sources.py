import argparse
import csv
import hashlib
import mimetypes
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = REPOSITORY_ROOT / "docs/sources/source-inventory.csv"
DEFAULT_CACHE = REPOSITORY_ROOT / "var/cms-sources"
DEFAULT_MANIFEST = REPOSITORY_ROOT / "docs/sources/source-revisions.csv"
USER_AGENT = "CMS-Quality-Intelligence-source-verification/0.1"

MANIFEST_FIELDS = (
    "source_id",
    "official_url",
    "retrieved_at",
    "final_url",
    "http_status",
    "mime_type",
    "byte_length",
    "sha256",
    "cache_path",
    "verification_state",
    "error",
)


@dataclass(frozen=True)
class DownloadResult:
    source_id: str
    official_url: str
    retrieved_at: str
    final_url: str
    http_status: str
    mime_type: str
    byte_length: str
    sha256: str
    cache_path: str
    verification_state: str
    error: str


def load_inventory(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as inventory_file:
        rows = list(csv.DictReader(inventory_file))
    source_ids = [row["source_id"] for row in rows]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Source inventory contains duplicate source_id values.")
    return rows


def _extension(url: str, mime_type: str) -> str:
    suffix = Path(unquote(urlparse(url).path)).suffix.lower()
    if suffix in {".csv", ".html", ".htm", ".pdf", ".xlsx", ".zip"}:
        return ".html" if suffix == ".htm" else suffix
    guessed = mimetypes.guess_extension(mime_type.split(";", maxsplit=1)[0].strip())
    return guessed or ".bin"


def _relative_cache_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPOSITORY_ROOT))
    except ValueError:
        return str(path)


def download_source(row: dict[str, str], cache_dir: Path) -> DownloadResult:
    source_id = row["source_id"]
    official_url = row["official_url"]
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    request = Request(official_url, headers={"User-Agent": USER_AGENT})
    temporary_path: Path | None = None

    try:
        with urlopen(request, timeout=120) as response:  # noqa: S310 - vetted inventory URLs
            mime_type = response.headers.get_content_type()
            extension = _extension(response.geturl(), mime_type)
            destination = cache_dir / f"{source_id}{extension}"
            cache_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            byte_length = 0
            with tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as temporary_file:
                temporary_path = Path(temporary_file.name)
                while chunk := response.read(1024 * 1024):
                    temporary_file.write(chunk)
                    digest.update(chunk)
                    byte_length += len(chunk)
            os.replace(temporary_path, destination)
            temporary_path = None
            return DownloadResult(
                source_id=source_id,
                official_url=official_url,
                retrieved_at=retrieved_at,
                final_url=response.geturl(),
                http_status=str(response.status),
                mime_type=mime_type,
                byte_length=str(byte_length),
                sha256=digest.hexdigest(),
                cache_path=_relative_cache_path(destination),
                verification_state="downloaded_unreviewed",
                error="",
            )
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        return DownloadResult(
            source_id=source_id,
            official_url=official_url,
            retrieved_at=retrieved_at,
            final_url="",
            http_status=str(error.code) if isinstance(error, HTTPError) else "",
            mime_type="",
            byte_length="",
            sha256="",
            cache_path="",
            verification_state="download_failed",
            error=str(error),
        )


def write_manifest(results: list[DownloadResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(manifest_file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download inventoried CMS sources and record immutable SHA-256 hashes."
    )
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        help="Download only this source ID; repeat to select multiple sources.",
    )
    args = parser.parse_args()

    rows = load_inventory(args.inventory)
    if args.source_ids:
        requested = set(args.source_ids)
        known = {row["source_id"] for row in rows}
        unknown = requested - known
        if unknown:
            parser.error(f"Unknown source IDs: {', '.join(sorted(unknown))}")
        rows = [row for row in rows if row["source_id"] in requested]

    results = []
    for row in rows:
        print(f"Retrieving {row['source_id']}...")
        result = download_source(row, args.cache_dir)
        results.append(result)
        print(f"  {result.verification_state}: {result.sha256 or result.error}")

    write_manifest(results, args.manifest)
    failures = [result for result in results if result.verification_state == "download_failed"]
    print(f"Wrote {len(results)} revisions to {args.manifest}")
    if failures:
        raise SystemExit(f"{len(failures)} source downloads failed; inspect the manifest.")


if __name__ == "__main__":
    main()
