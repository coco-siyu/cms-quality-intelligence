import getpass
import secrets

from app.auth import hash_admin_password


def main() -> None:
    username = input("Admin username: ").strip()
    if not username:
        raise SystemExit("Admin username cannot be empty.")
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < 12:
        raise SystemExit("Admin password must contain at least 12 characters.")

    print("\nAdd these values to the repository .env file:")
    print(f"CMSQI_ADMIN_USERNAME={username}")
    print(f"CMSQI_ADMIN_PASSWORD_HASH={hash_admin_password(password)}")
    print(f"CMSQI_ADMIN_SESSION_SECRET={secrets.token_urlsafe(48)}")
    print("CMSQI_ADMIN_SESSION_SECURE=false")


if __name__ == "__main__":
    main()
