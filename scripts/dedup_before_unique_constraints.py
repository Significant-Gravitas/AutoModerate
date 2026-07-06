"""One-shot data-migration helper: dedup APIUser and ProjectMember rows so
the new unique constraints can be added cleanly.

Background
----------
AutoModerate recently added two uniqueness invariants:

    APIUser      UNIQUE (project_id, external_user_id)
    ProjectMember UNIQUE (project_id, user_id)

Databases that existed before this change can legitimately contain duplicate
rows (race-winners from check-then-insert patterns). Alembic / SQLAlchemy
will refuse to add the UNIQUE constraint while duplicates exist, so run this
script once before you bring up the app with the new models.

Usage
-----
    # dry run — prints what would be merged
    python scripts/dedup_before_unique_constraints.py

    # actually apply (commits)
    python scripts/dedup_before_unique_constraints.py --apply

Strategy
--------
Keep the oldest row of each duplicate group (by created_at / id) as the
winner, repoint any foreign keys from the losers onto the winner, merge
counters by summing them, then delete the losers.
"""
import argparse
import os
import sys
from collections import defaultdict

# Make the project importable whether you run this from the repo root or from
# inside scripts/.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app, db  # noqa: E402
from app.models.api_user import APIUser  # noqa: E402
from app.models.content import Content  # noqa: E402
from app.models.project import ProjectMember  # noqa: E402


def _group_duplicates_api_users():
    """Returns {(project_id, external_user_id): [APIUser, ...sorted oldest first]}
    for groups with more than one row."""
    groups = defaultdict(list)
    for row in APIUser.query.all():
        groups[(row.project_id, row.external_user_id)].append(row)
    return {key: sorted(rows, key=lambda r: (r.created_at or r.first_seen, r.id))
            for key, rows in groups.items() if len(rows) > 1}


def _group_duplicates_memberships():
    groups = defaultdict(list)
    for row in ProjectMember.query.all():
        groups[(row.project_id, row.user_id)].append(row)
    return {key: sorted(rows, key=lambda r: (r.joined_at, r.id))
            for key, rows in groups.items() if len(rows) > 1}


def dedup_api_users(apply: bool) -> int:
    groups = _group_duplicates_api_users()
    if not groups:
        print("api_users: no duplicates found")
        return 0

    merged = 0
    for (project_id, ext_id), rows in groups.items():
        winner, losers = rows[0], rows[1:]
        loser_ids = [r.id for r in losers]
        print(f"api_users: merging {len(losers)} duplicate(s) of "
              f"(project_id={project_id}, external_user_id={ext_id}) -> "
              f"keeping {winner.id}")

        if apply:
            # Repoint content rows at the winner
            Content.query.filter(Content.api_user_id.in_(loser_ids)).update(
                {Content.api_user_id: winner.id}, synchronize_session=False)

            # Sum counters from losers onto the winner
            for loser in losers:
                winner.total_requests += loser.total_requests or 0
                winner.approved_count += loser.approved_count or 0
                winner.rejected_count += loser.rejected_count or 0
                winner.flagged_count += loser.flagged_count or 0
                if loser.last_seen and (not winner.last_seen or loser.last_seen > winner.last_seen):
                    winner.last_seen = loser.last_seen
                if loser.first_seen and (not winner.first_seen or loser.first_seen < winner.first_seen):
                    winner.first_seen = loser.first_seen

            # Delete losers
            APIUser.query.filter(APIUser.id.in_(loser_ids)).delete(
                synchronize_session=False)

        merged += len(losers)

    if apply:
        db.session.commit()
    return merged


def dedup_memberships(apply: bool) -> int:
    groups = _group_duplicates_memberships()
    if not groups:
        print("project_members: no duplicates found")
        return 0

    merged = 0
    for (project_id, user_id), rows in groups.items():
        # Keep the highest-privilege row; tiebreak by oldest.
        role_rank = {'owner': 0, 'admin': 1, 'member': 2}
        rows.sort(key=lambda r: (role_rank.get(r.role, 99), r.joined_at, r.id))
        winner, losers = rows[0], rows[1:]
        loser_ids = [r.id for r in losers]
        print(f"project_members: merging {len(losers)} duplicate(s) of "
              f"(project_id={project_id}, user_id={user_id}) -> "
              f"keeping {winner.id} (role={winner.role})")

        if apply:
            ProjectMember.query.filter(ProjectMember.id.in_(loser_ids)).delete(
                synchronize_session=False)

        merged += len(losers)

    if apply:
        db.session.commit()
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='Actually commit the dedup. Omit for dry-run.')
    args = parser.parse_args()

    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    with app.app_context():
        mode = "APPLY" if args.apply else "DRY RUN"
        print(f"=== dedup_before_unique_constraints.py ({mode}) ===")
        api_user_merged = dedup_api_users(args.apply)
        member_merged = dedup_memberships(args.apply)
        print(f"\nSummary: {api_user_merged} APIUser duplicates + "
              f"{member_merged} ProjectMember duplicates "
              f"{'MERGED' if args.apply else '(dry run, no changes)'}")


if __name__ == '__main__':
    main()
