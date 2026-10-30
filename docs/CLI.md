# The `lab` command line

One command for the things the READMEs otherwise make you copy and paste: checking your machine, running the repository checks, building and testing the ROS 2 Jazzy container, and driving the historical Vagrant cluster. It works on Linux, macOS and Windows and needs only **Python 3.8 or newer**.

> **Scope, so the command does not promise more than the lab delivers.** `lab cluster` drives the *historical* Vagrant lab (ROS 2 Foxy, Kubernetes 1.29, Weave Net), which is not a validated or production deployment. `lab image test` is a smoke test **inside one container**; it does not test Kubernetes or cross-node DDS delivery. See the [project status](../README.md) and the [Windows and macOS guide](./WINDOWS-AND-MAC.md).

## 1. Start it

Run it from the repository (any directory inside it works).

| Your shell | Command |
|---|---|
| Linux, macOS (bash, zsh, fish) | `./lab` |
| Windows PowerShell | `.\lab.cmd` |
| Windows `cmd.exe` | `lab.cmd` (or just `lab` once the repository folder is on `PATH`) |
| Any shell, no launcher | `python scripts/lab.py` (Windows: `py -3 scripts\lab.py`) |
| Linux, macOS with `make` | `make` lists shortcuts such as `make check` or `make image-test` |

Everything below writes `lab ...`; use the form from the table. To type just `lab` from anywhere, put the repository folder on your `PATH`, or on Linux/macOS link the launcher: `ln -s "$PWD/lab" ~/.local/bin/lab`. Tab completion is registered for the command name `lab` (bash also registers `./lab`; PowerShell also `lab.cmd`, `.\lab.cmd`), so put `lab` on your `PATH` if you want completion in zsh or fish.

## 2. Ten-second tour

```text
lab                                  # overview, with examples
lab help cluster up                  # help for one command (same as: lab cluster up --help)
lab doctor                           # can this machine run the lab? (read-only)
lab check                            # all repository checks, with a PASS / FAIL / SKIPPED summary
lab image build                      # build the Jazzy image
lab image test                       # smoke-test it (one container only)
lab cluster up --dry-run             # show what would run; start nothing
```

Every command has its own `--help` with an `Examples:` section, and **every command accepts `--dry-run`**, which prints the exact commands instead of running them. That works even when Docker or Vagrant is not installed, so you can see what a command does before you install anything.

## 3. Commands

| Command | What it does |
|---|---|
| `lab doctor` | Runs [`scripts/doctor.py`](../scripts/doctor.py): CPU type, RAM, installed tools, git line endings, and which lab paths fit your machine. Installs and changes nothing. |
| `lab check [what]` | Runs the same static checks as CI. `what` is `all` (default), `preflight`, `shell`, `links`, `site` or `vagrantfile`. |
| `lab image build` | `docker build` of [`ROS2/Dockerfile`](../ROS2/Dockerfile) as `ros-jazzy-lab:local` for `linux/amd64`. Options: `--tag`, `--platform`, `--pull`. |
| `lab image test` | Sends [`scripts/test-ros2-image.sh`](../scripts/test-ros2-image.sh) into a container. Same-container check only. |
| `lab image shell` | Interactive `bash` inside the image. |
| `lab cluster status` | `vagrant status`. |
| `lab cluster up [--profile default\|small]` | `vagrant up`. Shows the cost and asks you to type `yes`. `--profile small` sets `LAB_PROFILE=small` (about 16 GB RAM, 8 vCPUs; not validated end to end). |
| `lab cluster ssh [node]` | `vagrant ssh` into `controlplane` (default), `worker1` or `worker2`. |
| `lab cluster halt` | `vagrant halt`: stop the VMs, keep their disks. |
| `lab cluster destroy` | `vagrant destroy --force` after you type `yes`. |
| `lab completion <shell>` | Print a tab-completion script for `bash`, `zsh`, `fish` or `powershell`. |
| `lab help [command ...]` | Same as adding `--help`. |

Global options, accepted before or after the command: `--dry-run`, `--no-color` (the [`NO_COLOR`](https://no-color.org/) variable also works; colour is decided separately for stdout and stderr, so `lab check 2>log` stays clean), `-v/--verbose`.

### `lab check` in detail

| `what` | Runs | Needs |
|---|---|---|
| `preflight` | `python scripts/doctor.py` (fails on CRLF in Linux-bound files) | Python |
| `shell` | `bash scripts/check-shell.sh` (`bash -n` on the provisioning scripts) | bash |
| `links` | `python scripts/check-markdown-links.py` | Python |
| `site` | `python scripts/validate-site.py` | Python |
| `vagrantfile` | `ruby -c Vagrantfile` (**syntax only**; it does not run Vagrant) | Ruby |

If the tool a check needs is missing, that check is reported as `SKIPPED` and the summary says so; a skipped check is never counted as a pass. The exit status is still 0 for a skip, so scripts that must not miss one should use `lab check --strict`, which exits 1 if anything was skipped. `shell` is also skipped outside a git checkout (for example a ZIP download), because `check-shell.sh` validates tracked files. On Windows, `shell` uses Git for Windows' `bash.exe` and deliberately ignores the WSL launcher in `System32`, which cannot read Windows paths. These are static checks: they do not prove the lab runs.

## 4. Tab completion

Completion scripts are generated from the command line's own definition, so they always match the commands you have. `lab completion <shell>` only **prints** a script; it never edits your shell configuration.

**bash** (no extra package needed for the first two lines; the lazy-loaded file in the last line is picked up only if the `bash-completion` package is installed):

```bash
source <(lab completion bash)                                              # this shell only
echo 'source <(lab completion bash)' >> ~/.bashrc                          # permanent, always works
lab completion bash > ~/.local/share/bash-completion/completions/lab       # permanent, needs bash-completion
```

**zsh** (completion must be initialised: `autoload -Uz compinit && compinit`):

```zsh
source <(lab completion zsh)                    # this shell only
lab completion zsh > "${fpath[1]}/_lab"         # permanent (choose a writable folder on $fpath)
```

**fish:**

```fish
lab completion fish > ~/.config/fish/completions/lab.fish
```

**PowerShell** (Windows PowerShell 5.1 or PowerShell 7):

```powershell
lab completion powershell | Out-String | Invoke-Expression      # this session only
notepad $PROFILE                                                # add the line above to keep it
```

Try it: type `lab cl` and press Tab to get `cluster`; `lab cluster ssh ` and Tab lists the node names; `lab cluster up --p` completes `--profile`. Options are only offered once you start a word with `-`.

For `make`, your shell's own `make` completion lists the targets (bash-completion and zsh both ship one).

## 5. Safety behaviour

- **`cluster up` and `cluster destroy` never act silently.** They print what will happen (for `up`: the resource cost and that the lab is historical) and need you to type `yes`. With no terminal (a script, CI) they **refuse** unless you pass `--yes`.
- **The cost is computed, not guessed.** `cluster up` adds up the memory and vCPUs the Vagrantfile will actually request (profile plus any `LAB_*` overrides) before it asks, rejects an unknown `LAB_PROFILE` or a non-numeric size up front (exit 2), and checks that Vagrant is installed *before* the prompt, so you never type `yes` only to be told it is missing.
- **Vagrant is pinned to this repository.** `lab` sets `VAGRANT_CWD` to the repository and drops `VAGRANT_VAGRANTFILE` for the Vagrant commands it runs, and warns when it overrides a value. A stale variable from another project in your shell cannot send `lab cluster destroy` to that project's VMs.
- **Ctrl-C is handed to the tool.** The first Ctrl-C makes `lab` wait while the wrapped command shuts down by itself (Vagrant does this); a second asks it to terminate and a third kills it. `lab` never kills a running `vagrant up` on your first Ctrl-C.
- **Arm hosts are stopped early.** On Apple Silicon and other Arm machines, `cluster up` explains that the x86-64 VirtualBox box cannot run there and points you to the container path. Set `LAB_ALLOW_ARM=1` only if you know what you are doing; that combination is untested (see the [guide](./WINDOWS-AND-MAC.md#5-full-vagrant-lab-on-an-intel-mac)).
- **No shell is involved.** Commands run as argument lists from the repository root, so file names with spaces and Windows paths are safe, and output of the wrapped tools is never filtered or logged. `--tag` and `--platform` reject values that start with `-` so they cannot be read as docker options. On Windows, tools are looked up on `PATH` only, never in the folder you happen to be in, so a `docker.exe` dropped into a directory cannot be picked up by running `lab` there.
- **Nothing sensitive is printed.** `lab` does not read or show kubeconfigs, tokens or logs. `lab cluster ssh` simply hands your terminal to Vagrant.

## 6. Environment variables and exit codes

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disable colour. |
| `LAB_PROFILE`, `LAB_*` | Read by the `Vagrantfile`; `--profile` sets `LAB_PROFILE` for you. See [sizing](./WINDOWS-AND-MAC.md#6-sizing-the-vms-for-your-machine). |
| `LAB_ALLOW_ARM` | `1` lifts the early Arm stop (untested). |

| Exit status | Meaning |
|---|---|
| 0 | Success (a `SKIPPED` check still exits 0; use `lab check --strict` to fail on it) |
| 1 | A command or check failed, or you declined a prompt |
| 2 | Usage error (unknown command or option) |
| 3 | A required tool is missing; the message says how to install it |

## 7. Troubleshooting

- **`Python 3 was not found`** (launcher, exit 3): install Python 3.8+ from [python.org](https://www.python.org/downloads/). On Windows, the Microsoft Store `python` stub is not a real interpreter; prefer the python.org installer, which also provides the `py` launcher.
- **`bad interpreter` or `^M` errors, or `lab doctor` reports CRLF:** a Windows checkout converted line endings. Follow the re-normalise recipe in the [Windows and macOS guide](./WINDOWS-AND-MAC.md#2-windows-only-fix-line-endings-before-anything-else).
- **PowerShell refuses to run `$PROFILE`:** that is the execution policy, not `lab`. See Microsoft's `about_Execution_Policies`.
- **`lab image test` says the image is missing:** run `lab image build` first, or pass the tag you built with `--tag`. If it says Docker could not be queried, Docker is not running (exit 3).
- **Something unexpected?** Add `--dry-run` to see the commands `lab` would run, and `-v` to see which tool was found. Environment variables (such as `LAB_PROFILE`) are listed after the command rather than as a shell-specific prefix, and `lab image test` additionally sends the script on stdin, so a printed line is a description, not always something to paste.

## 8. What has and has not been verified

**Run on Linux** (Ubuntu 24.04 host, Docker 29.9.2) with 49 unit tests (`python -m unittest discover -s tests`):

- **Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13 and 3.14** all pass, run in the official `python:<version>-slim` containers. Python 3.7 is refused with a clear message (exit 3); 3.6 and older cannot parse the file at all.
- **Shell completion under the real shells:** bash (functional calls of the completion function), fish 3.7 (`fish --no-execute` plus `complete -C` on several inputs) and PowerShell 7.6 (`TabExpansion2` on `lab` and `.\lab.cmd` forms). zsh 5.9 is syntax-checked and the generated function is run with zsh's `_describe` replaced by a stub, so the command-walking and quoting are verified but **zsh's own completion machinery is not**.
- **Safety behaviour:** the confirmation gates, `VAGRANT_CWD` override, first Ctrl-C not killing the child (also with a real SIGINT sent to a real process), closed-pipe handling and the Windows `PATH`-only lookup have tests, and each was confirmed to fail when the protection is removed.
- **Against the real tools:** `lab check` (five checks), `lab doctor`, `lab image build` (all layers were cached) and `lab image test`, which passed with the script piped from Python.

**Run in CI** on GitHub-hosted runners (workflow [`lab-cli.yml`](../.github/workflows/lab-cli.yml), all jobs green on its first full run):

- **Windows Server 2025 (x64):** the unit tests (including PowerShell 7 completion and the `lab.cmd` launcher), both launchers from Windows PowerShell 5.1 and `cmd.exe`, bare `lab` in `cmd.exe` with the folder on `PATH`, and PowerShell 5.1 tab completion for both `lab` and `.\lab.cmd`.
- **macOS 15 (arm64):** the unit tests (including the bash, fish and zsh completion tests), the POSIX launcher, and the Arm guard, which stops `lab cluster up` with exit 3 on a real Arm host.
- **Ubuntu 24.04:** the same tests plus a Python 3.8 to 3.14 matrix in official `python` containers, and a check that `cluster up` and `cluster destroy` refuse without a terminal or `--yes` (the check was confirmed to fail when the gate is removed).

**Not verified:** `lab cluster up` and every other Vagrant command (Vagrant is not installed on the test machines; they are covered only by mocks, `--dry-run` and the prompt tests), a from-scratch `lab image build`, Docker on Windows or macOS, and zsh's own completion machinery (only the generated function is exercised). Nobody has yet used `lab` by hand on real Windows or macOS hardware or tried interactive tab completion in zsh. If something fails for you, please [open an issue](https://github.com/MSKazemi/ros2-kubernetes-lab/issues) with the output of `lab doctor` and the command you ran with `--dry-run`.
