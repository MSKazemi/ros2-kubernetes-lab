"""Tests for scripts/lab.py (stdlib unittest; no Docker, Vagrant or network needed).

Run:  python -m unittest discover -s tests -v

Tests that need an optional shell (zsh, fish, PowerShell) skip themselves when it is absent.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
LAB_PATH = ROOT / "scripts" / "lab.py"

spec = importlib.util.spec_from_file_location("lab", LAB_PATH)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def run_lab(*argv: str, stdin_tty: bool = False) -> tuple[int, str, str]:
    """Call lab.main in-process; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    stdin = mock.Mock()
    stdin.isatty.return_value = stdin_tty
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
            mock.patch.object(sys, "stdin", stdin):
        code = lab.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def all_command_paths() -> list[list[str]]:
    return [list(path) for path, _ in lab.flatten(lab.command_tree(lab.build_parser())) if path]


class FakeChild:
    """Stands in for subprocess.Popen and records what lab would have started."""

    def __init__(self, args, kwargs, returncode, interrupts):
        self.args, self.kwargs, self.returncode = list(args), kwargs, returncode
        self.input = None
        self.interrupts_left = interrupts
        self.terminated = self.killed = False

    def communicate(self, input=None):
        if input is not None:
            self.input = input
        if self.interrupts_left:
            self.interrupts_left -= 1
            raise KeyboardInterrupt
        return None, None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class ChildProcesses:
    """Patch lab so no real program is started; `started` lists the FakeChild objects."""

    def __init__(self, returncode: int = 0, interrupts: int = 0, tools: bool = True):
        self.started: list[FakeChild] = []
        self.returncode, self.interrupts, self.tools = returncode, interrupts, tools
        self.patches = [
            mock.patch.object(lab.subprocess, "Popen", self._spawn),
            mock.patch.object(lab, "find_tool", lambda name: f"/fake/{name}" if self.tools else None),
            mock.patch.object(lab.platform, "machine", return_value="x86_64"),
        ]

    def _spawn(self, args, **kwargs):
        child = FakeChild(args, kwargs, self.returncode, self.interrupts)
        self.started.append(child)
        return child

    def __enter__(self):
        # Python 3.8 runs `uname -p` through subprocess on the first platform call; cache it
        # before Popen is replaced, or the stdlib itself would talk to the fake.
        lab.platform.uname()
        for patch in self.patches:
            patch.start()
        return self

    def __exit__(self, *exc):
        for patch in reversed(self.patches):
            patch.stop()


class HelpTests(unittest.TestCase):
    def test_every_command_has_examples_and_exits_zero(self):
        paths = all_command_paths()
        self.assertGreaterEqual(len(paths), 12)
        for path in paths:
            with self.subTest(command=" ".join(path)):
                code, out, _ = run_lab(*path, "--help")
                self.assertEqual(code, 0)
                self.assertIn("Examples:", out)
                self.assertIn("lab ", out.split("Examples:")[1])

    def test_top_level_help_and_bare_invocation(self):
        for argv in ([], ["--help"], ["help"]):
            with self.subTest(argv=argv):
                code, out, _ = run_lab(*argv)
                self.assertEqual(code, 0)
                for word in ("doctor", "check", "image", "cluster", "completion", "HISTORICAL", "ONE container"):
                    self.assertIn(word, out)

    def test_help_never_suggests_double_ampersand(self):
        # `&&` is a parse error in Windows PowerShell 5.1, which the docs claim to support.
        for path in all_command_paths() + [[]]:
            with self.subTest(command=" ".join(path)):
                _, out, _ = run_lab(*path, "--help")
                self.assertNotIn("&&", out)

    def test_group_without_subcommand_prints_help(self):
        for group in ("image", "cluster"):
            code, out, _ = run_lab(group)
            self.assertEqual(code, 0)
            self.assertIn("subcommands:", out)

    def test_help_command_matches_dash_help(self):
        _, via_help, _ = run_lab("help", "cluster", "up")
        _, via_flag, _ = run_lab("cluster", "up", "--help")
        self.assertEqual(via_help, via_flag)

    def test_usage_error_exits_2(self):
        code, _, err = run_lab("cluster", "ssh", "nosuchnode")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_docker_values_that_look_like_options_are_rejected(self):
        for flag in ("--tag", "--platform"):
            code, _, err = run_lab("image", "build", f"{flag}=--privileged")
            self.assertEqual(code, 2)
            self.assertIn("must not be empty or start with '-'", err)

    def test_source_is_ascii_for_legacy_windows_consoles(self):
        LAB_PATH.read_bytes().decode("ascii")


class DryRunTests(unittest.TestCase):
    def test_flag_works_before_and_after_the_subcommand(self):
        _, before, _ = run_lab("--dry-run", "image", "build")
        _, after, _ = run_lab("image", "build", "--dry-run")
        self.assertEqual(before, after)
        self.assertIn("docker build --platform linux/amd64 --file ROS2/Dockerfile --tag ros-jazzy-lab:local .", before)

    def test_dry_run_needs_no_installed_tools(self):
        with mock.patch.object(lab, "find_tool", return_value=None):
            for argv in (["image", "build"], ["image", "test"], ["cluster", "status"],
                         ["cluster", "up"], ["cluster", "destroy"], ["cluster", "ssh", "worker1"],
                         ["check"], ["doctor"]):
                with self.subTest(argv=argv):
                    code, out, _ = run_lab(*argv, "--dry-run")
                    self.assertEqual(code, 0)
                    self.assertIn("$ ", out)

    def test_environment_is_described_not_shell_prefixed(self):
        _, out, _ = run_lab("cluster", "up", "--profile", "small", "--dry-run")
        self.assertIn("$ vagrant up", out)
        self.assertIn("(environment: LAB_PROFILE=small)", out)
        self.assertNotIn("$env:", out)  # cmd.exe, PowerShell and POSIX set variables differently
        _, out, _ = run_lab("cluster", "up", "--dry-run")
        self.assertNotIn("LAB_PROFILE", out)

    def test_check_dry_run_lists_every_command(self):
        _, out, _ = run_lab("check", "--dry-run")
        for needle in ("doctor.py", "check-shell.sh", "check-markdown-links.py", "validate-site.py", "ruby -c Vagrantfile"):
            self.assertIn(needle, out)


class SafetyTests(unittest.TestCase):
    """cluster up/destroy must never start or delete VMs without an explicit yes."""

    def setUp(self):
        self.children = ChildProcesses()
        self.children.__enter__()
        self.addCleanup(self.children.__exit__)
        probe = mock.patch.object(lab.subprocess, "run", return_value=mock.Mock(returncode=0, stderr=""))
        self.probe = probe.start()
        self.addCleanup(probe.stop)

    def test_non_interactive_without_yes_refuses(self):
        for argv in (["cluster", "up"], ["cluster", "destroy"]):
            with self.subTest(argv=argv):
                code, _, err = run_lab(*argv, stdin_tty=False)
                self.assertEqual(code, 1)
                self.assertIn("--yes", err)
                self.assertEqual(self.children.started, [])

    def test_interactive_requires_typing_yes(self):
        for answer, expected_children in (("no", 0), ("", 0), ("YES", 1)):
            self.children.started.clear()
            with self.subTest(answer=answer), mock.patch("builtins.input", return_value=answer):
                code, _, _ = run_lab("cluster", "up", stdin_tty=True)
                self.assertEqual(len(self.children.started), expected_children)
                self.assertEqual(code, 0 if expected_children else 1)

    def test_yes_flag_runs_vagrant_from_repo_root(self):
        code, _, _ = run_lab("cluster", "destroy", "--yes")
        self.assertEqual(code, 0)
        child = self.children.started[0]
        self.assertEqual(child.args, ["/fake/vagrant", "destroy", "--force"])
        self.assertEqual(Path(child.kwargs["cwd"]), ROOT)

    def test_vagrant_cannot_be_redirected_to_another_project(self):
        stale = {"VAGRANT_CWD": "/some/other/project", "VAGRANT_VAGRANTFILE": "/some/other/Vagrantfile"}
        with mock.patch.dict(os.environ, stale):
            code, _, err = run_lab("cluster", "destroy", "--yes")
        env = self.children.started[0].kwargs["env"]
        self.assertEqual(code, 0)
        self.assertEqual(env["VAGRANT_CWD"], str(ROOT))
        self.assertNotIn("VAGRANT_VAGRANTFILE", env)
        self.assertIn("ignoring VAGRANT_CWD=/some/other/project", err)
        self.assertIn("ignoring VAGRANT_VAGRANTFILE", err)

    def test_other_tools_do_not_get_vagrant_variables(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("VAGRANT_CWD", None)
            run_lab("image", "build")
        self.assertNotIn("VAGRANT_CWD", self.children.started[0].kwargs["env"])

    def test_up_prints_scope_and_default_cost_before_asking(self):
        _, _, err = run_lab("cluster", "up", "--yes")
        for needle in ("HISTORICAL", "Foxy", "not a validated", "30 GB", "18 vCPUs"):
            self.assertIn(needle, err)

    def test_cost_banner_follows_profile_and_overrides(self):
        _, _, err = run_lab("cluster", "up", "--profile", "small", "--yes")
        self.assertIn("16 GB", err)
        self.assertIn("8 vCPUs", err)
        self.assertIn("not validated", err)
        with mock.patch.dict(os.environ, {"LAB_WORKER_MEMORY_MB": "8192"}):
            _, _, err = run_lab("cluster", "up", "--yes")
        self.assertIn("34 GB", err)  # 18240 + 2 * 8192 MB
        self.assertIn("changed by LAB_* variables", err)

    def test_bad_profile_or_size_is_rejected_before_the_prompt(self):
        for name, value in (("LAB_PROFILE", "huge"), ("LAB_CP_CPUS", "many"), ("LAB_WORKER_CPUS", "0")):
            self.children.started.clear()
            with self.subTest(variable=name), mock.patch.dict(os.environ, {name: value}), \
                    mock.patch("builtins.input", side_effect=AssertionError("must not prompt")):
                code, _, err = run_lab("cluster", "up", stdin_tty=True)
            self.assertEqual(code, 2)
            self.assertIn(name, err)
            self.assertEqual(self.children.started, [])

    def test_missing_vagrant_is_reported_before_the_prompt(self):
        self.children.tools = False
        for argv in (["cluster", "up"], ["cluster", "destroy"]):
            with self.subTest(argv=argv), mock.patch("builtins.input", side_effect=AssertionError("must not prompt")):
                code, _, err = run_lab(*argv, stdin_tty=True)
            self.assertEqual(code, 3)
            self.assertIn("developer.hashicorp.com", err)

    def test_arm_host_is_refused_before_prompting(self):
        with mock.patch.object(lab.platform, "machine", return_value="arm64"), \
                mock.patch.dict(os.environ, {"LAB_ALLOW_ARM": ""}):
            code, _, err = run_lab("cluster", "up", "--yes")
        self.assertEqual(code, 3)
        self.assertIn("Arm", err)
        self.assertEqual(self.children.started, [])

    def test_missing_tool_exits_3_with_hint(self):
        self.children.tools = False
        code, _, err = run_lab("cluster", "status")
        self.assertEqual(code, 3)
        self.assertIn("vagrant", err)
        self.assertIn("developer.hashicorp.com", err)

    def test_image_test_sends_lf_script_on_stdin_and_states_scope(self):
        crlf = b"#!/usr/bin/env bash\r\necho hi\r\n"
        with mock.patch.object(Path, "read_bytes", return_value=crlf):
            code, _, err = run_lab("image", "test")
        self.assertEqual(code, 0)
        child = self.children.started[-1]
        self.assertEqual(child.input, b"#!/usr/bin/env bash\necho hi\n")
        self.assertEqual(child.args[-2:], ["bash", "-s"])
        self.assertIn("does not exercise Kubernetes", err)
        self.assertIn("same-container", err)

    def test_image_test_without_built_image_explains(self):
        self.probe.return_value = mock.Mock(returncode=1, stderr="Error: No such image: ros-jazzy-lab:local")
        code, _, err = run_lab("image", "test")
        self.assertEqual(code, 1)
        self.assertIn("lab image build", err)
        self.assertEqual(self.children.started, [])

    def test_image_test_with_docker_down_says_so_instead_of_blaming_the_image(self):
        self.probe.return_value = mock.Mock(
            returncode=1, stderr="Cannot connect to the Docker daemon at unix:///var/run/docker.sock.")
        code, _, err = run_lab("image", "test")
        self.assertEqual(code, 3)
        self.assertIn("Is Docker running?", err)
        self.assertNotIn("lab image build", err)

    def test_unreachable_docker_socket_is_not_mistaken_for_a_missing_image(self):
        # Verbatim from Docker 29 with DOCKER_HOST pointing at a dead socket: it contains "no such file".
        self.probe.return_value = mock.Mock(returncode=1, stderr=(
            "failed to connect to the docker API at unix:///nonexistent.sock; check if the path is "
            "correct and if the daemon is running: dial unix /nonexistent.sock: connect: no such file or directory"))
        code, _, err = run_lab("image", "test")
        self.assertEqual(code, 3)
        self.assertIn("Is Docker running?", err)
        self.assertNotIn("lab image build", err)


class InterruptTests(unittest.TestCase):
    def test_first_ctrl_c_waits_for_the_child_instead_of_killing_it(self):
        with ChildProcesses(interrupts=1) as children:
            code, _, err = run_lab("cluster", "status")
        child = children.started[0]
        self.assertEqual(code, 0)
        self.assertFalse(child.terminated or child.killed)
        self.assertIn("Interrupted", err)

    def test_repeated_ctrl_c_terminates_then_kills(self):
        with ChildProcesses(interrupts=3) as children:
            run_lab("cluster", "status")
        child = children.started[0]
        self.assertTrue(child.terminated)
        self.assertTrue(child.killed)

    def test_ctrl_c_outside_a_child_exits_130_without_traceback(self):
        with mock.patch.object(lab, "run", side_effect=KeyboardInterrupt):
            code, _, err = run_lab("cluster", "status")
        self.assertEqual(code, 130)
        self.assertNotIn("Traceback", err)

    @unittest.skipIf(os.name == "nt", "POSIX signals and shell script")
    def test_real_sigint_does_not_kill_the_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "vagrant"
            fake.write_text("#!/bin/sh\necho started\nsleep 1\necho finished\n")
            fake.chmod(0o755)
            env = {**os.environ, "PATH": tmp + os.pathsep + os.environ["PATH"]}
            proc = subprocess.Popen([sys.executable, str(LAB_PATH), "cluster", "status"], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(proc.stdout.readline().strip(), "started")
            time.sleep(0.3)
            proc.send_signal(signal.SIGINT)  # to lab only, not the child
            out, err = proc.communicate(timeout=30)
        self.assertIn("finished", out, "lab killed the child on Ctrl-C")
        self.assertEqual(proc.returncode, 0, err)
        self.assertNotIn("Traceback", err)


class OutputTests(unittest.TestCase):
    def test_colour_is_decided_per_stream(self):
        tty, plain = mock.Mock(), mock.Mock()
        tty.isatty.return_value, plain.isatty.return_value = True, False
        with mock.patch.dict(os.environ), mock.patch.object(lab.platform, "system", return_value="Linux"):
            os.environ.pop("NO_COLOR", None)
            self.assertTrue(lab.use_color(False, tty))
            self.assertFalse(lab.use_color(False, plain))  # e.g. `lab check 2>log`
            self.assertFalse(lab.use_color(True, tty))  # --no-color
            os.environ["NO_COLOR"] = "1"
            self.assertFalse(lab.use_color(False, tty))

    def test_style_uses_the_flag_of_the_stream_it_is_written_to(self):
        with mock.patch.object(lab, "_color_out", True), mock.patch.object(lab, "_color_err", False):
            self.assertIn("\033[", lab.style("x", "31"))
            self.assertNotIn("\033[", lab.style("x", "31", err=True))

    def test_no_colour_when_not_a_terminal(self):
        _, out, err = run_lab("image", "build", "--dry-run")
        self.assertNotIn("\033[", out + err)

    @unittest.skipIf(os.name == "nt", "POSIX pipes")
    def test_closed_pipe_is_quiet(self):
        proc = subprocess.Popen([sys.executable, str(LAB_PATH), "--help"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdout.close()  # the reader goes away before lab writes
        err = proc.stderr.read().decode()
        proc.stderr.close()
        code = proc.wait()
        self.assertEqual(err, "", "BrokenPipeError leaked to stderr")
        self.assertIn(code, (0, 1))


class CheckTests(unittest.TestCase):
    def test_missing_optional_tool_is_skipped_not_passed(self):
        real_find = lab.find_tool
        with ChildProcesses():
            with mock.patch.object(lab, "find_tool", side_effect=lambda n: None if n in ("bash", "ruby") else real_find(n)):
                code, out, _ = run_lab("check", "shell")
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)
        self.assertNotIn("PASS", out)
        self.assertIn("not a pass", out)

    def test_strict_turns_skipped_into_a_failure(self):
        with ChildProcesses(), mock.patch.object(lab, "find_tool", return_value=None):
            code, out, _ = run_lab("check", "vagrantfile", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("SKIPPED", out)
        self.assertIn("--strict", out)

    def test_shell_check_is_skipped_outside_a_git_checkout(self):
        with ChildProcesses(), tempfile.TemporaryDirectory() as tmp, mock.patch.object(lab, "REPO_ROOT", Path(tmp)):
            code, out, _ = run_lab("check", "shell")
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)
        self.assertIn("git checkout", out)

    def test_failing_check_exits_1(self):
        with ChildProcesses(returncode=1):
            code, out, _ = run_lab("check", "links")
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_windows_bash_never_picks_the_wsl_launcher(self):
        no_roots = {"ProgramFiles": "", "ProgramW6432": "", "ProgramFiles(x86)": "", "LOCALAPPDATA": ""}
        for found, expected in ((r"C:\Windows\System32\bash.exe", None),
                                (r"C:\tools\msys64\usr\bin\bash.exe", r"C:\tools\msys64\usr\bin\bash.exe")):
            with self.subTest(found=found), mock.patch.object(lab.platform, "system", return_value="Windows"), \
                    mock.patch.dict(os.environ, no_roots), \
                    mock.patch.object(lab, "find_on_windows_path", return_value=found):
                self.assertEqual(lab.find_tool("bash"), expected)

    def test_windows_tool_lookup_ignores_the_current_directory(self):
        with tempfile.TemporaryDirectory() as cwd_dir, tempfile.TemporaryDirectory() as path_dir:
            (Path(cwd_dir) / "docker.EXE").write_text("planted")
            env = {"PATH": path_dir, "PATHEXT": ".COM;.EXE;.BAT;.CMD"}
            old_cwd = os.getcwd()
            os.chdir(cwd_dir)
            try:
                with mock.patch.dict(os.environ, env):
                    self.assertIsNone(lab.find_on_windows_path("docker"))
                    (Path(path_dir) / "docker.EXE").write_text("real")
                    self.assertEqual(lab.find_on_windows_path("docker"), os.path.join(path_dir, "docker.EXE"))
            finally:
                os.chdir(old_cwd)


class CompletionTests(unittest.TestCase):
    def script(self, shell: str) -> str:
        proc = subprocess.run([sys.executable, str(LAB_PATH), "completion", shell],
                              capture_output=True, check=True)
        self.assertNotIn(b"\r", proc.stdout, "completion output must use LF only")
        return proc.stdout.decode("ascii")

    def write(self, tmp: str, name: str, text: str) -> Path:
        path = Path(tmp) / name
        path.write_bytes(text.encode("ascii"))  # bytes: keep LF on Windows
        return path

    def test_every_command_appears_in_every_script(self):
        words = {w for path in all_command_paths() for w in path}
        self.assertLessEqual({"doctor", "check", "image", "cluster", "ssh", "destroy", "build", "completion", "help"}, words)
        for shell in lab.GENERATORS:
            text = self.script(shell)
            for word in words:
                with self.subTest(shell=shell, word=word):
                    self.assertIn(word, text)
            for node in lab.NODES:
                self.assertIn(node, text)

    @unittest.skipIf(os.name == "nt", "on Windows `bash` may be the WSL stub; Git Bash use is not tested")
    @unittest.skipUnless(shutil.which("bash"), "bash not installed")
    def test_bash_syntax_and_real_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "lab.bash", self.script("bash"))
            self.assertEqual(subprocess.run(["bash", "-n", str(path)]).returncode, 0)

            def complete(*words: str) -> list[str]:
                line = f"COMP_WORDS=({' '.join(words)}); COMP_CWORD={len(words) - 1}; _lab; echo \"${{COMPREPLY[@]}}\""
                proc = subprocess.run(["bash", "-c", f"source '{path}'; {line}"], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                return proc.stdout.split()

            self.assertEqual(complete("lab", "cl"), ["cluster"])
            self.assertEqual(complete("lab", "cluster", ""), ["status", "up", "ssh", "halt", "destroy"])
            self.assertEqual(complete("lab", "cluster", "s"), ["status", "ssh"])
            self.assertEqual(complete("lab", "cluster", "ssh", ""), ["controlplane", "worker1", "worker2"])
            self.assertEqual(complete("lab", "--dry-run", "image", "t"), ["test"])
            self.assertIn("--profile", complete("lab", "cluster", "up", "--p"))
            self.assertEqual(complete("lab", "check", ""), ["all", "preflight", "shell", "links", "site", "vagrantfile"])
            self.assertEqual(complete("lab", "completion", ""), ["bash", "fish", "powershell", "zsh"])
            self.assertIn("cluster", complete("lab", "help", ""))

    @unittest.skipUnless(shutil.which("fish"), "fish not installed")
    def test_fish_syntax_and_real_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "lab.fish", self.script("fish"))
            self.assertEqual(subprocess.run(["fish", "--no-execute", str(path)]).returncode, 0)

            def complete(line: str) -> list[str]:
                proc = subprocess.run(["fish", "-c", f"source '{path}'; complete -C '{line}'"],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                return sorted(entry.split("\t")[0] for entry in proc.stdout.splitlines())

            self.assertEqual(complete("lab cl"), ["cluster"])
            self.assertEqual(complete("lab cluster "), ["destroy", "halt", "ssh", "status", "up"])
            self.assertEqual(complete("lab cluster s"), ["ssh", "status"])
            self.assertEqual(complete("lab cluster ssh "), ["controlplane", "worker1", "worker2"])
            self.assertEqual(complete("lab --d"), ["--dry-run"])
            self.assertEqual(complete("lab completion "), ["bash", "fish", "powershell", "zsh"])

    @unittest.skipUnless(shutil.which("zsh"), "zsh not installed")
    def test_zsh_syntax_and_command_walking(self):
        """Runs the generated function under real zsh with `_describe` stubbed, so this checks the
        command-path logic and quoting, not zsh's own completion machinery (compinit)."""
        harness = (
            'compdef() { :; }\n'
            '_describe() { local -a arr; arr=("${(@P)${@[-1]}}"); print -r -- "${(j: :)${arr[@]%%:*}}" }\n'
            'source "$LAB_ZSH_SCRIPT"\n'
            't() { words=("$@"); CURRENT=$#; PREFIX="${@[-1]}"; _lab }\n'
            't lab cluster ""\n'
            't lab --dry-run image t\n'
            't lab cluster ssh ""\n'
            'command -v ls >/dev/null && echo PATH-OK\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "lab.zsh", self.script("zsh"))
            self.assertEqual(subprocess.run(["zsh", "-n", str(path)]).returncode, 0)
            proc = subprocess.run(["zsh", "-f", "-c", harness], capture_output=True, text=True,
                                  env={**os.environ, "LAB_ZSH_SCRIPT": str(path)})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["status up ssh halt destroy", "build test shell",
                          "controlplane worker1 worker2", "PATH-OK"])  # PATH-OK: `path` not clobbered

    def test_powershell_real_completion_when_available(self):
        exe = shutil.which("pwsh") or shutil.which("powershell")
        if not exe:
            self.skipTest("PowerShell is not installed")
        probes = [("lab cluster s", ["ssh", "status"]), (".\\lab.cmd cluster s", ["ssh", "status"]),
                  ("lab --d", ["--dry-run"]), ("lab cluster up --p", ["--profile"])]
        with tempfile.TemporaryDirectory() as tmp:
            for line, expected in probes:
                probe = (f"(TabExpansion2 -inputScript '{line}' -cursorColumn {len(line)})"
                         ".CompletionMatches.CompletionText -join ','")
                path = self.write(tmp, "probe.ps1", self.script("powershell") + "\n" + probe + "\n")
                proc = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                       "-File", str(path)], capture_output=True, text=True)
                with self.subTest(line=line):
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(sorted(proc.stdout.strip().split(",")), expected)


class LauncherTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX launcher")
    def test_posix_launcher(self):
        launcher = ROOT / "lab"
        self.assertTrue(os.access(launcher, os.X_OK), "./lab must be executable (git mode 100755)")
        self.assertEqual(subprocess.run(["sh", "-n", str(launcher)]).returncode, 0)
        proc = subprocess.run([str(launcher), "image", "build", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("docker build", proc.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX launcher")
    def test_posix_launcher_follows_symlink_and_runs_from_any_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "lab"
            link.symlink_to(ROOT / "lab")
            proc = subprocess.run([str(link), "cluster", "status", "--dry-run"], cwd=tmp,
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("vagrant status", proc.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows launcher")
    def test_windows_launcher(self):
        proc = subprocess.run([str(ROOT / "lab.cmd"), "image", "build", "--dry-run"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("docker build", proc.stdout)


if __name__ == "__main__":
    unittest.main()
