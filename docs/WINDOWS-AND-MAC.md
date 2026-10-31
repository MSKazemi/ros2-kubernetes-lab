# Windows and macOS guide

This lab was built on Linux. This guide explains what works on **Windows**, **Intel Macs** and **Apple Silicon Macs**, which path to pick, and how to avoid the problems that most often break a first attempt.

> **Do not overclaim.** The checks listed under [What has and has not been verified](#what-has-and-has-not-been-verified) were run on Linux. The Windows and macOS steps below follow the vendors' documentation and a simulated Windows checkout; they have not yet been run end to end on real Windows or macOS machines (only the static tooling has run there, on CI runners). If a step fails for you, please [open an issue](https://github.com/MSKazemi/ros2-kubernetes-lab/issues) with the output of `python scripts/doctor.py`.

## 1. Pick your path

| Your machine | Recommended path | Full 3-VM Vagrant lab? |
|---|---|---|
| Windows 10/11, Intel/AMD (x86-64) | [Container path](#3-container-path-all-platforms); optionally [Vagrant on Windows](#4-full-vagrant-lab-on-windows) | Yes, if you have the RAM and can use VirtualBox |
| Windows on Arm | [Container path](#3-container-path-all-platforms) | No (x86-64 box) |
| Intel Mac | [Container path](#3-container-path-all-platforms); optionally [Vagrant on macOS](#5-full-vagrant-lab-on-an-intel-mac) | Yes, if you have the RAM |
| Apple Silicon Mac (M1 or later) | [Container path](#3-container-path-all-platforms) | **No.** The `ubuntu/jammy64` box is x86-64 only |
| Linux | See the main [README](../README.md) | Yes |

Not sure? Run the read-only preflight check. It looks at your CPU type, RAM, installed tools, git line-ending settings and reports which paths fit your machine:

```text
python scripts/doctor.py          # macOS / Linux, or Windows with Python on PATH
py -3 scripts/doctor.py           # Windows, if `python` is not found
```

## 2. Windows only: fix line endings before anything else

Windows Git often converts `LF` to `CRLF` when it checks files out (`core.autocrlf=true`). Shell scripts with `CRLF` endings fail inside the Linux VMs with `/bin/bash^M: bad interpreter`. This repository now ships a [`.gitattributes`](../.gitattributes) that forces `LF` for scripts, the `Vagrantfile`, `Dockerfile` and YAML, so a **fresh clone is safe regardless of your git settings**.

If you cloned **before** this protection existed, re-normalise once:

```powershell
git pull
git rm --cached -r -q .
git reset --hard
```

> `git reset --hard` discards uncommitted changes. Commit or stash your work first.

Then confirm:

```powershell
py -3 scripts/doctor.py
```

Look for `[OK] Scripts, Vagrantfile, Dockerfile and YAML use LF line endings`.

**Other Windows tips**

- Clone into a short path outside OneDrive/Dropbox, for example `C:\src\ros2-kubernetes-lab`. Sync clients lock files and long paths cause errors.
- Use PowerShell or Windows Terminal. In Git Bash, Docker paths such as `/scripts/...` are rewritten by MSYS; prefix the command with `MSYS_NO_PATHCONV=1` if you see a `C:/Program Files/Git/...` path in an error.
- The PowerShell prompt does not support `< file` input redirection ("The '<' operator is reserved for future use"). Use the bind-mount form shown below instead.

## 3. Container path (all platforms)

This path needs only **Docker Desktop** ([Windows](https://docs.docker.com/desktop/setup/install/windows-install/), [macOS](https://docs.docker.com/desktop/setup/install/mac-install/)). It builds the ROS 2 Jazzy image and runs the smoke test **inside one container**. It does not need Vagrant, VirtualBox or Kubernetes, and it does **not** prove cross-node DDS delivery on Kubernetes (see [ROS2/jazzy/README.md](../ROS2/jazzy/README.md)).

From the repository root. Build (the same on every platform):

```text
docker build --platform linux/amd64 --file ROS2/Dockerfile --tag ros-jazzy-lab:local .
```

Run the smoke test:

```bash
# macOS, Linux, WSL, Git Bash (input redirection):
docker run --rm -i --platform linux/amd64 ros-jazzy-lab:local bash -s < scripts/test-ros2-image.sh
```

```powershell
# Windows PowerShell (no "<" operator): mount the scripts folder read-only instead.
docker run --rm --platform linux/amd64 -v "${PWD}/scripts:/scripts:ro" ros-jazzy-lab:local bash /scripts/test-ros2-image.sh
```

Success ends with `PASS: listener received a ROS 2 talker message inside one container.`

**Apple Silicon and other Arm hosts.** The commands above request `linux/amd64`, which is what the project's CI tests. Docker Desktop runs it through emulation, so it works but is slower. The upstream ROS base image also publishes arm64, but **this repository has not tested its own image natively on arm64**. If you drop `--platform linux/amd64` you are trying something unvalidated; please report what you see.

## 4. Full Vagrant lab on Windows

Requirements: Windows 10/11 on x86-64, [VirtualBox](https://www.virtualbox.org/wiki/Downloads), [Vagrant](https://developer.hashicorp.com/vagrant/install), Git, and the RAM described in [Sizing](#6-sizing-the-vms-for-your-machine). Run every command in **Windows PowerShell**, not inside WSL.

```powershell
git clone https://github.com/MSKazemi/ros2-kubernetes-lab.git C:\src\ros2-kubernetes-lab
cd C:\src\ros2-kubernetes-lab
py -3 scripts/doctor.py
$env:VAGRANT_DEFAULT_PROVIDER = "virtualbox"
vagrant up
vagrant ssh controlplane
```

Everything you type **after** `vagrant ssh controlplane` is ordinary Linux/bash inside the VM and is identical on every host operating system.

**Hyper-V, WSL 2 and VirtualBox.** The box `ubuntu/jammy64` is published for VirtualBox only, so Hyper-V cannot run it; setting `VAGRANT_DEFAULT_PROVIDER=virtualbox` avoids Vagrant choosing another provider. When Windows features such as Hyper-V, WSL 2 or Docker Desktop's WSL backend are enabled, VirtualBox may run noticeably slower or fail to start VMs; see the [VirtualBox manual](https://www.virtualbox.org/manual/) for the current guidance on your version.

**Vagrant from WSL.** Running `vagrant up` from inside WSL with a Windows VirtualBox needs extra setup and the repository on the Windows file system; follow [HashiCorp's WSL guide](https://developer.hashicorp.com/vagrant/docs/other/wsl) or use PowerShell instead.

## 5. Full Vagrant lab on an Intel Mac

```bash
brew install --cask virtualbox vagrant      # or install both from their websites
git clone https://github.com/MSKazemi/ros2-kubernetes-lab.git
cd ros2-kubernetes-lab
python3 scripts/doctor.py
vagrant up
vagrant ssh controlplane
```

On first install macOS may block VirtualBox's system extension until you approve it in **System Settings, Privacy & Security** and restart. This is standard VirtualBox-on-macOS behaviour; see the [VirtualBox macOS notes](https://www.virtualbox.org/manual/).

**Apple Silicon.** `vagrant up` stops immediately with an explanation instead of failing halfway through provisioning. Use the [container path](#3-container-path-all-platforms). Advanced users can try an Arm64 VirtualBox box with `LAB_BOX=<box>` and `LAB_ALLOW_ARM=1`; that combination is **untested** and the Kubernetes scripts and Weave Net manifest have not been checked on Arm.

## 6. Sizing the VMs for your machine

The default profile requests about **30 GB RAM and 18 vCPUs** across three VMs. The `Vagrantfile` reads optional environment variables, and with none set it behaves exactly as before.

| Variable | Meaning | Default |
|---|---|---|
| `LAB_PROFILE` | `default` or `small` | `default` |
| `LAB_CP_MEMORY_MB`, `LAB_CP_CPUS` | control-plane VM | 18240 MB, 14 vCPUs (`small`: 8192, 4) |
| `LAB_WORKER_MEMORY_MB`, `LAB_WORKER_CPUS` | each worker VM | 6096 MB, 2 vCPUs (`small`: 4096, 2) |
| `LAB_BOX` | Vagrant box | `ubuntu/jammy64` |
| `LAB_ALLOW_ARM` | set to `1` to skip the Arm stop | unset |

```powershell
# Windows PowerShell
$env:LAB_PROFILE = "small"; vagrant up
```

```bash
# macOS / Linux
LAB_PROFILE=small vagrant up
```

```bat
:: Windows cmd.exe
set LAB_PROFILE=small&& vagrant up
```

> **The `small` profile is not validated end to end.** kubeadm needs at least 2 vCPUs and 2 GB RAM per node, and Prometheus/Grafana need more headroom than that. Treat it as a starting point and tell us what worked.

Values must be positive whole numbers; anything else stops `vagrant up` with a clear message before any VM is created.

## 7. Translating commands

| README says | PowerShell equivalent |
|---|---|
| `export NAME=value` | `$env:NAME = "value"` |
| `NAME=value command` | `$env:NAME = "value"; command` |
| `cmd < file` | `Get-Content file \| cmd` is **not** byte-safe; use a mount (`-v`) or WSL |
| `$(pwd)` | `${PWD}` |
| `python3 script.py`, `python3 -m http.server 8000 --directory site` (website preview) | `py -3 script.py`, `py -3 -m http.server 8000 --directory site`; `python3` is often missing or a Microsoft Store shortcut on Windows |
| `ls`, `cat`, `rm` | work as aliases, but flags differ; prefer `Get-ChildItem`, `Get-Content`, `Remove-Item` |
| `sudo ...` | not needed on the host; only used inside the Linux VMs |

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/bin/bash^M: bad interpreter` during `vagrant up` | Scripts were checked out with CRLF | [Re-normalise](#2-windows-only-fix-line-endings-before-anything-else), then `vagrant provision` |
| `doctor.py` prints `[FAIL] ... contain CRLF` | Same | Same |
| `The '<' operator is reserved for future use` | PowerShell has no input redirection | Use the PowerShell command in [section 3](#3-container-path-all-platforms) |
| `vagrant up` stops with "cannot run on an Arm host" | Apple Silicon or Windows on Arm | Use the [container path](#3-container-path-all-platforms) |
| `LAB_PROFILE must be one of ...` | Typo in the profile name | Use `default` or `small` |
| VirtualBox error about VT-x/AMD-V, or very slow VMs | Virtualisation disabled in firmware, or Hyper-V/WSL 2 competing | Enable virtualisation in BIOS/UEFI; see [section 4](#4-full-vagrant-lab-on-windows) |
| Not enough memory, VMs killed or host freezes | Default profile needs about 30 GB | Use [`LAB_PROFILE=small`](#6-sizing-the-vms-for-your-machine) or the container path |
| `docker: invalid reference format` with a Windows path | Quoting or MSYS path rewriting | Use PowerShell; in Git Bash set `MSYS_NO_PATHCONV=1` |

## What has and has not been verified

| Check | Result |
|---|---|
| Simulated Windows checkout (`core.autocrlf=true`) **without** `.gitattributes` | 36 Linux-bound files get CRLF, the shebang becomes `#!/bin/bash\r` (reproduced locally on Linux) |
| Same checkout **with** `.gitattributes` | 0 CRLF lines in scripts, `Vagrantfile`, YAML; the CRLF data CSV is left byte-identical (local, Linux) |
| `Vagrantfile` sizing variables, validation and Arm stop | Exercised against a stub of the Vagrant API with several environment combinations (local, Linux). Real Vagrant was **not** run |
| Container smoke test, both invocation forms | Passed on Linux amd64 (Docker 29.9.2) |
| `scripts/doctor.py`, Markdown-link, shell-syntax, site and `ruby -c Vagrantfile` checks | Pass on Linux **and** on GitHub's `windows-2025` (amd64) and `macos-15` (arm64) runners with `core.autocrlf=true` forced ([PR #119](https://github.com/MSKazemi/ros2-kubernetes-lab/pull/119) run). Scripts stayed LF on Windows; RAM/CPU detection worked on both. These runners have no Vagrant or VirtualBox, so this covers the tooling only |
| `vagrant up` on Windows, Intel Mac or Apple Silicon | **Not run** |
| PowerShell command, Docker Desktop, VirtualBox on Windows/macOS | **Not run** |
| Native arm64 image | **Not tested** |
