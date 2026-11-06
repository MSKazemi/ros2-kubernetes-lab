"""Tests for scripts/ci/scan-secrets.py.

All "secrets" below are SYNTHETIC and assembled at runtime from fragments so that
this file never contains a complete token-shaped string (it must pass its own scan).
stdlib unittest, offline. Run:
    python3 -m unittest discover -s tests -p 'test_scan_secrets.py'
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("scan_secrets", REPO / "scripts" / "ci" / "scan-secrets.py")
ss = importlib.util.module_from_spec(_SPEC)
sys.modules["scan_secrets"] = ss
_SPEC.loader.exec_module(ss)  # type: ignore[union-attr]

# ---- synthetic material (fragments joined at runtime) ----
RAND36 = "aB3dE5gH7jK9mN1pQ3sT5vX7zC9fL2hR4tW6"          # 36 mixed chars
GH_TOKEN = "ghp" + "_" + RAND36
GH_PAT = "github_pat" + "_" + "11ABCDEFG0" + "abcdefghijKLMNOPQR" + "stuvwxYZ01"
AWS_ID = "AKIA" + "QWERTYUIOPASDFGH"                     # 4 + 16
AWS_SECRET_VALUE = "wJalrXUtnFEMI" + "K7MDENGbPxRfiCYzq3H5vN9aB"  # 13 + 24 + ... = 40 below
SLACK = "xox" + "b-" + "1234567890-abcdefghijklmnop"
HF = "hf" + "_" + "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
PEM_HEADER = "-----" + "BEGIN RSA PRIVATE" + " KEY-----"
JWT = "eyJ" + "hbGciOiJSUzI1NiJ9" + "." + "eyJ" + "pc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50In0" + "." + "Xy7Zq1Pabc_DEFghiJKLmnOP"
JOIN = "abcdef" + "." + "0123456789abcdef"
CA_HASH = "sha256:" + "a1b2c3d4" * 8
NO_GROUP_SECRET = "Zx9Qw3Er7Ty1" + "Ui5Op8As2Df6" + "Gh4Jk0Lm"   # 32 mixed chars


def scan(text: str, rel: str = "docs/x.md", cfg: "ss.Config | None" = None, profile: str = "public"):
    return ss.scan_text(rel, text, cfg or ss.Config({}), profile)


def rules(findings) -> set[str]:
    return {f.rule for f in findings}


class DetectionTests(unittest.TestCase):
    def test_true_positives(self):
        cases = {
            "private-key-block": PEM_HEADER,
            "aws-access-key-id": f"id = {AWS_ID}",
            "aws-secret-access-key": "aws_secret_access_key = " + ("A1b2C3d4E5" * 4),
            "github-token": f"token {GH_TOKEN}",
            "slack-token": f"SLACK={SLACK}",
            "slack-webhook": "https://hooks" + ".slack.com/services/T01ABCDEF/B02GHIJKL/" + "a1b2c3d4e5f6g7h8i9j0k1l2",
            "huggingface-token": f"HF={HF}",
            "jwt": f"bearer {JWT}",
            "kubeadm-join-token": f"kubeadm join 10.0.0.1:6443 --token {JOIN}",
            "kubeadm-ca-hash": f"--discovery-token-ca-cert-hash {CA_HASH}",
            "kubeconfig-client-key": "    client-key-data: " + ("LS0tLS1CRUdJTiBSU0Eg" * 3),
            "secret-assignment": f"API_KEY={NO_GROUP_SECRET}",
        }
        for rule, line in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, rules(scan(line)), line[:20])
        self.assertIn("github-token", rules(scan(f"x {GH_PAT} y")))

    def test_forbidden_file_names(self):
        cfg = ss.Config({})
        for rel in (".env", ".env.production", "deploy/server.pem", "id_rsa", "kubeconfig", "join-command.sh", "a/b/admin.conf"):
            with self.subTest(rel=rel):
                self.assertIn("forbidden-filename", rules(ss.scan_path_name(rel, cfg, "public")))

    def test_whole_kubeconfig_file(self):
        text = "apiVersion: v1\nkind: Config\nclusters:\n- name: c\nusers:\n- name: u\n  user:\n    token: short\n"
        self.assertIn("kubeconfig-file", rules(scan(text, "kc.yaml")))


class FalsePositiveTests(unittest.TestCase):
    def assertClean(self, text: str, rel: str = "docs/x.md"):
        self.assertEqual(scan(text, rel), [], text)

    def test_placeholders_and_references(self):
        for line in (
            "password: ${{ secrets.DOCKER_PASSWORD }}",
            "username: ${{ secrets.DOCKER_USERNAME }}",
            "export API_KEY=<your-api-key-goes-here>",
            "DB_PASSWORD=changeme-changeme-changeme",
            "token: $(cat /var/run/secrets/token-file-1234567890)",
            "api_key = os.environ['API_KEY_FROM_ENVIRONMENT']",
            "SECRET_TOKEN=${SECRET_TOKEN_FROM_VAULT_ENTRY}",
            "AWS_SECRET_ACCESS_KEY=your-secret-access-key-goes-here-1234567",
        ):
            with self.subTest(line=line):
                self.assertClean(line)

    def test_documented_example_keys(self):
        self.assertClean("AWS example: AKIAIOSFODNN7" + "EXAMPLE")

    def test_key_names_that_only_contain_the_word(self):
        for line in (
            "TOKEN_FILE=/home/vagrant/dashboard-token",
            'SECRET_MARKER = "DOCTOR-TEST-SECRET-MARKER-7c1e"',
            'secretFieldSelector: "type!=kubernetes.io/dockercfg,type!=x"',
            "secretName: grafana-admin-credentials-store",
        ):
            with self.subTest(line=line):
                self.assertClean(line)

    def test_low_entropy_and_prose(self):
        self.assertClean("password: aaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertClean("The token is checked before every request, so tokens expire quickly.")
        self.assertClean("hf_model_name is a variable, hf_ is only a prefix here")
        self.assertClean("uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683")
        self.assertClean("sha256: " + "0123456789abcdef" * 4)

    def test_env_example_files_are_allowed(self):
        cfg = ss.Config({})
        for rel in (".env.example", ".env.sample", ".env.template"):
            self.assertEqual(ss.scan_path_name(rel, cfg, "public"), [], rel)

    def test_public_key_files_and_pub_not_flagged(self):
        self.assertEqual(ss.scan_path_name("keys/id_rsa.pub", ss.Config({}), "public"), [])

    def test_inline_ignore_marker(self):
        self.assertClean(f"id = {AWS_ID}  # scan-secrets: ignore")


class PlaceholderTests(unittest.TestCase):
    """A placeholder must be the WHOLE value; a placeholder word inside a longer value is not one."""

    def found(self, line: str) -> set[str]:
        return {f.rule for f in scan(line)}

    def test_real_looking_values_that_merely_contain_a_placeholder_word_are_found(self):
        values = [
            "Passw0rd-example-2026Xq",
            "token99todo7realvalue",
            "aB3dExampleQ9xK2mZ7vL1pR5s",            # long mixed-case value, 'example' in the middle
            "Zk9fixmeQ2wE8rT5yU1iO3pA7s",
            "R7dummyH2jK9lM4nB6vC1xZ8q",
            "Qw3Er5Ty7Ui9OpplaceholderAs2Df4",
            "Mn8bV5cX2zL9kJ4hG7fD1sAredactedQ",
            "Hj4Kl8Zx2Cv6Bn1Mq3W5e%sR9tY7uI",
            "Ab12<x>Cd34Ef56Gh78Ij90Kl12Mn",
            "pQ8${rT5yU1iO3pA7sD9fG2hJ4kL",
            "yourSecretIs8xK2mZ7vL1pR5sT9",
        ]
        for v in values:
            for line in (f"API_KEY={v}", f"password: {v}", f"token = {v}"):
                with self.subTest(line=line):
                    self.assertIn("secret-assignment", self.found(line))

    def test_whole_value_placeholders_are_not_reported(self):
        values = [
            "changeme", "change-me-change-me-change-me", "changeme-changeme-changeme", "<your-token>", "<your-api-key-goes-here>",
            "xxxxxxxx", "XXXXXXXXXXXXXXXXXXXX", "********************", "................", "${TOKEN}", "${SECRET_TOKEN_FROM_VAULT_ENTRY}",
            "$(cat-/run/secret)", "$MY_SECRET_VARIABLE_VALUE", "{{.Values.secretToken}}", "secrets.DOCKER_PASSWORD_VALUE_X",
            "env.SOME_TOKEN_NAME_LONG_ENOUGH", "example-token-1", "your-secret-access-key-goes-here-1234567",
            "dummy-password-123456789", "placeholder_value_1234567", "sample-api-key-0000000000",
            "ghp_" + "x" * 36, "hf_" + "x" * 34, "AKIA" + "X" * 16,
        ]
        for v in values:
            for line in (f"API_KEY={v}", f"password: {v}"):
                with self.subTest(line=line):
                    self.assertNotIn("secret-assignment", self.found(line))

    def test_token_shaped_placeholders_for_other_rules(self):
        self.assertEqual(scan("x = " + "ghp" + "_" + "x" * 36), [])
        self.assertEqual(scan("id: AKIA" + "X" * 16), [])
        self.assertEqual(scan("AWS example: AKIAIOSFODNN7" + "EXAMPLE"), [])
        self.assertEqual(scan("secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCY" + "EXAMPLEKEY"), [])
        # but a real-shaped key that only ends similarly short of the convention is still found
        self.assertIn("aws-access-key-id", rules(scan("id = " + AWS_ID)))

    def test_is_placeholder_unit(self):
        for v in ("changeme", "<x>", "${A}", "xxxx", "Example-Token-9", "YOUR_API_KEY_HERE", "example"):
            self.assertTrue(ss.is_placeholder(v), v)
        for v in ("Passw0rd-example-2026Xq", "token99todo7realvalue", "token-key-secret", "your-8xK2mZ7vL1pR5s", ""):
            self.assertFalse(ss.is_placeholder(v), v)


class RedactionTests(unittest.TestCase):
    def test_value_never_printed(self):
        secrets = [GH_TOKEN, AWS_ID, SLACK, HF, JWT, JOIN, NO_GROUP_SECRET]
        text = "\n".join(f"v{i} = {s}" for i, s in enumerate(secrets))
        with tempfile.TemporaryDirectory(prefix="ss-test-") as d:
            (Path(d) / "a.txt").write_text(text, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = ss.main(["--root", d, "--no-config", d])
            blob = out.getvalue() + err.getvalue()
            self.assertEqual(code, 1)
            for s in secrets:
                self.assertNotIn(s, blob)
                self.assertNotIn(s[:12], blob)
            with redirect_stdout(out), redirect_stderr(err):
                ss.main(["--root", d, "--no-config", "--json", d])
            for s in secrets:
                self.assertNotIn(s, out.getvalue())

    def test_private_term_not_printed(self):
        cfg = ss.Config({"denylist_terms": [{"id": "t1", "term": "acmecorp-codename", "paths": ["**"]}]})
        found = scan("we talk to AcmeCorp-Codename about it", cfg=cfg)
        self.assertEqual(rules(found), {"t1"})
        self.assertNotIn("acmecorp", found[0].text().lower())


class ConfigAndGlobTests(unittest.TestCase):
    def test_glob_semantics(self):
        g = ss.glob_to_regex
        self.assertTrue(g("alphadir/**").match("alphadir/a/b.md"))
        self.assertFalse(g("alphadir/**").match("docs/alphadir/a.md"))  # anchored (has a slash)
        self.assertTrue(g("*BETAWORD*").match("x/y/MY-BETAWORD-2026.md"))  # basename, any depth
        self.assertTrue(g("/README.md").match("README.md"))
        self.assertFalse(g("/README.md").match("alphadir/README.md"))
        self.assertTrue(g("**/__pycache__/**").match("a/b/__pycache__/c.pyc"))
        self.assertFalse(g("docs/*.md").match("docs/a/b.md"))

    def test_denylist_paths_only_in_public_profile(self):
        cfg = ss.Config({"denylist_paths": [{"glob": "alphadir/**"}]})
        self.assertEqual(rules(ss.scan_path_name("alphadir/a.md", cfg, "public")), {"private-marker-denylist"})
        self.assertEqual(ss.scan_path_name("alphadir/a.md", cfg, "private"), [])
        self.assertEqual(ss.scan_path_name("docs/alphadir-notes.md", cfg, "public"), [])

    def test_term_scope_whole_word_and_disabled(self):
        base = {"id": "p", "term": "gammaword(s)?", "regex": True, "paths": ["docs/**"]}
        cfg = ss.Config({"denylist_terms": [base]})
        self.assertEqual(rules(scan("Our gammawords are fine", "docs/a.md", cfg)), {"p"})
        self.assertEqual(scan("Our gammaword are fine", "src/a.py", cfg), [])        # out of scope
        self.assertEqual(scan("a gammawordish approach", "docs/a.md", cfg), [])      # whole word only
        self.assertEqual(scan("Our gammaword", "docs/a.md", ss.Config({"denylist_terms": [dict(base, enabled=False)]})), [])
        self.assertEqual(scan("Our gammaword", "docs/a.md", cfg, profile="private"), [])

    def test_allow_entry_by_rule_and_wildcard(self):
        text = f"id = {AWS_ID}"
        self.assertEqual(scan(text, "tests/f.py", ss.Config({"allow": [{"path": "tests/**", "rule": "aws-access-key-id"}]})), [])
        self.assertEqual(scan(text, "tests/f.py", ss.Config({"allow": [{"path": "tests/**", "rule": "*"}]})), [])
        self.assertTrue(scan(text, "src/f.py", ss.Config({"allow": [{"path": "tests/**", "rule": "*"}]})))

    def test_unknown_config_key_rejected(self):
        with self.assertRaises(ValueError):
            ss.Config({"denylist": []})

    def test_shipped_config_loads_and_terms_compile(self):
        cfg = ss.Config.load(ss.DEFAULT_CONFIG)
        self.assertTrue(cfg.ignore)

    def test_shipped_config_is_neutral(self):
        """The tracked config carries no private directory or word; those load at run time."""
        cfg = ss.Config.load(ss.DEFAULT_CONFIG)
        self.assertEqual((cfg.deny_paths, cfg.terms), ([], []))

    def test_tracked_ci_files_name_no_private_markers(self):
        # fragments are assembled so this test file does not itself contain the words
        fragments = ("pros" + "pect", "partner" + "ship", "out" + "reach")
        for f in ("scan-secrets.py", "scan-secrets.config.json", "README.md", "repo_guard.py", "run-offline-checks.sh"):
            text = (REPO / "scripts" / "ci" / f).read_text(encoding="utf-8").lower()
            for fragment in fragments:
                self.assertNotIn(fragment, text, f"{f}: {fragment}")


class ChunkedScanTests(unittest.TestCase):
    """Large text is scanned in overlapping windows; nothing straddling a cut may be missed."""

    def lines_found(self, text: str):
        return sorted((f.line, f.rule) for f in ss.scan_text("big.txt", text, ss.Config({})))

    def test_token_straddling_the_window_boundary_is_found(self):
        # one long line (no newline to cut at); the token starts 14 chars before the 64-char cut
        text = "a " * 25 + GH_TOKEN + " " + "b " * 40
        cut = 64
        start = text.index(GH_TOKEN)
        self.assertLess(start, cut)
        self.assertGreater(start + len(GH_TOKEN), cut)
        with mock.patch.object(ss, "CHUNK_CHARS", cut), mock.patch.object(ss, "OVERLAP_CHARS", 48):
            self.assertEqual(self.lines_found(text), [(1, "github-token")])

    def test_token_straddling_with_default_sizes_on_a_multi_megabyte_line(self):
        pad = "z " * ((ss.CHUNK_CHARS - 20) // 2)               # token begins 20 chars before the 1 MiB cut
        text = pad + GH_TOKEN + " " + "z " * 4000
        self.assertEqual(self.lines_found(text), [(1, "github-token")])

    def test_every_alignment_of_the_token_around_the_cut_is_found(self):
        with mock.patch.object(ss, "CHUNK_CHARS", 80), mock.patch.object(ss, "OVERLAP_CHARS", 50):
            for shift in range(0, 60):
                text = "q " * (shift // 2) + "." * (shift % 2) + " " * 3 + "w " * 15 + GH_TOKEN + " end " + "e " * 80
                with self.subTest(shift=shift):
                    self.assertEqual(self.lines_found(text), [(1, "github-token")])

    def test_line_numbers_are_exact_across_windows_and_duplicates_merge(self):
        body = [("k%03d " % i) * 4 for i in range(300)]
        body[199] = "tok " + GH_TOKEN
        body[250] = "api " + HF
        text = "\n".join(body)
        with mock.patch.object(ss, "CHUNK_CHARS", 700), mock.patch.object(ss, "OVERLAP_CHARS", 120):
            self.assertEqual(self.lines_found(text), [(200, "github-token"), (251, "huggingface-token")])

    def test_window_starting_mid_line_does_not_invent_line_start_findings(self):
        # the secret-assignment rule is anchored at line start; mid-line text must not match it
        filler = "word " * 30
        text = filler + " API_KEY=" + NO_GROUP_SECRET + "\n" + "next line\n"
        self.assertEqual(self.lines_found(text), [])  # sanity: not at line start, whole-text scan finds nothing
        with mock.patch.object(ss, "CHUNK_CHARS", 90), mock.patch.object(ss, "OVERLAP_CHARS", 40):
            self.assertEqual(self.lines_found(text), [])

    def test_line_start_findings_still_found_when_lines_are_intact(self):
        text = "".join(f"line {i}\n" for i in range(200)) + f"API_KEY={NO_GROUP_SECRET}\n" + "tail\n" * 50
        with mock.patch.object(ss, "CHUNK_CHARS", 300), mock.patch.object(ss, "OVERLAP_CHARS", 60):
            self.assertEqual(self.lines_found(text), [(201, "secret-assignment")])

    def test_kubeconfig_file_rule_still_sees_the_whole_text(self):
        text = "apiVersion: v1\nkind: Config\nclusters:\n- name: c\nusers:\n- name: u\n  user:\n    token: short\n"
        with mock.patch.object(ss, "CHUNK_CHARS", 40), mock.patch.object(ss, "OVERLAP_CHARS", 10):
            self.assertIn("kubeconfig-file", {f.rule for f in ss.scan_text("kc.yaml", text, ss.Config({}))})

    def test_real_notebooks_are_scanned_not_skipped(self):
        notebooks = sorted((REPO / "DataAnalysis").glob("*.ipynb")) if (REPO / "DataAnalysis").is_dir() else []
        if not notebooks:
            self.skipTest("no notebooks in this tree")
        big = [n for n in notebooks if n.stat().st_size > 1_000_000]
        if not big:
            self.skipTest("no notebook above 1 MB in this tree")
        for nb in big:
            found, skip = ss.scan_file(REPO, str(nb.relative_to(REPO)), ss.Config.load(ss.DEFAULT_CONFIG), "public")
            self.assertIsNone(skip, nb.name)
            self.assertEqual(found, [], nb.name)  # no false positives either


class PrivateDenyFileTests(unittest.TestCase):
    """Private patterns/words come from untracked local files whose location is configured at run time."""

    DENY = "# comment\n\nalphadir/\n*BETAWORD*\nsecretsdir\nexperiments/*\nresults/\n!ignored-negation\n*.pem\n"
    CARVE = "# carve-outs\nexperiments/pub-one/\nsite/results/\n"

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="ss-repo-"))      # the scanned "repository"
        self.cfgdir = Path(tempfile.mkdtemp(prefix="localcfg-"))  # the untracked local files, outside it
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.cfgdir, ignore_errors=True)
        (self.cfgdir / "deny.txt").write_text(self.DENY, encoding="utf-8")
        (self.cfgdir / "carve.txt").write_text(self.CARVE, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("RRL_")}
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def cfg(self) -> "ss.Config":
        cfg = ss.Config({})
        self.assertTrue(cfg.load_private_deny(self.cfgdir / "deny.txt", self.cfgdir / "carve.txt"))
        return cfg

    def test_patterns_match_at_any_depth_and_by_name(self):
        cfg = self.cfg()
        for rel in ("alphadir/a.md", "docs/alphadir/a.md", "x/y/MY-BETAWORD-2026.md", "secretsdir/f", "a/secretsdir/f",
                    "experiments/private-two/a.py", "src/results/out.json"):
            self.assertTrue(cfg.path_denied(rel), rel)
        for rel in ("docs/a.md", "docs/alphadir-notes.md", "experiments", "src/resultsfile.py", "ignored-negation/x"):
            self.assertFalse(cfg.path_denied(rel), rel)

    def test_carveout_reincludes_dir_but_nested_denies_still_apply(self):
        cfg = self.cfg()
        self.assertFalse(cfg.path_denied("experiments/pub-one/run.py"))
        self.assertFalse(cfg.path_denied("experiments/pub-one/tests/t.py"))
        self.assertTrue(cfg.path_denied("experiments/pub-one/results/out.json"))   # nested deny below the carve-out
        self.assertTrue(cfg.path_denied("experiments/pub-one/key.pem"))
        self.assertTrue(cfg.path_denied("experiments/pub-two/run.py"))

    def test_absent_file_is_a_clean_skip(self):
        cfg = ss.Config({})
        self.assertFalse(cfg.load_private_deny(self.cfgdir / "nope.deny"))
        self.assertFalse(cfg.private_deny_loaded)
        self.assertFalse(cfg.path_denied("alphadir/a.md"))

    def _main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ss.main(["--root", str(self.dir), "--no-config", *args])
        return code, out.getvalue() + err.getvalue()

    def _bad_file(self):
        (self.dir / "alphadir").mkdir(exist_ok=True)
        (self.dir / "alphadir" / "a.md").write_text("fine\n", encoding="utf-8")
        (self.dir / "ok.md").write_text("fine\n", encoding="utf-8")

    def test_nothing_configured_prints_exactly_one_skipped_line_and_passes(self):
        self._bad_file()
        code, out = self._main(str(self.dir))
        self.assertEqual(code, 0, out)
        self.assertEqual([l for l in out.splitlines() if "private-marker checks" in l],
                         ["scan-secrets: private-marker checks SKIPPED (not configured); only the secret rules ran"])
        self.assertNotIn("RAN", out)

    def test_flag_configures_and_patterns_are_never_printed(self):
        self._bad_file()
        code, out = self._main("--private-deny", str(self.cfgdir / "deny.txt"), str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("alphadir/a.md: private-marker-denylist", out)
        self.assertIn("private-marker checks RAN using 1 local source(s)", out)
        for secret in ("BETAWORD", "secretsdir", "deny.txt"):
            self.assertNotIn(secret, out)

    def test_environment_variable_configures(self):
        self._bad_file()
        os.environ["RRL_PRIVATE_DENY"] = str(self.cfgdir / "deny.txt")
        os.environ["RRL_PRIVATE_CARVEOUT"] = str(self.cfgdir / "carve.txt")
        code, out = self._main(str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("alphadir/a.md: private-marker-denylist", out)
        self.assertIn("RAN using 1 local source(s)", out)

    def test_flag_beats_environment(self):
        self._bad_file()
        other = self.cfgdir / "other.txt"
        other.write_text("nothing-matches-this\n", encoding="utf-8")
        os.environ["RRL_PRIVATE_DENY"] = str(self.cfgdir / "deny.txt")
        self.assertEqual(self._main("--private-deny", str(other), str(self.dir))[0], 0)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_repo_local_git_config_with_a_relative_path(self):
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True, capture_output=True)
        (self.dir / "localcfg").mkdir()
        shutil.copy2(self.cfgdir / "deny.txt", self.dir / "localcfg" / "deny.txt")
        subprocess.run(["git", "-C", str(self.dir), "config", "--local", "rrl.privateDeny", "localcfg/deny.txt"],
                       check=True, capture_output=True)
        self._bad_file()
        code, out = self._main(str(self.dir / "alphadir"), str(self.dir / "ok.md"))
        self.assertEqual(code, 1, out)
        self.assertIn("alphadir/a.md: private-marker-denylist", out)
        self.assertIn("RAN using 1 local source(s)", out)
        os.environ["RRL_PRIVATE_DENY"] = str(self.cfgdir / "nope.txt")       # environment beats git config
        code, out = self._main(str(self.dir / "alphadir"))
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED (configured file(s) not found)", out)

    def test_configured_but_missing_via_environment_is_a_skip_not_a_claim(self):
        self._bad_file()
        os.environ["RRL_PRIVATE_DENY"] = str(self.cfgdir / "nope.txt")
        code, out = self._main(str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("private-marker checks SKIPPED (configured file(s) not found)", out)
        self.assertNotIn("RAN", out)

    def test_explicit_missing_flag_is_an_error_and_private_profile_and_disable_switch(self):
        self.assertEqual(self._main("--private-deny", str(self.cfgdir / "nope"), str(self.dir))[0], 2)
        self._bad_file()
        self.assertEqual(self._main("--private-deny", str(self.cfgdir / "deny.txt"), "--profile", "private", str(self.dir))[0], 0)
        code, out = self._main("--private-deny", str(self.cfgdir / "deny.txt"), "--no-private-markers", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED (disabled", out)

    def test_markers_file_adds_whole_word_terms_and_is_never_echoed(self):
        (self.dir / "docs").mkdir()
        (self.dir / "docs" / "a.md").write_text("see Epsilonword and epsilonwordish\n", encoding="utf-8")
        markers = self.cfgdir / "markers.txt"
        self.assertEqual(self._main(str(self.dir))[0], 0)
        markers.write_text("# words\nepsilonword\n\n", encoding="utf-8")
        os.environ["RRL_PRIVATE_MARKERS"] = str(markers)
        code, out = self._main(str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("docs/a.md:1: private-marker-term", out)
        self.assertNotIn("epsilonword", out.lower())
        self.assertEqual(self._main("--profile", "private", str(self.dir))[0], 0)

    def test_local_config_adds_terms_when_present(self):
        (self.dir / "docs").mkdir()
        (self.dir / "docs" / "a.md").write_text("mentions deltaword here\n", encoding="utf-8")
        self.assertEqual(self._main(str(self.dir))[0], 0)
        local = self.cfgdir / "local.json"
        local.write_text(json.dumps({"denylist_terms": [{"id": "local-term", "term": "deltaword", "paths": ["docs/**"]}]}),
                         encoding="utf-8")
        os.environ["RRL_SCAN_LOCAL_CONFIG"] = str(local)
        code, out = self._main(str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("docs/a.md:1: local-term", out)
        self.assertNotIn("deltaword", out)


class TrackedFilesNamePrivateSetupTests(unittest.TestCase):
    NEEDLES = (".dual" + "git", ".git-" + "private")  # assembled so this file does not contain them

    def test_no_tracked_ci_or_test_file_names_the_private_setup(self):
        for base in (REPO / "scripts" / "ci", REPO / "tests"):
            for path in sorted(base.rglob("*")):
                if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                for needle in self.NEEDLES:
                    self.assertNotIn(needle, text, f"{path.relative_to(REPO)} contains a private-setup name")

    def test_runner_prunes_other_git_dirs_but_not_dot_github(self):
        text = (REPO / "scripts" / "ci" / "run-offline-checks.sh").read_text(encoding="utf-8")
        self.assertIn("-name '.git-*'", text)
        self.assertNotIn("-name .github", text)
        self.assertNotIn("'.git*'", text)

    def test_ignore_glob_matches_other_git_dirs_not_dot_github(self):
        cfg = ss.Config.load(ss.DEFAULT_CONFIG)
        self.assertTrue(cfg.ignored(".git-alt/objects/x"))
        self.assertTrue(cfg.ignored(".git/config"))
        self.assertFalse(cfg.ignored(".github/workflows/ci.yml"))
        self.assertFalse(cfg.ignored(".gitattributes"))
        self.assertFalse(cfg.ignored(".gitignore"))


class SelectionAndCliTests(unittest.TestCase):
    def setUp(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("RRL_")}
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = Path(tempfile.mkdtemp(prefix="ss-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def w(self, rel: str, text: str | bytes) -> Path:
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(text, encoding="utf-8")
        return p

    def cli(self, *args: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ss.main(["--root", str(self.dir), *args])
        return code, out.getvalue() + err.getvalue()

    def test_clean_tree_exit_zero_and_finding_exit_one(self):
        self.w("a/ok.md", "nothing to see\n")
        self.assertEqual(self.cli("--no-config", str(self.dir))[0], 0)
        self.w("a/bad.txt", f"x {GH_TOKEN}\n")
        code, out = self.cli("--no-config", str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("a/bad.txt:1: github-token", out)

    def test_only_given_paths_are_scanned(self):
        self.w("bad.txt", f"x {GH_TOKEN}\n")
        self.w("ok/clean.txt", "fine\n")
        code, out = self.cli("--no-config", str(self.dir / "ok"))
        self.assertEqual(code, 0)
        self.assertIn("scanned 1 file", out)

    def test_directory_walk_skips_other_git_dirs_but_scans_dot_github(self):
        self.w(".git-alt/a.txt", f"x {GH_TOKEN}\n")
        self.w(".github/b.txt", f"x {HF}\n")
        code, out = self.cli("--no-config", "--no-private-markers", str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn(".github/b.txt:1: huggingface-token", out)
        self.assertNotIn(".git-alt", out)

    def test_large_text_file_over_old_1mb_limit_is_scanned(self):
        """Regression: files above 1 MB (e.g. notebooks) used to be skipped silently."""
        filler = ("x" * 99 + "\n") * 12000  # about 1.2 MB, several lines
        self.w("big.ipynb", filler + f"token {GH_TOKEN}\n" + filler)
        code, out = self.cli("--no-config", "--no-private-markers", str(self.dir))
        self.assertEqual(code, 1)
        self.assertIn("big.ipynb:12001: github-token", out)
        self.assertIn("skipped 0", out)
        self.assertNotIn(GH_TOKEN, out)

    def test_skipped_files_are_counted_by_category(self):
        self.w("bin.dat", b"\0\1\2" + GH_TOKEN.encode())
        self.w("ok.txt", "fine\n")
        code, out = self.cli("--no-config", "--no-private-markers", str(self.dir))
        self.assertEqual(code, 0)
        self.assertIn("scanned 1 file(s), skipped 1 (binary: 1), 0 finding(s)", out)
        self.assertNotIn(GH_TOKEN, out)

    def test_over_cap_symlink_and_unreadable_are_counted_and_listed(self):
        self.w("big.txt", "y" * 3000)
        self.w("ok.txt", "fine\n")
        os.symlink(self.dir / "ok.txt", self.dir / "link.txt")
        locked = self.w("locked.txt", "fine\n")
        os.chmod(locked, 0)
        self.addCleanup(os.chmod, locked, 0o644)
        with mock.patch.object(ss, "HARD_CAP_BYTES", 2000):
            code, out = self.cli("--no-config", "--no-private-markers", "--list-skipped", "--max-mb", "0.0019", str(self.dir))
        self.assertEqual(code, 0, out)
        unreadable = os.access(locked, os.R_OK) is False
        expect = "skipped %d (over-cap: 1, unreadable: 1, symlink: 1)" % 3 if unreadable else "skipped 2 (over-cap: 1, symlink: 1)"
        self.assertIn(expect, out)
        self.assertIn("not scanned (over-cap): big.txt", out)
        self.assertIn("not scanned (symlink): link.txt", out)

    def test_missing_tracked_file_is_counted_not_silent(self):
        found, skip = ss.scan_file(self.dir, "gone.txt", ss.Config({}), "public")
        self.assertEqual((found, skip), ([], "missing"))

    def test_fail_on_skipped_default_off_and_flag_on(self):
        self.w("bin.dat", b"\0\1\2")
        self.w("ok.txt", "fine\n")
        base = ["--no-config", "--no-private-markers", str(self.dir)]
        self.assertEqual(self.cli(*base)[0], 0)
        code, out = self.cli("--fail-on-skipped", *base)
        self.assertEqual(code, 1)
        self.assertIn("skipped 1 (binary: 1)", out)
        self.assertIn("--fail-on-skipped", out)

    def test_fail_on_skipped_category_list(self):
        self.w("bin.dat", b"\0\1\2")
        self.w("ok.txt", "fine\n")
        tail = ["--no-config", "--no-private-markers", str(self.dir)]
        self.assertEqual(self.cli("--fail-on-skipped=over-cap,unreadable", *tail)[0], 0)   # only binary skipped
        self.assertEqual(self.cli("--fail-on-skipped=binary", *tail)[0], 1)
        self.assertEqual(self.cli("--fail-on-skipped=bogus", *tail)[0], 2)

    def test_over_cap_with_fail_flag_and_json_counts(self):
        self.w("big.txt", "y" * 3000)
        with mock.patch.object(ss, "HARD_CAP_BYTES", 2000):
            code, out = self.cli("--no-config", "--no-private-markers", "--fail-on-skipped", "--max-mb", "0.0019", str(self.dir))
            self.assertEqual(code, 1)
            code, out = self.cli("--no-config", "--no-private-markers", "--json", "--max-mb", "0.0019", str(self.dir))
        self.assertEqual(json.loads(out)["skipped"], {"over-cap": 1})
        self.assertEqual(code, 0)

    def test_missing_path_and_missing_config_exit_two(self):
        self.assertEqual(self.cli("--no-config", str(self.dir / "nope"))[0], 2)
        self.assertEqual(self.cli("--config", str(self.dir / "nope.json"), str(self.dir))[0], 2)

    def test_bad_config_exit_two(self):
        cfg = self.w("c.json", "{not json")
        with self.assertRaises(SystemExit):
            ss.Config.load(cfg)
        self.assertEqual(self.cli("--config", str(cfg), str(self.dir))[0], 2)

    def test_ignore_paths_from_config(self):
        self.w("vendor/x.txt", f"x {GH_TOKEN}\n")
        cfg = self.w("c.json", json.dumps({"ignore_paths": ["vendor/**"]}))
        self.assertEqual(self.cli("--config", str(cfg), str(self.dir))[0], 0)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_default_selection_is_git_tracked_files_only(self):
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True, capture_output=True)
        self.w("tracked.txt", f"x {GH_TOKEN}\n")
        self.w("untracked.txt", f"x {HF}\n")
        subprocess.run(["git", "-C", str(self.dir), "add", "tracked.txt"], check=True, capture_output=True)
        code, out = self.cli("--no-config")
        self.assertEqual(code, 1)
        self.assertIn("tracked.txt:1", out)
        self.assertNotIn("untracked.txt", out)
        code, out = self.cli("--no-config", "--include-untracked")
        self.assertIn("untracked.txt:1", out)

    def test_scanner_passes_its_own_source_and_tests(self):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            code = ss.main(["--root", str(REPO), "--no-config", "--no-private-markers", "scripts/ci", "tests/test_scan_secrets.py",
                            "tests/test_repo_guard.py"])
        self.assertEqual(code, 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
