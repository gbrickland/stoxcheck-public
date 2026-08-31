"""Interactively create or reset the ten generic Firebase username/password accounts.

Firebase email/password authentication needs an email-shaped identifier, so the reserved suffix is
an implementation detail. Website users enter a randomly generated username and password.
The generated administrator copy is written to a private CSV and must never be committed.
"""

from __future__ import annotations

import csv
import os
import secrets
import string
from pathlib import Path

import firebase_admin
from firebase_admin import auth


PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "stoxcheck-staging")
ACCOUNT_DOMAIN = "accounts.stoxcheck.invalid"
ACCOUNT_COUNT = 10
PRIVATE_DIR = Path(os.environ.get("STOXCHECK_PRIVATE_DIR", Path(__file__).parent)).resolve()
USERNAME_FILE = PRIVATE_DIR / "account_usernames.private.csv"
CREDENTIAL_FILE = PRIVATE_DIR / "account_credentials.private.csv"


def usernames() -> list[str]:
    """Reuse a private list when resetting accounts; otherwise create ten strong random IDs."""
    if USERNAME_FILE.exists():
        with USERNAME_FILE.open(newline="", encoding="utf-8") as handle:
            values = [row["username"] for row in csv.DictReader(handle)]
        if len(values) != ACCOUNT_COUNT or len(set(values)) != ACCOUNT_COUNT:
            raise SystemExit(f"Expected ten unique usernames in {USERNAME_FILE}")
        return values
    alphabet = string.ascii_lowercase + string.digits
    values: list[str] = []
    while len(values) < ACCOUNT_COUNT:
        candidate = "member-" + "".join(secrets.choice(alphabet) for _ in range(12))
        if candidate not in values:
            values.append(candidate)
    with USERNAME_FILE.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["account", "username"])
        writer.writeheader()
        writer.writerows({"account": number, "username": value}
                         for number, value in enumerate(values, 1))
    return values


def random_password() -> str:
    """Generate a readable strong password with upper/lowercase, numbers and symbols."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    value = [secrets.choice(string.ascii_uppercase), secrets.choice(string.ascii_lowercase),
             secrets.choice(string.digits), secrets.choice("!@#$%")]
    value += [secrets.choice(alphabet) for _ in range(16)]
    secrets.SystemRandom().shuffle(value)
    return "".join(value)


def main() -> None:
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
    if CREDENTIAL_FILE.exists():
        raise SystemExit(f"Refusing to overwrite existing credentials: {CREDENTIAL_FILE}")
    results = []
    for number, username in enumerate(usernames(), 1):
        password = random_password()
        email = f"{username}@{ACCOUNT_DOMAIN}"
        try:
            user = auth.get_user_by_email(email)
            auth.update_user(user.uid, password=password, disabled=False, display_name=username)
            action = "reset"
        except auth.UserNotFoundError:
            user = auth.create_user(email=email, password=password, email_verified=True,
                                    display_name=username)
            action = "created"
        # Requiring this claim keeps accounts created outside this script out of Stoxcheck.
        auth.set_custom_user_claims(user.uid, {"stoxcheck_access": True, "stoxcheck_username": username})
        results.append({"account": number, "username": username, "password": password,
                        "firebase_uid": user.uid, "action": action})

    with CREDENTIAL_FILE.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader(); writer.writerows(results)
    print(f"Provisioned {ACCOUNT_COUNT} accounts in Firebase project {PROJECT_ID}.")
    print(f"Private login list written to {CREDENTIAL_FILE} (ignored by Git).")


if __name__ == "__main__":
    main()
