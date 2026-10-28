"""Prepare the Render preview with public roster data and private review candidates."""

import os

from app.commands.seed_demo import clear_demo_records_in_session
from app.commands.seed_verified import seed_verified_drafts
from app.database import SessionLocal
from app.services.roster_publication import publish_verified_roster_baseline


def _assert_preview_target() -> None:
    if os.getenv("CMSQI_DEPLOYMENT_ENVIRONMENT") != "preview":
        raise RuntimeError(
            "Refusing preview bootstrap outside CMSQI_DEPLOYMENT_ENVIRONMENT=preview."
        )
    if os.getenv("CMSQI_BOOTSTRAP_PREVIEW") != "true":
        raise RuntimeError("Set CMSQI_BOOTSTRAP_PREVIEW=true to bootstrap preview data.")


def main() -> None:
    _assert_preview_target()
    with SessionLocal.begin() as session:
        removed_demo_measures, removed_demo_sources = clear_demo_records_in_session(session)
        measures, roster_versions, variant_versions, candidates = seed_verified_drafts(
            session
        )
        publication = publish_verified_roster_baseline(session)

    print(
        f"Removed {removed_demo_measures} fictional demo measures and "
        f"{removed_demo_sources} fictional demo sources."
    )
    print(
        f"Prepared {measures} measures, {roster_versions} roster versions, "
        f"{variant_versions} private variants, and {candidates} private candidates."
    )
    print(
        f"Published {publication.published_measures} measures, "
        f"{publication.published_memberships} memberships, "
        f"{publication.published_roster_versions} roster versions, and "
        f"{publication.published_source_revisions} source revisions."
    )
    print("Detailed specification variants and candidates remain private.")


if __name__ == "__main__":
    main()
