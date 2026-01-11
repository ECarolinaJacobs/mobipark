import json
from pathlib import Path

from utils.storage_utils import insert_single_json_to_db

PARKING_SESSION_FOLDER = Path("data/pdata")


def import_parking_sessions():
    if not PARKING_SESSION_FOLDER.exists():
        print(f"Folder not found: {PARKING_SESSION_FOLDER}")
        return

    for file in PARKING_SESSION_FOLDER.iterdir():
        if file.suffix != ".json":
            continue

        print(f"Processing {file.name}")

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for session_id, session_data in data.items():
            if "id" not in session_data:
                session_data["id"] = session_id

            try:
                insert_single_json_to_db("parking_sessions", session_data)
                print(f"Inserted session {session_id}")
            except Exception as e:
                print(f"Failed to insert {session_id}: {e}")

    print("Done importing all parking sessions.")


if __name__ == "__main__":
    import_parking_sessions()


# python -m scripts.insert_parkingsessions_json  run this module once to 
# insert parking sessions json data into the db
