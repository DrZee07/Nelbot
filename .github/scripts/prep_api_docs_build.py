#!/usr/bin/env python
"""Script to sync libraries from various repositories into the main langchain repository."""

import os
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any


def load_packages_yaml() -> Dict[str, Any]:
    """Load and parse the packages.yml file."""
    with open("langchain/libs/packages.yml", "r") as f:
        all_packages = yaml.safe_load(f)

    return {k: v for k, v in all_packages.items() if k["repo"]}


def get_target_dir(package_name: str) -> Path:
    """Get the target directory for a given package."""
    package_name_short = package_name.replace("langchain-", "")
    base_path = Path("langchain/libs")
    if package_name_short == "experimental":
        return base_path / "experimental"
    return base_path / "partners" / package_name_short


def clean_target_directories(packages: list) -> None:
    """Remove old directories that will be replaced."""
    for package in packages:

        target_dir = get_target_dir(package["name"])
        if target_dir.exists():
            print(f"Removing {target_dir}")
            shutil.rmtree(target_dir)


def move_libraries(packages: list) -> None:
    """Move libraries from their source locations to the target directories."""
    for package in packages:

        repo_name = package["repo"].split("/")[1]
        source_path = package["path"]
        target_dir = get_target_dir(package["name"])

        # Handle root path case
        if source_path == ".":
            source_dir = repo_name
        else:
            source_dir = f"{repo_name}/{source_path}"

        print(f"Moving {source_dir} to {target_dir}")

        # Ensure target directory exists
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        try:
            # Move the directory
            shutil.move(source_dir, target_dir)
        except Exception as e:
            print(f"Error moving {source_dir} to {target_dir}: {e}")


def main():
    """Main function to orchestrate the library sync process."""
    try:
        # Load packages configuration
        package_yaml = load_packages_yaml()
        packages = [
            p
            for p in package_yaml["packages"]
            if not p.get("disabled", False)
            and p["repo"].startswith("langchain-ai/")
            and p["repo"] != "langchain-ai/langchain"
        ]

        # Clean target directories
        clean_target_directories(packages)

        # Move libraries to their new locations
        move_libraries(packages)

        print("Library sync completed successfully!")

    except Exception as e:
        print(f"Error during library sync: {e}")
        raise


if __name__ == "__main__":
    main()
