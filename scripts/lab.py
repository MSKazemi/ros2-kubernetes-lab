#!/usr/bin/env python3
"""One command line for the ROS 2 on Kubernetes lab (stdlib only; Linux, macOS, Windows).

Wraps the commands that are otherwise spread across the READMEs: repository checks,
the ROS 2 Jazzy container image and its smoke test, and the historical Vagrant
cluster. Every command accepts --dry-run, which prints what would be executed.

Start it with the launcher (./lab on Linux/macOS, lab.cmd on Windows) or run
`python scripts/lab.py`. Tab completion: `lab completion --help`.

Exit status: 0 success, 1 a command or check failed (or you declined a prompt),
2 usage error, 3 a prerequisite is missing. Messages are plain ASCII on purpose
so they survive legacy Windows console code pages.
"""

from __future__ import annotations

import argparse
import os
import platform
import shlex
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

if sys.version_info < (3, 8):  # shlex.join; the launchers already prefer a newer interpreter
    print(f"lab: error: Python 3.8 or newer is required (this is {platform.python_version()}).", file=sys.stderr)
    sys.exit(3)

REPO_ROOT = Path(__file__).resolve().parent.parent

IMAGE_TAG = "ros-jazzy-lab:local"
IMAGE_PLATFORM = "linux/amd64"  # the platform the project's CI builds and tests
NODES = ("controlplane", "worker1", "worker2")
# Keep in sync with the `lab_profiles` table in the Vagrantfile:
# (control-plane MB, control-plane vCPUs, each worker MB, each worker vCPUs).
PROFILE_SIZES = {"default": (18240, 14, 6096, 2), "small": (8192, 4, 4096, 2)}
SIZE_VARIABLES = ("LAB_CP_MEMORY_MB", "LAB_CP_CPUS", "LAB_WORKER_MEMORY_MB", "LAB_WORKER_CPUS")

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_PREREQ = 0, 1, 2, 3

INSTALL_HINTS = {
    "docker": "Install Docker Engine (Linux): https://docs.docker.com/engine/install/ "
    "or Docker Desktop (macOS, Windows): https://docs.docker.com/desktop/",
    "vagrant": "Install Vagrant https://developer.hashicorp.com/vagrant/install "
    "and VirtualBox https://www.virtualbox.org/wiki/Downloads",
    "bash": "Install Git for Windows (includes Git Bash): https://git-scm.com/download/win",
    "ruby": "Install Ruby (only needed for the optional Vagrantfile syntax check): "
    "https://www.ruby-lang.org/en/documentation/installation/",
}

_color_out = False
_color_err = False


class PrereqError(Exception):
    """A required external tool is missing."""


# --- output ----------------------------------------------------------------------


def style(text: str, code: str, err: bool = False) -> str:
    """Colour `text` if the stream it will be written to (stdout, or stderr when err) is a terminal."""
    return f"\033[{code}m{text}\033[0m" if (_color_err if err else _color_out) else text


def info(message: str) -> None:
    print(message, file=sys.stderr)


def warn(message: str) -> None:
    print(style("warning: ", "33", err=True) + message, file=sys.stderr)


def error(message: str) -> None:
    print(style("lab: error: ", "31", err=True) + message, file=sys.stderr)


def use_color(no_color_flag: bool, stream) -> bool:
    if no_color_flag or "NO_COLOR" in os.environ or not stream.isatty():
        return False
    if platform.system() == "Windows":
        # Only modern terminals interpret ANSI escapes; classic conhost may not.
        return bool(os.environ.get("WT_SESSION") or os.environ.get("TERM"))
    return True


# --- running external tools ---------------------------------------------------------


def find_windows_bash() -> str | None:
    """Git for Windows' bash. Never the WSL launcher in System32, which would run the
    script inside WSL with Windows paths it cannot resolve."""
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramW6432"),
        os.environ.get("ProgramFiles(x86)"),
    ]
    local = os.environ.get("LOCALAPPDATA")
    candidates = [Path(r) / "Git" / "bin" / "bash.exe" for r in roots if r]
    if local:
        candidates.append(Path(local) / "Programs" / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    found = find_on_windows_path("bash")
    if found and "\\windows\\" not in found.lower():
        return found
    return None


def find_on_windows_path(name: str) -> str | None:
    """Search PATH only. shutil.which also tries the current directory first on Windows, so a
    docker.exe or vagrant.cmd in the folder you run `lab` from could be picked instead."""
    folders = [folder for folder in os.environ.get("PATH", "").split(os.pathsep) if folder]
    extensions = [ext for ext in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if ext]
    suffixes = [""] if os.path.splitext(name)[1] else extensions
    for folder in folders:
        for suffix in suffixes:
            candidate = os.path.join(folder, name + suffix)
            if os.path.isfile(candidate):
                return candidate
    return None


def find_tool(name: str) -> str | None:
    if platform.system() == "Windows":
        return find_windows_bash() if name == "bash" else find_on_windows_path(name)
    return shutil.which(name)


def require(name: str, verbose: bool = False) -> str:
    """Resolve a tool to a full path (needed on Windows for .cmd shims) or raise."""
    if os.path.isabs(name) and os.path.exists(name):
        return name
    path = find_tool(name)
    if not path:
        hint = INSTALL_HINTS.get(name, "")
        raise PrereqError(f"'{name}' was not found on PATH." + (f"\n  {hint}" if hint else ""))
    if verbose:
        info(f"resolved {name} -> {path}")
    return path


def format_cmd(cmd: list[str]) -> str:
    shown = ["python" if part == sys.executable else part for part in cmd]
    if platform.system() == "Windows":
        return subprocess.list2cmdline(shown)
    return shlex.join(shown)


def child_environment(tool: str, env_extra: dict[str, str] | None) -> dict[str, str]:
    env = {**os.environ, **(env_extra or {})}
    if tool == "vagrant":
        # Vagrant reads these before it looks at the working directory. A value left in your
        # shell from another project would send `vagrant destroy` to that project's VMs.
        for name in ("VAGRANT_CWD", "VAGRANT_VAGRANTFILE"):
            stale = os.environ.get(name)
            if stale and not (name == "VAGRANT_CWD" and os.path.realpath(stale) == os.path.realpath(str(REPO_ROOT))):
                warn(f"ignoring {name}={stale}; this command always targets {REPO_ROOT}")
        env["VAGRANT_CWD"] = str(REPO_ROOT)
        env.pop("VAGRANT_VAGRANTFILE", None)
    return env


def run_child(real: list[str], env: dict[str, str], stdin_data: bytes | None) -> int:
    """Run to completion. Unlike subprocess.run this does not SIGKILL the child on Ctrl-C:
    the terminal already sent Ctrl-C to it, and tools such as Vagrant need that first Ctrl-C
    to shut down cleanly. A second Ctrl-C asks it to terminate, a third kills it."""
    proc = subprocess.Popen(real, cwd=str(REPO_ROOT), env=env,
                            stdin=subprocess.PIPE if stdin_data is not None else None)
    interrupts, first = 0, True
    while True:
        try:
            proc.communicate(stdin_data if first else None)
            return proc.returncode
        except KeyboardInterrupt:
            first = False
            interrupts += 1
            if interrupts == 1:
                info("Interrupted: waiting for the command to stop. Press Ctrl-C again to terminate it.")
            elif interrupts == 2:
                proc.terminate()
            else:
                proc.kill()


def run(
    args: argparse.Namespace,
    cmd: list[str],
    env_extra: dict[str, str] | None = None,
    stdin_data: bytes | None = None,
) -> int:
    """Run a command from the repository root; in --dry-run only print it.

    The command line goes to stdout in a dry run (it *is* the output) and to stderr
    otherwise, so piped output of the wrapped tool stays clean. Environment variables are
    described after the command instead of in a shell-specific prefix, because cmd.exe,
    PowerShell and POSIX shells each set them differently.
    """
    line = "$ " + format_cmd(cmd)
    if env_extra:
        line += "   (environment: " + " ".join(f"{k}={v}" for k, v in env_extra.items()) + ")"
    if args.dry_run:
        print(line)
        return EXIT_OK
    info(style(line, "2", err=True))
    real = [require(cmd[0], args.verbose)] + cmd[1:]
    try:
        return run_child(real, child_environment(cmd[0], env_extra), stdin_data)
    except OSError as exc:
        raise PrereqError(f"cannot start '{cmd[0]}': {exc}") from exc


def confirm(args: argparse.Namespace, consequence: str) -> bool:
    """Ask the user to type 'yes'. Refuses (never assumes yes) when not interactive."""
    if args.yes:
        return True
    if args.dry_run:
        info(f"(dry run) would ask for confirmation first: {consequence}")
        return True
    if not sys.stdin.isatty():
        error("this command needs confirmation but there is no terminal; pass --yes to proceed.")
        return False
    try:
        answer = input("Type 'yes' to continue: ")
    except EOFError:
        return False
    return answer.strip().lower() == "yes"


def examples(rows: list[tuple[str, str]]) -> str:
    width = max(len(cmd) for cmd, _ in rows)
    lines = [f"  {cmd:<{width}}  {text}" for cmd, text in rows]
    return "Examples:\n" + "\n".join(lines)


# --- doctor ------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    return run(args, [sys.executable, "scripts/doctor.py"])


# --- check -------------------------------------------------------------------------

PASS, FAIL, SKIPPED = "PASS", "FAIL", "SKIPPED"


def _check_python_script(args: argparse.Namespace, script: str) -> tuple[str, str]:
    return (PASS if run(args, [sys.executable, script]) == 0 else FAIL), ""


def check_preflight(args: argparse.Namespace) -> tuple[str, str]:
    return _check_python_script(args, "scripts/doctor.py")


def check_links(args: argparse.Namespace) -> tuple[str, str]:
    return _check_python_script(args, "scripts/check-markdown-links.py")


def check_site(args: argparse.Namespace) -> tuple[str, str]:
    return _check_python_script(args, "scripts/validate-site.py")


def _check_optional_tool(args: argparse.Namespace, tool: str, cmd: list[str]) -> tuple[str, str]:
    if not args.dry_run and not find_tool(tool):
        return SKIPPED, f"{tool} not found. {INSTALL_HINTS.get(tool, '')}".strip()
    return (PASS if run(args, cmd) == 0 else FAIL), ""


def check_shell(args: argparse.Namespace) -> tuple[str, str]:
    if not args.dry_run and not ((REPO_ROOT / ".git").exists() and find_tool("git")):
        # check-shell.sh validates *tracked* files, so a ZIP download cannot be checked.
        return SKIPPED, "needs a git checkout and git on PATH"
    return _check_optional_tool(args, "bash", ["bash", "scripts/check-shell.sh"])


def check_vagrantfile(args: argparse.Namespace) -> tuple[str, str]:
    return _check_optional_tool(args, "ruby", ["ruby", "-c", "Vagrantfile"])


CHECKS = {
    "preflight": check_preflight,
    "shell": check_shell,
    "links": check_links,
    "site": check_site,
    "vagrantfile": check_vagrantfile,
}


def cmd_check(args: argparse.Namespace) -> int:
    names = list(CHECKS) if args.what == "all" else [args.what]
    results = []
    for name in names:
        info(style(f"== check {name}", "1", err=True))
        status, note = CHECKS[name](args)
        results.append((name, status, note))
    if args.dry_run:
        return EXIT_OK
    print("\nSummary")
    colors = {PASS: "32", FAIL: "31", SKIPPED: "33"}
    for name, status, note in results:
        print(f"  {style(f'{status:<8}', colors[status])} {name}" + (f"  ({note})" if note else ""))
    if any(status == SKIPPED for _, status, _ in results):
        print("SKIPPED means the check did not run; it is not a pass."
              + (" (--strict: counted as a failure.)" if args.strict else " Use --strict to fail on it."))
    failed = any(status == FAIL for _, status, _ in results)
    skipped = any(status == SKIPPED for _, status, _ in results)
    return EXIT_FAIL if failed or (args.strict and skipped) else EXIT_OK


# --- image -------------------------------------------------------------------------


def cmd_image_build(args: argparse.Namespace) -> int:
    cmd = ["docker", "build", "--platform", args.platform]
    if args.pull:
        cmd.append("--pull")
    cmd += ["--file", "ROS2/Dockerfile", "--tag", args.tag, "."]
    return run(args, cmd)


def cmd_image_test(args: argparse.Namespace) -> int:
    script = REPO_ROOT / "scripts" / "test-ros2-image.sh"
    info("Smoke test inside ONE container: ROS 2 Jazzy, demo nodes, stress-ng, local talker/listener.")
    info("It does not exercise Kubernetes, Vagrant or cross-node DDS delivery.")
    if not args.dry_run:
        docker = require("docker", args.verbose)
        try:
            probe = subprocess.run([docker, "image", "inspect", args.tag], capture_output=True,
                                   text=True, errors="replace", check=False)
        except OSError as exc:
            raise PrereqError(f"cannot start 'docker': {exc}") from exc
        if probe.returncode != 0:
            detail = (probe.stderr or "").strip()
            if any(phrase in detail.lower() for phrase in ("no such image", "no such object")):
                error(f"image '{args.tag}' not found locally. Build it first: lab image build")
                return EXIT_FAIL
            first_line = detail.splitlines()[0] if detail else "no error text"
            error(f"Docker could not be queried ({first_line}). Is Docker running?")
            return EXIT_PREREQ
    # Send the script on stdin from Python: no `<` redirection (PowerShell has none) and
    # CRLF from a misconfigured Windows checkout is normalised so bash can run it.
    data = script.read_bytes().replace(b"\r\n", b"\n")
    cmd = ["docker", "run", "--rm", "-i", "--platform", args.platform, args.tag, "bash", "-s"]
    if args.dry_run:
        info("(the script scripts/test-ros2-image.sh would be sent on stdin)")
    rc = run(args, cmd, stdin_data=data)
    if rc == 0 and not args.dry_run:
        info("Passed. Scope: same-container check only.")
    return rc


def cmd_image_shell(args: argparse.Namespace) -> int:
    return run(args, ["docker", "run", "--rm", "-it", "--platform", args.platform, args.tag, "bash"])


# --- cluster -----------------------------------------------------------------------


def is_arm_host() -> bool:
    machine = platform.machine().lower()
    return machine.startswith(("arm", "aarch")) and os.environ.get("LAB_ALLOW_ARM", "").strip() != "1"


def cmd_cluster_status(args: argparse.Namespace) -> int:
    return run(args, ["vagrant", "status"])


def planned_cost(profile: str) -> tuple[int, int, bool]:
    """(total MB, total vCPUs, customised by LAB_* variables) as the Vagrantfile will compute them."""
    if profile not in PROFILE_SIZES:
        raise ValueError(f"LAB_PROFILE must be one of: {', '.join(sorted(PROFILE_SIZES))} (got '{profile}').")
    values, customised = [], False
    for default, name in zip(PROFILE_SIZES[profile], SIZE_VARIABLES):
        raw = os.environ.get(name, "").strip()
        if raw:
            if not (raw.isdigit() and int(raw) > 0):
                raise ValueError(f"{name} must be a positive whole number (got '{raw}').")
            default, customised = int(raw), True
        values.append(default)
    cp_mb, cp_cpus, worker_mb, worker_cpus = values
    return cp_mb + 2 * worker_mb, cp_cpus + 2 * worker_cpus, customised


def cmd_cluster_up(args: argparse.Namespace) -> int:
    if is_arm_host() and not args.dry_run:
        error(
            "this Vagrant lab uses an x86-64 VirtualBox box and cannot run on an Arm host. "
            "Use the container path instead (lab image build, then lab image test) "
            "(see docs/WINDOWS-AND-MAC.md)."
        )
        return EXIT_PREREQ
    profile = args.profile or os.environ.get("LAB_PROFILE", "default").strip().lower()
    try:
        total_mb, total_cpus, customised = planned_cost(profile)
    except ValueError as exc:
        error(str(exc))
        return EXIT_USAGE
    sizes = f"about {round(total_mb / 1024)} GB RAM and {total_cpus} vCPUs in total"
    sizes += " (changed by LAB_* variables)" if customised else ""
    sizes += "; the small profile is not validated end to end" if profile == "small" else ""
    info("HISTORICAL lab: ROS 2 Foxy (end of life), Kubernetes 1.29, Ubuntu 22.04 VMs, Weave Net.")
    info("It is not a validated modern or production deployment, and the first run downloads a lot.")
    info(f"Profile '{profile}': three VMs, {sizes}.")
    if not args.dry_run:
        require("vagrant", args.verbose)  # fail before the prompt, not after typing 'yes'
    if not confirm(args, "this starts three VirtualBox VMs sized as above."):
        info("Aborted. Nothing was started.")
        return EXIT_FAIL
    env = {"LAB_PROFILE": args.profile} if args.profile else None
    return run(args, ["vagrant", "up"], env_extra=env)


def cmd_cluster_ssh(args: argparse.Namespace) -> int:
    return run(args, ["vagrant", "ssh", args.node])


def cmd_cluster_halt(args: argparse.Namespace) -> int:
    return run(args, ["vagrant", "halt"])


def cmd_cluster_destroy(args: argparse.Namespace) -> int:
    info("This deletes the three lab VMs and everything stored inside them.")
    if not args.dry_run:
        require("vagrant", args.verbose)
    if not confirm(args, "this destroys the lab VMs."):
        info("Aborted. Nothing was destroyed.")
        return EXIT_FAIL
    return run(args, ["vagrant", "destroy", "--force"])


# --- completion --------------------------------------------------------------------


def command_tree(parser: argparse.ArgumentParser) -> dict:
    """Describe the parser as {subs: {name: node}, opts: [(flag, help)], values: [...]}."""
    node: dict = {"subs": {}, "opts": [], "values": [], "help": ""}
    for action in parser._actions:  # argparse has no public API for introspection
        if isinstance(action, argparse._SubParsersAction):
            helps = {a.dest: a.help or "" for a in action._choices_actions}
            for name, sub in action.choices.items():
                child = command_tree(sub)
                child["help"] = helps.get(name, "")
                node["subs"][name] = child
        elif action.option_strings:
            text = "" if action.help in (None, argparse.SUPPRESS) else action.help
            node["opts"] += [(flag, text) for flag in action.option_strings]
        elif action.choices:
            node["values"] += [str(choice) for choice in action.choices]
    return node


def flatten(node: dict, path: tuple = ()) -> list[tuple[tuple, dict]]:
    found = [(path, node)]
    for name, child in node["subs"].items():
        found += flatten(child, path + (name,))
    return found


def candidates(node: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    subs = [(name, child["help"]) for name, child in node["subs"].items()]
    subs += [(value, "") for value in node["values"]]
    return subs, node["opts"]


def clean(text: str) -> str:
    """Make a help string safe inside single quotes in every shell."""
    text = text.encode("ascii", "replace").decode("ascii")
    for char in "'\"`$\\|":
        text = text.replace(char, "")
    return " ".join(text.split())


def gen_bash(tree: dict) -> str:
    nodes = flatten(tree)
    known = "|".join(f'"{" ".join(p)}"' for p, _ in nodes if p)
    cases = []
    for path, node in nodes:
        subs, opts = candidates(node)
        cases.append(
            f'        "{" ".join(path)}") subs="{" ".join(n for n, _ in subs)}"; '
            f'opts="{" ".join(n for n, _ in opts)}" ;;'
        )
    return f"""# bash completion for lab -- generated by `lab completion bash`; do not edit.
# Install for this shell:  source <(lab completion bash)
# Install permanently:     lab completion bash > ~/.local/share/bash-completion/completions/lab
_lab() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}" node="" next w i subs="" opts=""
    for ((i = 1; i < COMP_CWORD; i++)); do
        w="${{COMP_WORDS[i]}}"
        next="${{node:+$node }}$w"
        case "$next" in
            {known}) node="$next" ;;
        esac
    done
    case "$node" in
{chr(10).join(cases)}
    esac
    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "$opts" -- "$cur"))
    else
        COMPREPLY=($(compgen -W "$subs" -- "$cur"))
    fi
}}
complete -F _lab lab ./lab
"""


def gen_zsh(tree: dict) -> str:
    nodes = flatten(tree)
    known = "|".join(f'"{" ".join(p)}"' for p, _ in nodes if p)

    def items(pairs: list[tuple[str, str]]) -> str:
        return " ".join(f"'{n}:{clean(h)}'" if h else f"'{n}'" for n, h in pairs)

    cases = []
    for path, node in nodes:
        subs, opts = candidates(node)
        cases.append(f'        "{" ".join(path)}") subs=({items(subs)}); opts=({items(opts)}) ;;')
    # `path` is tied to PATH in zsh, so the walker uses `node`.
    return f"""#compdef lab
# zsh completion for lab -- generated by `lab completion zsh`; do not edit.
# Install for this shell (after compinit):  source <(lab completion zsh)
# Install permanently:                      lab completion zsh > "${{fpath[1]}}/_lab"
_lab() {{
    local node="" next w
    local -a subs opts
    for w in "${{(@)words[2,CURRENT-1]}}"; do
        next="${{node:+$node }}$w"
        case "$next" in
            {known}) node="$next" ;;
        esac
    done
    case "$node" in
{chr(10).join(cases)}
    esac
    if [[ "$PREFIX" == -* ]]; then
        _describe -t options 'option' opts
    else
        _describe -t commands 'command' subs
    fi
}}
if [[ "${{funcstack[1]}}" == "_lab" ]]; then _lab "$@"; else compdef _lab lab; fi
"""


def gen_fish(tree: dict) -> str:
    nodes = flatten(tree)
    known = " ".join(f"'{' '.join(p)}'" for p, _ in nodes if p)

    def printf(pairs: list[tuple[str, str]]) -> str:
        body = " ".join(f"'{n}' '{clean(h)}'" for n, h in pairs)
        return f"printf '%s\\t%s\\n' {body}" if pairs else "true"

    cases = []
    for path, node in nodes:
        subs, opts = candidates(node)
        cases.append(
            f"        case '{' '.join(path)}'\n"
            f"            if test $want = opts\n                {printf(opts)}\n"
            f"            else\n                {printf(subs)}\n            end"
        )
    return f"""# fish completion for lab -- generated by `lab completion fish`; do not edit.
# Install:  lab completion fish > ~/.config/fish/completions/lab.fish
function __lab_candidates
    set -l tokens (commandline -opc)
    set -e tokens[1]
    set -l node ''
    for w in $tokens
        set -l next (string trim -- "$node $w")
        switch $next
            case {known}
                set node $next
        end
    end
    set -l want subs
    if string match -q -- '-*' (commandline -ct)
        set want opts
    end
    switch $node
{chr(10).join(cases)}
    end
end
complete -c lab -f -a '(__lab_candidates)'
"""


def gen_powershell(tree: dict) -> str:
    def items(pairs: list[tuple[str, str]]) -> str:
        return ", ".join(f"'{n}|{clean(h)}'" for n, h in pairs)

    entries = []
    for path, node in flatten(tree):
        subs, opts = candidates(node)
        key = " ".join(("lab",) + path)
        entries.append(f"    '{key}' = @{{ Subs = @({items(subs)}); Opts = @({items(opts)}) }}")
    return f"""# PowerShell completion for lab -- generated by `lab completion powershell`; do not edit.
# Install for this session:  lab completion powershell | Out-String | Invoke-Expression
# Keep it: add that line to your profile (notepad $PROFILE).
$global:LabCompletionTree = @{{
{chr(10).join(entries)}
}}
Register-ArgumentCompleter -Native -CommandName @('lab', 'lab.cmd', '.\\lab', '.\\lab.cmd') -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $words = @($commandAst.CommandElements | Select-Object -Skip 1 | ForEach-Object {{ $_.ToString() }})
    if ($wordToComplete -ne '' -and $words.Count -gt 0) {{
        if ($words.Count -le 1) {{ $words = @() }} else {{ $words = @($words[0..($words.Count - 2)]) }}
    }}
    $node = 'lab'
    foreach ($w in $words) {{
        $next = "$node $w"
        if ($global:LabCompletionTree.ContainsKey($next)) {{ $node = $next }}
    }}
    $entry = $global:LabCompletionTree[$node]
    $items = if ($wordToComplete.StartsWith('-')) {{ $entry.Opts }} else {{ $entry.Subs }}
    foreach ($item in $items) {{
        $name, $desc = $item -split '\\|', 2
        if ($name -like "$wordToComplete*") {{
            if (-not $desc) {{ $desc = $name }}
            [System.Management.Automation.CompletionResult]::new($name, $name, 'ParameterValue', $desc)
        }}
    }}
}}
"""


GENERATORS = {"bash": gen_bash, "zsh": gen_zsh, "fish": gen_fish, "powershell": gen_powershell}


def cmd_completion(args: argparse.Namespace) -> int:
    tree = command_tree(build_parser())
    tree["subs"]["help"]["values"] = list(tree["subs"])  # `lab help <TAB>` lists commands
    text = GENERATORS[args.shell](tree)
    # Bytes, not print(): Windows text mode would write CRLF and break `source <(...)` in Git Bash.
    sys.stdout.buffer.write(text.encode("ascii"))
    sys.stdout.buffer.flush()
    return EXIT_OK


def cmd_help(args: argparse.Namespace) -> int:
    build_parser().parse_args(list(args.words) + ["--help"])  # prints help, raises SystemExit(0)
    return EXIT_OK


# --- parser ------------------------------------------------------------------------


def common_flags(top: bool) -> argparse.ArgumentParser:
    """Global flags. Sub-commands re-declare them with SUPPRESS defaults so that
    `lab --dry-run image build` and `lab image build --dry-run` both work."""
    parent = argparse.ArgumentParser(add_help=False)
    default = (lambda value: value) if top else (lambda value: argparse.SUPPRESS)
    group = parent.add_argument_group("global options")
    group.add_argument("--dry-run", action="store_true", default=default(False),
                       help="print the commands that would run, run nothing")
    group.add_argument("--no-color", action="store_true", default=default(False),
                       help="disable colored output (the NO_COLOR variable also works)")
    group.add_argument("-v", "--verbose", action="store_true", default=default(False),
                       help="show resolved tool paths")
    return parent


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Keep the hand-formatted description/epilog, and list sub-commands without the
    redundant '<command>' header line argparse adds above them."""

    def _format_action(self, action):
        if isinstance(action, argparse._SubParsersAction):
            return "".join(self._format_action(sub) for sub in action._get_subactions())
        return super()._format_action(action)


def docker_value(value: str) -> str:
    """Reject values that docker would read as an option (e.g. --tag=--privileged)."""
    if not value.strip() or value.startswith("-"):
        raise argparse.ArgumentTypeError("must not be empty or start with '-'")
    return value


def show_help(parser: argparse.ArgumentParser):
    def handler(args: argparse.Namespace) -> int:
        parser.print_help()
        return EXIT_OK
    return handler


def build_parser() -> argparse.ArgumentParser:
    raw = HelpFormatter
    sub_flags = common_flags(top=False)

    top = argparse.ArgumentParser(
        prog="lab",
        formatter_class=raw,
        parents=[common_flags(top=True)],
        description=(
            "ROS 2 on Kubernetes lab: checks, the Jazzy container image and the Vagrant\n"
            "cluster behind one command. Linux, macOS and Windows; needs only Python 3.\n\n"
            "Scope - please read:\n"
            "  * 'cluster' drives the HISTORICAL Vagrant lab (ROS 2 Foxy, Kubernetes 1.29,\n"
            "    Weave Net). It asks for about 30 GB RAM and 18 vCPUs by default and is not a\n"
            "    validated or production deployment.\n"
            "  * 'image test' is a smoke test inside ONE container. It does not test\n"
            "    Kubernetes or cross-node DDS delivery."
        ),
        epilog=(
            examples([
                ("lab doctor", "can this machine run the lab? (read-only)"),
                ("lab check", "run every repository check"),
                ("lab image build", "build the Jazzy container image"),
                ("lab image test", "smoke-test it (one container only)"),
                ("lab cluster up --profile small", "start a smaller historical cluster"),
                ("lab cluster up --dry-run", "preview the command, run nothing"),
                ("lab help cluster ssh", "help for one command"),
            ])
            + "\n\nStart it as ./lab (Linux, macOS) or lab.cmd (Windows). On Linux/macOS you can also\n"
            "run `make` for a list of shortcuts. Tab completion: lab completion --help\n"
            "Exit status: 0 ok, 1 failed or declined, 2 usage error, 3 missing prerequisite."
        ),
    )
    top.set_defaults(func=show_help(top), yes=False)
    commands = top.add_subparsers(dest="command", metavar="<command>", title="commands")

    def add(parent, name: str, summary: str, rows, func, long: str = ""):
        p = parent.add_parser(
            name, help=summary, description=textwrap.fill((long or summary) + ".", 78), parents=[sub_flags],
            formatter_class=raw, epilog=examples(rows) if rows else None,
        )
        p.set_defaults(func=func)
        return p

    add(commands, "doctor", "check this machine for the lab (read-only)", [
        ("lab doctor", "report CPU type, RAM, tools, line endings and which paths fit"),
    ], cmd_doctor, "Run scripts/doctor.py: reports your CPU type, RAM, installed tools and git "
       "line endings, and which lab paths this machine can realistically run. Installs nothing")

    check = add(commands, "check", "run the repository checks", [
        ("lab check", "run all checks and print a PASS/FAIL/SKIPPED summary"),
        ("lab check links", "only the Markdown link check"),
        ("lab check --strict", "exit 1 if a check had to be SKIPPED (scripts)"),
        ("lab check shell --dry-run", "show the command without running it"),
    ], cmd_check, "Run the same static checks as CI. They do not start any VM, container or "
       "cluster and do not prove the lab works. A check whose tool is missing is reported as "
       "SKIPPED, never as PASS")
    check.add_argument("--strict", action="store_true", help="exit 1 if any check was SKIPPED (for scripts)")
    check.add_argument("what", nargs="?", default="all", choices=["all", *CHECKS],
                       help="preflight=line endings/env, shell=bash -n, links=Markdown links, "
                            "site=website files, vagrantfile=ruby -c syntax only (default: all)")

    image = add(commands, "image", "build and test the ROS 2 Jazzy container", [
        ("lab image build", "build ros-jazzy-lab:local"),
        ("lab image test", "run the same-container smoke test"),
        ("lab image shell", "open a bash shell in the image"),
    ], None, "Jazzy / Ubuntu 24.04 image from ROS2/Dockerfile")
    image_cmds = image.add_subparsers(dest="subcommand", metavar="<subcommand>", title="subcommands")
    image.set_defaults(func=show_help(image))

    def image_flags(p):
        p.add_argument("--tag", default=IMAGE_TAG, type=docker_value, help=f"image name (default: {IMAGE_TAG})")
        p.add_argument("--platform", default=IMAGE_PLATFORM, type=docker_value,
                       help=f"target platform (default: {IMAGE_PLATFORM}, what CI tests)")

    p = add(image_cmds, "build", "build the image", [
        ("lab image build", "build ros-jazzy-lab:local for linux/amd64"),
        ("lab image build --pull", "refresh the base image first"),
        ("lab image build --dry-run", "print the docker command only"),
    ], cmd_image_build, "Run docker build on ROS2/Dockerfile. On Apple Silicon and other Arm hosts "
       "the default linux/amd64 runs through emulation (slower); native arm64 is untested here")
    image_flags(p)
    p.add_argument("--pull", action="store_true", help="always pull a newer base image")

    p = add(image_cmds, "test", "smoke-test the image (one container)", [
        ("lab image test", "test ros-jazzy-lab:local"),
        ("lab image test --tag my/img:dev", "test another tag"),
    ], cmd_image_test, "Send scripts/test-ros2-image.sh into a container: checks Jazzy, Ubuntu "
       "24.04, demo_nodes_cpp, stress-ng and a local talker/listener exchange. Same-container "
       "only; it does not test Kubernetes or cross-node DDS")
    image_flags(p)

    p = add(image_cmds, "shell", "open a shell in the image", [
        ("lab image shell", "interactive bash in ros-jazzy-lab:local"),
    ], cmd_image_shell, "Start an interactive container")
    image_flags(p)

    cluster = add(commands, "cluster", "drive the historical Vagrant cluster", [
        ("lab cluster status", "show the state of the three VMs"),
        ("lab cluster up --profile small", "start with smaller VMs"),
        ("lab cluster ssh worker1", "log in to a node"),
        ("lab cluster destroy", "delete the VMs (asks first)"),
    ], None, "Wraps Vagrant for the historical lab (ROS 2 Foxy, Kubernetes 1.29). Needs "
       "VirtualBox and Vagrant; not available on Arm hosts such as Apple Silicon")
    cluster_cmds = cluster.add_subparsers(dest="subcommand", metavar="<subcommand>", title="subcommands")
    cluster.set_defaults(func=show_help(cluster))

    add(cluster_cmds, "status", "show VM state", [
        ("lab cluster status", "vagrant status"),
    ], cmd_cluster_status, "Show the state of the three VMs")

    p = add(cluster_cmds, "up", "start the three VMs (asks first)", [
        ("lab cluster up", "default sizes (about 30 GB RAM, 18 vCPUs)"),
        ("lab cluster up --profile small", "about 16 GB RAM, 8 vCPUs (unvalidated)"),
        ("lab cluster up --dry-run", "show the command, start nothing"),
        ("lab cluster up --yes", "skip the confirmation (scripts)"),
    ], cmd_cluster_up, "Run vagrant up. Shows the memory/CPU cost and asks you to type 'yes' "
       "first. Sizes come from the Vagrantfile (LAB_PROFILE, LAB_* variables)")
    p.add_argument("--profile", choices=sorted(PROFILE_SIZES), help="VM size profile (sets LAB_PROFILE)")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")

    p = add(cluster_cmds, "ssh", "log in to a node", [
        ("lab cluster ssh", "log in to the control plane"),
        ("lab cluster ssh worker2", "log in to a worker"),
    ], cmd_cluster_ssh, "Run vagrant ssh. Inside the VM, kubectl is already configured")
    p.add_argument("node", nargs="?", default="controlplane", choices=NODES,
                   help="node name (default: controlplane)")

    add(cluster_cmds, "halt", "stop the VMs (keeps their disks)", [
        ("lab cluster halt", "vagrant halt"),
    ], cmd_cluster_halt, "Shut the VMs down without deleting them")

    p = add(cluster_cmds, "destroy", "delete the VMs (asks first)", [
        ("lab cluster destroy", "asks you to type 'yes'"),
        ("lab cluster destroy --yes", "no prompt (scripts)"),
    ], cmd_cluster_destroy, "Delete the three VMs and everything stored in them")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")

    p = add(commands, "completion", "print a shell completion script", [
        ("source <(lab completion bash)", "bash, current shell"),
        ("source <(lab completion zsh)", "zsh, current shell (after compinit)"),
        ("lab completion fish > ~/.config/fish/completions/lab.fish", "fish, permanent"),
        ("lab completion powershell | Out-String | Invoke-Expression", "PowerShell, current session"),
    ], cmd_completion, "Print a tab-completion script for your shell. The script is generated from "
       "this program's own commands, so it always matches. Nothing is installed or edited for you; "
       "see docs/CLI.md for permanent setup")
    p.add_argument("shell", choices=sorted(GENERATORS), help="your shell")

    p = add(commands, "help", "show help for a command", [
        ("lab help", "overview"),
        ("lab help cluster up", "same as: lab cluster up --help"),
    ], cmd_help, "Same as adding --help to a command")
    p.add_argument("words", nargs="*", help="the command to explain, e.g. cluster up")

    return top


def run_cli(argv: list[str] | None) -> int:
    global _color_out, _color_err
    try:
        args = build_parser().parse_args(argv)
        _color_out = use_color(args.no_color, sys.stdout)
        _color_err = use_color(args.no_color, sys.stderr)
        return args.func(args)
    except PrereqError as exc:
        error(str(exc))
        return EXIT_PREREQ
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 130
    except SystemExit as exc:  # argparse --help (0) and usage errors (2), including `lab help`
        if exc.code is None:
            return EXIT_OK
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # legacy Windows code pages
        except (AttributeError, ValueError):
            pass
    try:
        code = run_cli(argv)
        sys.stdout.flush()  # here, outside every handler above, so a closed pipe cannot slip past
        return code
    except BrokenPipeError:  # e.g. `lab completion bash | head -n 1`: the reader left early
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())  # silence the exit-time flush
        except (OSError, ValueError):
            pass
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
