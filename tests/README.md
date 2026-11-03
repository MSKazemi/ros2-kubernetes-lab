# Automated tests

Hermetic, offline tests for the repository's Python helpers and static
manifest policy. They need no Docker, Vagrant, VirtualBox, kind or Kubernetes
cluster, and they write only inside pytest's temporary directories.

## Run

```sh
python3 -m venv .venv-tests && . .venv-tests/bin/activate
pip install pytest pyyaml
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests
```

`pyyaml` is needed only by `test_manifests.py`, which is skipped with a message
if it is missing. Python 3.9+ is the supported floor; the suite was run on
3.10, 3.11, 3.13 and 3.14.

## What is covered

| File | Target | Checks |
|------|--------|--------|
| `test_check_markdown_links.py` | `scripts/check-markdown-links.py` | broken file/anchor/reference links, code fences and comments ignored, known-issues suppression and stale warning, exit codes, slugs |
| `test_doctor.py` | `scripts/doctor.py` | missing git, CRLF in Linux-executed files, read-only behaviour, no environment leakage (PATH-simulated tools) |
| `test_validate_site.py` | `scripts/validate-site.py` | the real `site/` copy passes; deliberately broken pages, ids, fragments, sitemap and scenario-registry mutations fail |
| `test_manifests.py` | every YAML file in the working tree (excluding `.git`, `.claude`) | YAML parses; no privileged containers or host namespaces; resource limits; no `latest`/untagged images |

## Policy for `test_manifests.py`

Violations are reported, not hidden. Known legacy violations are listed in
`ALLOWLIST` with a reason. An allowlist entry that is no longer violated fails
the suite, so fixed items must be removed from the list.

## Not covered

No cluster, image build or ROS 2 message test runs here; those belong to the
container and multi-VM checks described in `AGENTS.md`.
