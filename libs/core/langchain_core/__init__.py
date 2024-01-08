from importlib import metadata
from typing import Sequence

from langchain_core._api import (
    surface_langchain_beta_warnings,
    surface_langchain_deprecation_warnings,
)

try:
    __version__ = metadata.version(__package__)
except metadata.PackageNotFoundError:
    # Case where package metadata is not available.
    __version__ = ""

surface_langchain_deprecation_warnings()
surface_langchain_beta_warnings()


def print_info(*, additional_pkgs: Sequence[str] = tuple()) -> None:
    """Print information about the environment for debugging purposes."""
    import importlib
    import platform
    import sys

    packages = [
        "langchain_core",
        "langchain",
        "langchain_community",
    ] + list(additional_pkgs)

    system_info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "Python Version": sys.version,
    }

    print("System Information")
    print("------------------")
    print("OS: ", system_info["OS"])
    print("OS Version: ", system_info["OS Version"])
    print("Python Version: ", system_info["Python Version"])

    # Print out only langchain packages
    print()
    print("Package Information")
    print("-------------------")

    for pkg in packages:
        try:
            found_package = importlib.util.find_spec(pkg)
        except Exception:
            found_package = None
        if found_package is None:
            print(f"{pkg}: Not Found")
            continue

        # Package version
        try:
            package_version = importlib.metadata.version(pkg)
        except Exception:
            package_version = None

        # Print package with version
        if package_version is not None:
            print(f"{pkg}: {package_version}")
        else:
            print(f"{pkg}: Found")
