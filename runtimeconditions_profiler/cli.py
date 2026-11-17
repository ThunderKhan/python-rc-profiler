from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from importlib import metadata
from pathlib import Path

from .errors import RuntimeConditionsError
from .profile.writer import ProfileYamlWriter
from .project.installed import InstalledBindingDiscovery
from .project.verify import InstalledBindingVerifier, VerifiedBindingSet
from .profile.generated import GeneratedBindingExtractor
from .profile.semantic import CORE_VERSION, GeneratedProfileValidator

NAME = "runtimeconditions-python-profiler"
COMMANDS = ("generate", "verify-bindings")


def version() -> str:
    try:
        return metadata.version("runtimeconditions-profiler")
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--version"]:
        # The rc command asks for this to see which core profile schema the add-on emits.
        if "--json" in argv[1:]:
            print(json.dumps({"name": NAME, "version": version(), "coreSchemas": [CORE_VERSION]}, separators=(",", ":")))
        else:
            print(version())
        return 0
    if argv[:1] and argv[0] in COMMANDS:
        # The profile prefix is optional, so rc can pass the subcommand straight through.
        argv = ["profile", *argv]
    parser = argparse.ArgumentParser(prog=NAME)
    subparsers = parser.add_subparsers(dest="command", required=True)

    profile = subparsers.add_parser("profile")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_generate = profile_commands.add_parser("generate")
    profile_generate.add_argument("--project", default=".")
    profile_generate.add_argument("--name", required=True)
    profile_generate.add_argument("--workload-uri", required=True)
    profile_generate.add_argument("--workload-version")
    profile_generate.add_argument("--out")
    profile_verify = profile_commands.add_parser(
        "verify-bindings",
        help="verify installed generated bindings without running application or binding code",
    )
    profile_verify.add_argument("--project", default=".")
    profile_verify.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    command = args.command
    try:
        if command == "profile" and args.profile_command == "generate":
            return run_profile_generate(args)
        if command == "profile" and args.profile_command == "verify-bindings":
            return run_profile_verify_bindings(args)
    except RuntimeConditionsError as exc:
        print(f"runtimeconditions: {exc}", file=sys.stderr)
        return 1
    return 0


def run_profile_generate(args: argparse.Namespace) -> int:
    verified = verified_installed_bindings(Path(args.project))
    extracted = GeneratedBindingExtractor(verified).extract(Path(args.project))
    profile = GeneratedProfileValidator(verified).build(
        extracted, args.name, args.workload_uri, args.workload_version,
    )
    yaml_text = ProfileYamlWriter.write(profile)
    if args.out:
        destination = Path(args.out)
        temporary: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(yaml_text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        except OSError as exc:
            raise RuntimeConditionsError(f"cannot write profile {destination}: {exc}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    else:
        print(yaml_text, end="")
    return 0


def verified_installed_bindings(project: Path) -> VerifiedBindingSet:
    discovery = InstalledBindingDiscovery().discover(project)
    return InstalledBindingVerifier().verify(discovery)


def run_profile_verify_bindings(args: argparse.Namespace) -> int:
    verified = verified_installed_bindings(Path(args.project))
    direct = {item.installed.distribution for item in verified.imported_packages}
    packages = [
        {
            "distribution": item.installed.distribution,
            "direct": item.installed.distribution in direct,
            "version": item.installed.version,
            "importPackage": item.installed.import_package,
            "extensionId": item.model["rootExtension"]["id"],
            "extensionVersion": item.model["rootExtension"]["version"],
            "modelSha256": item.model["metadata"]["semanticSha256"],
        }
        for item in verified.packages
    ]
    if args.json:
        print(json.dumps({"packages": packages}, sort_keys=True))
    else:
        for item in packages:
            marker = "" if item["direct"] else " (dependency)"
            print(f"verified {item['distribution']}=={item['version']} ({item['importPackage']}){marker}")
    return 0


