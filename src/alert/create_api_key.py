import argparse

from alert.core.application import auth


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", type=str)
    args = parser.parse_args()
    username: str = args.username

    print("Creating api-key for user ", username)
    api_key = auth.create(username)
    print("Generated API-Key: ", api_key)


if __name__ == "__main__":
    main()
