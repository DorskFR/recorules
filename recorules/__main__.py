"""Main entry point for recorules."""

import sys
from getpass import getpass

from recorules.app import RecoRulesApp
from recorules.config import DEFAULT_CONFIG_PATH, Config


def configure() -> None:
    """Interactive configuration setup."""
    # Using sys.stdout.write for interactive prompts is allowed
    sys.stdout.write("RecoRules Configuration\n")
    sys.stdout.write("=" * 40 + "\n")
    recoru_contract_id = input("Recoru Contract ID: ")
    recoru_auth_id = input("Recoru Auth ID: ")
    recoru_password = getpass("Recoru Password: ")

    config = Config(
        recoru_contract_id=recoru_contract_id,
        recoru_auth_id=recoru_auth_id,
        recoru_password=recoru_password,
    )
    config.save()
    sys.stdout.write("\n✓ Configuration saved successfully!\n")
    sys.stdout.write(f"Config file: {DEFAULT_CONFIG_PATH}\n")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        configure()
        return

    # Check if config exists
    config = Config.from_env() or Config.load()
    if not config:
        configure()

    # Run the TUI
    app = RecoRulesApp()
    app.run()


if __name__ == "__main__":
    main()
