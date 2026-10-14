"""Reset the working database: copy the pristine data/campus_customs.db over data/campus_customs_new.db.

Wipes approvals, drafts, notes and payments made by the team; the audit trail is kept.
    python backend/reset_db.py
"""

import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

if __name__ == "__main__":
    shutil.copyfile(DATA / "campus_customs.db", DATA / "campus_customs_new.db")
    print(f"Reset {DATA / 'campus_customs_new.db'} from campus_customs.db")
