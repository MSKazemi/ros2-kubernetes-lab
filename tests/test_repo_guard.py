"""Tests for scripts/ci/repo_guard.py (job-level "public repositories only" guard for workflows).

stdlib unittest, offline, writes only inside temporary directories.
Run: python3 -m unittest discover -s tests -p 'test_repo_guard.py'
"""

from __future__ import annotations

import contextlib
import difflib
import importlib.util
import io
import itertools
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("repo_guard", REPO / "scripts" / "ci" / "repo_guard.py")
rg = importlib.util.module_from_spec(_SPEC)
sys.modules["repo_guard"] = rg
_SPEC.loader.exec_module(rg)  # type: ignore[union-attr]

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

N = "github.event.repository.private == false"        # the reviewed guard, spelled out independently of rg.GUARD
LEGACY = "github.repository == 'MSKazemi/robo-resilience-lab'"
OLD_COMMENT = "# Run only in the public repository; the private mirror and forks execute nothing."
PUBLIC_REPO = "MSKazemi/robo-resilience-lab"

SAMPLE = """\
name: sample
on:
  push:
    branches: [main]
jobs:
  verify:
    name: Verify
    runs-on: ubuntu-24.04
    steps:
      - run: echo verify
        if: github.ref == 'refs/heads/main'

  publish:
    name: Publish
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'
    needs: verify
    runs-on: ubuntu-24.04
    steps:
      - run: echo publish
"""


def evaluate(expr: str, event: str, ref: str, private: bool = False, repo: str = PUBLIC_REPO) -> bool:
    """Evaluate the tiny GitHub-expression subset used in job conditions."""
    py = rg.unwrap(expr).replace("&&", " and ").replace("||", " or ")
    py = re.sub(r"\bgithub\.event_name\b", "EVENT", py)
    py = re.sub(r"\bgithub\.ref\b", "REF", py)
    py = re.sub(r"\bgithub\.event\.repository\.private\b", "PRIVATE", py)
    py = re.sub(r"\bgithub\.repository\b", "REPO", py)
    py = re.sub(r"\bfalse\b", "False", py)
    py = re.sub(r"\btrue\b", "True", py)
    return bool(eval(py, {"__builtins__": {}}, {"EVENT": event, "REF": ref, "REPO": repo, "PRIVATE": private}))  # noqa: S307


def cli(*argv: str) -> int:
    """Run repo_guard.main with its console output suppressed."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return rg.main(list(argv))


def cli_with_output(*argv: str) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rg.main(list(argv))
    return code, out.getvalue() + err.getvalue()


def user_condition(cond):
    """The user's own condition: the guard stripped when `cond` has an apply-written shape, else `cond` itself."""
    if cond is None:
        return None
    try:
        return rg.original_condition(cond)
    except ValueError:
        return cond


def tmpdir(testcase: unittest.TestCase, prefix: str = "rg-test-") -> Path:
    d = Path(tempfile.mkdtemp(prefix=prefix))
    testcase.addCleanup(shutil.rmtree, d, ignore_errors=True)
    return d


class ConstantTests(unittest.TestCase):
    def test_the_guard_is_exactly_the_reviewed_expression(self):
        self.assertEqual(rg.GUARD, N)

    def test_legacy_guard_is_the_old_repository_name_expression(self):
        self.assertEqual(rg.legacy_guard_expr(), LEGACY)


@unittest.skipIf(yaml is None, "PyYAML not installed")
class ApplyTests(unittest.TestCase):
    def test_every_job_guarded_and_yaml_valid(self):
        new, changed = rg.apply_text(SAMPLE)
        self.assertEqual(changed, 2)
        for job_id, job in yaml.safe_load(new)["jobs"].items():
            self.assertEqual(rg.guard_status(job.get("if")), "guarded", job_id)

    def test_existing_condition_is_parenthesised_not_replaced(self):
        new, _ = rg.apply_text(SAMPLE)
        cond = yaml.safe_load(new)["jobs"]["publish"]["if"]
        self.assertEqual(cond, N + " && (github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch')")
        self.assertEqual(rg.original_condition(cond), "github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'")

    def test_step_level_if_untouched(self):
        new, _ = rg.apply_text(SAMPLE)
        self.assertIn("        if: github.ref == 'refs/heads/main'\n", new)
        self.assertEqual(yaml.safe_load(new)["jobs"]["verify"]["steps"][0]["if"], "github.ref == 'refs/heads/main'")

    def test_everything_else_is_preserved(self):
        new, _ = rg.apply_text(SAMPLE)
        before, after = yaml.safe_load(SAMPLE), yaml.safe_load(new)
        for job_id in before["jobs"]:
            b, a = dict(before["jobs"][job_id]), dict(after["jobs"][job_id])
            a_if, b_if = a.pop("if", None), b.pop("if", None)
            self.assertEqual(a, b, job_id)
            self.assertEqual(rg.original_condition(a_if), b_if)
        self.assertEqual(before[True], after[True])

    def test_idempotent(self):
        once, _ = rg.apply_text(SAMPLE)
        twice, changed = rg.apply_text(once)
        self.assertEqual((twice, changed), (once, 0))

    def test_private_repositories_run_nothing_public_ones_and_forks_run_the_original_condition(self):
        new, _ = rg.apply_text(SAMPLE)
        jobs_after, jobs_before = yaml.safe_load(new)["jobs"], yaml.safe_load(SAMPLE)["jobs"]
        original = jobs_before["publish"]["if"]
        for event, ref in itertools.product(["push", "pull_request", "workflow_dispatch"],
                                            ["refs/heads/main", "refs/heads/feature", "refs/pull/1/merge"]):
            patched = jobs_after["publish"]["if"]
            for repo in (PUBLIC_REPO, "someone/fork-of-it", "MSKazemi/robo-resilience-lab-private"):
                # private == true: skipped, whatever the repository is called or the condition says
                self.assertFalse(evaluate(patched, event, ref, private=True, repo=repo))
                self.assertFalse(evaluate(jobs_after["verify"]["if"], event, ref, private=True, repo=repo))
                # private == false (the public repository AND its forks): the original condition decides
                self.assertEqual(evaluate(patched, event, ref, private=False, repo=repo), evaluate(original, event, ref))
                self.assertTrue(evaluate(jobs_after["verify"]["if"], event, ref, private=False, repo=repo))

    def test_unsupported_constructs_refuse_instead_of_guessing(self):
        for bad in ("if: |\n      github.ref == 'x'", "if: \"github.ref == 'x'\"", "if: github.ref == 'x' # why"):
            text = f"jobs:\n  j:\n    name: J\n    {bad}\n    runs-on: x\n    steps: []\n"
            with self.assertRaises(rg.Unsupported, msg=bad):
                rg.apply_text(text)

    def test_expression_wrapper_is_unwrapped(self):
        text = "jobs:\n  j:\n    name: J\n    if: ${{ github.ref == 'refs/heads/main' }}\n    runs-on: x\n    steps: []\n"
        new, _ = rg.apply_text(text)
        self.assertEqual(yaml.safe_load(new)["jobs"]["j"]["if"], N + " && (github.ref == 'refs/heads/main')")


@unittest.skipIf(yaml is None, "PyYAML not installed")
class MigrationTests(unittest.TestCase):
    def wf(self, cond: str | None, comment: bool = True) -> str:
        lines = ["jobs:", "  j:", "    name: J"]
        if cond is not None:
            if comment:
                lines.append("    " + OLD_COMMENT)
            lines.append("    if: " + cond)
        lines += ["    runs-on: x", "    steps: []", ""]
        return "\n".join(lines)

    def test_legacy_guard_with_condition_is_migrated_and_the_condition_kept_verbatim(self):
        orig = "github.ref == 'refs/heads/main' && (github.event_name != 'pull_request' || always())"
        new, changed = rg.apply_text(self.wf(LEGACY + " && (" + orig + ")"))
        self.assertEqual(changed, 1)
        self.assertEqual(yaml.safe_load(new)["jobs"]["j"]["if"], N + " && (" + orig + ")")
        self.assertEqual(rg.original_condition(yaml.safe_load(new)["jobs"]["j"]["if"]), orig)

    def test_bare_legacy_guard_becomes_the_bare_new_guard(self):
        new, changed = rg.apply_text(self.wf(LEGACY))
        self.assertEqual((changed, yaml.safe_load(new)["jobs"]["j"]["if"]), (1, N))

    def test_old_comment_is_replaced_not_duplicated(self):
        new, _ = rg.apply_text(self.wf(LEGACY))
        self.assertNotIn(OLD_COMMENT, new)
        self.assertEqual(new.count(rg.COMMENT), 1)
        new2, _ = rg.apply_text(self.wf(LEGACY, comment=False))
        self.assertEqual(new2.count(rg.COMMENT), 1)

    def test_migration_is_idempotent(self):
        new, _ = rg.apply_text(self.wf(LEGACY + " && (a == 'b')"))
        self.assertEqual(rg.apply_text(new), (new, 0))

    def test_wrapped_legacy_guard_is_migrated(self):
        new, _ = rg.apply_text(self.wf("${{ " + LEGACY + " && (a == 'b') }}"))
        self.assertEqual(yaml.safe_load(new)["jobs"]["j"]["if"], N + " && (a == 'b')")

    def test_legacy_guard_in_a_non_standard_shape_is_refused(self):
        for cond in (LEGACY + " && a && b", "(" + LEGACY + ") && a", "a == 'x' && " + LEGACY):
            with self.subTest(cond=cond):
                with self.assertRaises(rg.Unsupported):
                    rg.apply_text(self.wf(cond))

    def test_a_job_with_both_guards_is_left_alone(self):
        text = self.wf(N + " && " + LEGACY)
        self.assertEqual(rg.apply_text(text), (text, 0))

    def test_the_real_workflows_migrate_back_to_exactly_the_fresh_application(self):
        files = sorted([*(REPO / ".github" / "workflows").glob("*.y*ml")])
        if not files:
            self.skipTest("no workflows in this tree")
        for f in files:
            fresh, _ = rg.apply_text(f.read_text(encoding="utf-8"))
            legacy_copy = fresh.replace(N, LEGACY).replace(rg.COMMENT, OLD_COMMENT)
            self.assertNotEqual(legacy_copy, fresh, f.name)
            self.assertEqual(rg.check_file(f.with_name(f.name), rg.LEGACY_REPO) is not None, True)
            migrated, changed = rg.apply_text(legacy_copy)
            self.assertEqual(migrated, fresh, f.name)
            self.assertGreater(changed, 0, f.name)


G = N  # the table below is written in terms of the reviewed guard


class IsGuardedTableTests(unittest.TestCase):
    """The guard must be a top-level AND-conjunct of the WHOLE condition (&& binds tighter than ||)."""

    GUARDED = [
        G,
        "${{ " + G + " }}",
        G + " && (github.ref == 'refs/heads/main')",
        G + " && github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",
        "(" + G + ") && github.ref == 'refs/heads/main'",
        "(" + G + ")",
        "((" + G + " && github.ref == 'x'))",
        G + " && (github.ref == 'a' || github.ref == 'b')",
        "github.ref == 'x' && " + G,
        "github.ref == 'x' && (" + G + ") && always()",
        "github.event.repository.private==false && a",                                   # spacing is irrelevant
        G + " && github.event.head_commit.message != ' || true && ('",                   # operators inside a string literal
        "github.ref == 'it''s a || b' && " + G,                                           # escaped quote inside a literal
        G + " && contains(github.event.head_commit.message, ') || (')",
        G + " && !cancelled()",
    ]
    UNGUARDED = [
        "",
        "true",
        "github.ref == 'refs/heads/main'",
        G + " && github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'",   # (g && a) || b
        "github.event_name == 'x' || " + G,
        G + " || github.event_name == 'x'",
        G + " || true",
        "(" + G + " && github.ref == 'x') || github.ref == 'y'",
        "(" + G + " || github.ref == 'x') && github.ref == 'y' || true",
        "!(" + G + ") && github.ref == 'x'",
        "!" + G,
        # other spellings of the same idea: only the exact reviewed expression counts
        "!github.event.repository.private",
        "!github.event.repository.private && a",
        "github.event.repository.private != true",
        "github.event.repository.private == 'false'",
        "false == github.event.repository.private",
        "github.event.repository.private == False",
        "github.event.repository['private'] == false",
        "github.event.repository.private == true",
        "github.event.repository.fork == false",
        "github.event.repository.private",
        'github.event.head_commit.message == "' + G + '"',
        "github.event.head_commit.message == 'github.event.repository.private == false'",
        "github.ref == 'x' && github.event.head_commit.message == '&& github.event.repository.private == false'",
        "always() || " + G + " && success()",
        G + " &&",                                                     # syntax error fails closed
        G + " && (github.ref == 'x'",
        "${{ " + G + " }} && ${{ true }}",
        None,
        True,
        42,
    ]
    LEGACY_FORMS = [
        LEGACY,
        LEGACY + " && (a)",
        "${{ " + LEGACY + " }}",
        LEGACY + " && a && b",
    ]

    def test_guarded_forms(self):
        for expr in self.GUARDED:
            with self.subTest(expr=expr):
                self.assertEqual(rg.guard_status(expr), "guarded")
                self.assertTrue(rg.is_guarded(expr))

    def test_unguarded_forms(self):
        for expr in self.UNGUARDED:
            with self.subTest(expr=expr):
                self.assertFalse(rg.is_guarded(expr))
                self.assertEqual(rg.guard_status(expr), "unguarded")

    def test_legacy_forms_are_reported_as_legacy_not_guarded(self):
        for expr in self.LEGACY_FORMS:
            with self.subTest(expr=expr):
                self.assertEqual(rg.guard_status(expr), "legacy")
                self.assertFalse(rg.is_guarded(expr))
        self.assertEqual(rg.guard_status(LEGACY + " || x"), "unguarded")      # a legacy guard that can be bypassed

    def test_precedence_matches_the_evaluator_for_the_dangerous_case(self):
        expr = G + " && github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'"
        self.assertFalse(rg.is_guarded(expr))
        self.assertTrue(evaluate(expr, "workflow_dispatch", "refs/heads/x", private=True))   # it would run in a private repo

    def test_is_guarded_agrees_with_the_evaluator_on_generated_conditions(self):
        """Property check: if is_guarded says yes, the condition is False whenever the repository is private."""
        atoms = ["github.ref == 'refs/heads/main'", "github.event_name == 'push'", G]
        seen_guarded = 0
        for a, b, c in itertools.product(atoms, repeat=3):
            for o1, o2 in itertools.product([" && ", " || "], repeat=2):
                for wrap in ("{}", "({})", "!({})"):
                    expr = wrap.format(a + o1 + b + o2 + c)
                    guarded = rg.is_guarded(expr)
                    seen_guarded += guarded
                    if guarded:
                        for event, ref in itertools.product(["push", "pull_request", "workflow_dispatch"],
                                                            ["refs/heads/main", "refs/heads/x"]):
                            self.assertFalse(evaluate(expr, event, ref, private=True), expr)
        self.assertGreater(seen_guarded, 0)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_apply_wraps_an_unsafe_existing_condition_so_the_result_is_safe(self):
        unsafe = G + " && github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'"
        text = "jobs:\n  j:\n    name: J\n    if: " + unsafe + "\n    runs-on: x\n    steps: []\n"
        new, changed = rg.apply_text(text)
        self.assertEqual(changed, 1)
        cond = yaml.safe_load(new)["jobs"]["j"]["if"]
        self.assertTrue(rg.is_guarded(cond))
        self.assertEqual(rg.original_condition(cond), unsafe)
        for event, ref in itertools.product(["push", "workflow_dispatch"], ["refs/heads/main", "refs/heads/x"]):
            self.assertFalse(evaluate(cond, event, ref, private=True))
            self.assertEqual(evaluate(cond, event, ref, private=False), evaluate(unsafe, event, ref, private=False))
        self.assertEqual(rg.apply_text(new), (new, 0))

    def test_original_condition_only_accepts_shapes_written_by_apply(self):
        self.assertIsNone(rg.original_condition(G))
        self.assertIsNone(rg.original_condition(LEGACY))
        self.assertEqual(rg.original_condition(G + " && (a == 'b')"), "a == 'b'")
        self.assertEqual(rg.original_condition(LEGACY + " && (a == 'b')"), "a == 'b'")
        for odd in (G + " && a && b", "(" + G + ") && a", G + " && (a) || (b)", LEGACY + " && a", "plain == 'condition'"):
            with self.assertRaises(ValueError, msg=odd):
                rg.original_condition(odd)

    def test_tokenizer_keeps_operators_inside_literals_inside_the_literal(self):
        toks = rg._tokenize("a == '&& || ( ) ! ''x'''")
        self.assertEqual([k for k, _ in toks], ["name", "op", "str"])
        self.assertEqual(toks[2][1], "&& || ( ) ! 'x'")


class UnwrapTests(unittest.TestCase):
    """`${{ }}` is removed only when it is ONE wrapper around the whole expression."""

    def wf(self, cond: str) -> str:
        return "jobs:\n  j:\n    name: J\n    if: " + cond + "\n    runs-on: x\n    steps: []\n"

    def test_valid_wrappers_and_plain_conditions(self):
        cases = {
            "${{ a }}": "a",
            "${{a}}": "a",
            "${{   github.ref == 'x'   }}": "github.ref == 'x'",
            "${{ format('{{0}}', x) }}": "format('{{0}}', x)",
            "${{ github.event.head_commit.message == '}}' }}": "github.event.head_commit.message == '}}'",
            "${{ x == 'a ${{ b' }}": "x == 'a ${{ b'",
            "a": "a",
            "github.ref == 'refs/heads/main'": "github.ref == 'refs/heads/main'",
            "format('{{0}}', x)": "format('{{0}}', x)",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(rg.unwrap(text), expected)

    def test_text_outside_a_single_wrapper_is_refused(self):
        for text in ("${{ a }} && ${{ b }}", "x ${{ a }}", "${{ a }} y", "a && ${{ b }}", "${{ a", "a }}", "${{ a }} }}",
                     "${{ ${{ a }} }}", "${{ x == 'oops }}"):
            with self.subTest(text=text):
                with self.assertRaises(rg.ExprError):
                    rg.unwrap(text)

    def test_is_guarded_is_false_for_unsupported_shapes(self):
        self.assertFalse(rg.is_guarded("${{ " + G + " }} && ${{ true }}"))
        self.assertFalse(rg.is_guarded("${{ a }} && ${{ b }}"))
        self.assertTrue(rg.is_guarded("${{ " + G + " }}"))
        self.assertTrue(rg.is_guarded("${{" + G + "}}"))

    def test_compose_wraps_a_wrapped_condition_without_corrupting_it(self):
        self.assertEqual(rg.compose("${{ a }}"), G + " && (a)")
        self.assertEqual(rg.compose("${{a}}"), G + " && (a)")
        self.assertEqual(rg.compose("${{ format('{{0}}', x) }}"), G + " && (format('{{0}}', x))")
        self.assertEqual(rg.compose("a"), G + " && (a)")
        self.assertEqual(rg.compose(None), G)
        with self.assertRaises(rg.ExprError):
            rg.compose("${{ a }} && ${{ b }}")

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_apply_text_on_valid_wrappers_is_correct_and_idempotent(self):
        for cond, inner in (("${{ a }}", "a"), ("${{a}}", "a"), ("${{ format('{{0}}', x) }}", "format('{{0}}', x)"), ("a", "a")):
            with self.subTest(cond=cond):
                new, changed = rg.apply_text(self.wf(cond))
                self.assertEqual(changed, 1)
                got = yaml.safe_load(new)["jobs"]["j"]["if"]
                self.assertEqual(got, G + " && (" + inner + ")")
                self.assertTrue(rg.is_guarded(got))
                self.assertEqual(rg.apply_text(new), (new, 0))

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_an_already_guarded_wrapped_condition_is_left_alone(self):
        text = self.wf("${{ " + G + " && a }}")
        self.assertEqual(rg.apply_text(text), (text, 0))

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_apply_refuses_two_wrappers_naming_file_and_job(self):
        f = tmpdir(self, "rg-unwrap-") / "bad.yml"
        original = self.wf("${{ a }} && ${{ b }}")
        f.write_text(original, encoding="utf-8")
        with self.assertRaises(rg.Unsupported):
            rg.apply_text(original)
        code, out = cli_with_output("apply", str(f))
        self.assertEqual(code, 2)
        self.assertIn("bad.yml", out)
        self.assertIn("job 'j'", out)
        self.assertEqual(f.read_text(encoding="utf-8"), original)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_check_reports_it_as_unguarded(self):
        f = tmpdir(self, "rg-unwrap-") / "bad.yml"
        f.write_text(self.wf("${{ " + G + " }} && ${{ true }}"), encoding="utf-8")
        problems = rg.check_file(f)
        self.assertEqual(len(problems), 1)
        self.assertIn("job 'j'", problems[0])
        self.assertIn("unsupported", problems[0])
        self.assertEqual(cli("check", str(f)), 1)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_other_jobs_in_a_file_are_not_written_when_one_is_unsupported(self):
        text = self.wf("${{ a }} && ${{ b }}") + "  k:\n    name: K\n    runs-on: x\n    steps: []\n"
        with self.assertRaises(rg.Unsupported):
            rg.apply_text(text)


@unittest.skipIf(yaml is None, "PyYAML not installed")
class CheckTests(unittest.TestCase):
    def write(self, text: str, name: str = "wf.yml") -> Path:
        p = tmpdir(self) / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_unguarded_job_is_reported(self):
        self.assertEqual(len(rg.check_file(self.write(SAMPLE))), 2)

    def test_guard_only_inside_a_disjunction_does_not_count(self):
        text = "on: push\njobs:\n  j:\n    name: J\n    if: github.ref == 'x' || " + N + "\n    runs-on: x\n    steps: []\n"
        self.assertEqual(len(rg.check_file(self.write(text))), 1)

    def test_legacy_guard_fails_the_check_and_says_to_run_apply(self):
        text = "on: push\njobs:\n  j:\n    name: J\n    if: " + LEGACY + " && (a == 'b')\n    runs-on: x\n    steps: []\n"
        problems = rg.check_file(self.write(text))
        self.assertEqual(len(problems), 1)
        self.assertIn("LEGACY", problems[0])
        self.assertIn("apply", problems[0])
        f = self.write(text)
        self.assertEqual(cli("check", str(f)), 1)
        self.assertEqual(cli("apply", str(f)), 0)
        self.assertEqual(cli("check", str(f)), 0)

    def test_other_spellings_fail_the_check(self):
        for cond in ("!github.event.repository.private", "github.event.repository.private != true",
                     "github.event.repository.private == 'false'"):
            text = "on: push\njobs:\n  j:\n    name: J\n    if: " + cond + "\n    runs-on: x\n    steps: []\n"
            with self.subTest(cond=cond):
                self.assertEqual(len(rg.check_file(self.write(text))), 1)

    def test_patched_sample_passes(self):
        new, _ = rg.apply_text(SAMPLE)
        self.assertEqual(rg.check_file(self.write(new)), [])

    def test_cli_exit_codes(self):
        bad = self.write(SAMPLE)
        self.assertEqual(cli("check", str(bad)), 1)
        self.assertEqual(cli("apply", str(bad)), 0)
        self.assertEqual(cli("check", str(bad)), 0)

    def job(self) -> str:
        return "jobs:\n  j:\n    name: J\n    if: " + N + "\n    runs-on: x\n    steps: []\n"

    def test_schedule_trigger_fails_in_every_on_form(self):
        forms = {
            "string": "on: schedule\n",
            "list": "on: [push, schedule]\n",
            "block list": "on:\n  - push\n  - schedule\n",
            "mapping": "on:\n  push:\n  schedule:\n    - cron: '0 3 * * *'\n",
            "quoted key": "'on':\n  schedule:\n    - cron: '0 3 * * *'\n",
        }
        for label, on in forms.items():
            with self.subTest(form=label):
                p = self.write(on + self.job())
                problems = rg.check_file(p)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("schedule", problems[0])
                self.assertIn("no repository payload", problems[0])
                self.assertEqual(cli("check", str(p)), 1)

    def test_triggers_that_carry_a_repository_payload_pass(self):
        for event in ("push", "pull_request", "pull_request_target", "workflow_dispatch", "workflow_run", "repository_dispatch",
                      "release", "issues", "workflow_call"):
            for on in (f"on: {event}\n", f"on: [{event}, push]\n", f"on:\n  {event}:\n"):
                with self.subTest(on=on):
                    self.assertEqual(rg.check_file(self.write(on + self.job())), [])

    def test_apply_warns_about_schedule_but_check_is_the_gate(self):
        p = self.write("on:\n  schedule:\n    - cron: '0 3 * * *'\njobs:\n  j:\n    name: J\n    runs-on: x\n    steps: []\n")
        code, out = cli_with_output("apply", str(p))
        self.assertEqual(code, 0)
        self.assertIn("WARNING", out)
        self.assertIn("schedule", out)
        self.assertEqual(cli("check", str(p)), 1)


def git_head_workflows() -> dict[str, str]:
    """Workflow files as committed at HEAD (empty if git or HEAD is unavailable)."""
    try:
        names = subprocess.run(["git", "-C", str(REPO), "ls-tree", "--name-only", "HEAD", ".github/workflows/"],
                               capture_output=True, text=True, timeout=30, check=True).stdout.split()
        return {n.rsplit("/", 1)[1]: subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{n}"], capture_output=True,
                                                    text=True, timeout=30, check=True).stdout
                for n in names if n.endswith((".yml", ".yaml"))}
    except (OSError, subprocess.SubprocessError):
        return {}


@unittest.skipIf(yaml is None, "PyYAML not installed")
class RealWorkflowTests(unittest.TestCase):
    """Invariants of the guard on the repository's own workflows in WHATEVER state they are
    (unguarded, legacy-guarded or already guarded), and a full run on the files committed at HEAD."""

    def workflow_files(self, wf_dir: Path) -> list[Path]:
        return sorted([*wf_dir.glob("*.yml"), *wf_dir.glob("*.yaml")])

    def check_dir(self, wf_dir: Path) -> int:
        files = self.workflow_files(wf_dir)
        for f in files:
            original = f.read_text(encoding="utf-8")
            new, _ = rg.apply_text(original)
            again, changed_again = rg.apply_text(new)
            self.assertEqual((again, changed_again), (new, 0), f"{f.name}: apply is not idempotent")
            before, after = yaml.safe_load(original), yaml.safe_load(new)
            self.assertEqual(before[True], after[True], f.name)
            self.assertEqual({k: v for k, v in before.items() if k != "jobs"}, {k: v for k, v in after.items() if k != "jobs"}, f.name)
            self.assertEqual(list(before["jobs"]), list(after["jobs"]), f.name)
            for job_id, job in before["jobs"].items():
                got = dict(after["jobs"][job_id])
                cond = got.pop("if")
                self.assertTrue(rg.is_guarded(cond), f"{f.name}:{job_id}")
                self.assertEqual(user_condition(cond), user_condition(job.get("if")), f"{f.name}:{job_id}")
                self.assertEqual(got, {k: v for k, v in job.items() if k != "if"}, f"{f.name}:{job_id}")
                needs = job.get("needs", [])
                for dep in [needs] if isinstance(needs, str) else needs:
                    self.assertTrue(rg.is_guarded(after["jobs"][dep]["if"]), f"{f.name}:{job_id}->{dep}")
        return len(files)

    def test_current_workflows_in_whatever_state_they_are(self):
        wf_dir = REPO / ".github" / "workflows"
        if not self.workflow_files(wf_dir):
            self.skipTest("no workflows in this tree")
        self.check_dir(wf_dir)

    def test_no_current_workflow_uses_a_trigger_without_a_repository_payload(self):
        wf_dir = REPO / ".github" / "workflows"
        for f in self.workflow_files(wf_dir):
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            self.assertFalse(set(rg.trigger_names(doc)) & rg.NO_REPO_PAYLOAD_EVENTS, f.name)

    def test_already_guarded_copy(self):
        files = self.workflow_files(REPO / ".github" / "workflows")
        if not files:
            self.skipTest("no workflows in this tree")
        tmp = tmpdir(self, "rg-guarded-")
        for f in files:
            guarded, _ = rg.apply_text(f.read_text(encoding="utf-8"))
            (tmp / f.name).write_text(guarded, encoding="utf-8")
        self.assertEqual(cli("check", *map(str, self.workflow_files(tmp))), 0)
        self.assertEqual(self.check_dir(tmp), len(files))
        before = {f.name: f.read_bytes() for f in self.workflow_files(tmp)}
        self.assertEqual(cli("apply", *map(str, self.workflow_files(tmp))), 0)
        self.assertEqual(before, {f.name: f.read_bytes() for f in self.workflow_files(tmp)})

    def test_workflows_committed_at_head_apply_then_check_and_differ_only_by_the_guard(self):
        committed = git_head_workflows()
        if not committed:
            self.skipTest("git HEAD workflows unavailable")
        tmp = tmpdir(self, "rg-head-")
        for name, text in committed.items():
            (tmp / name).write_text(text, encoding="utf-8")
        self.assertEqual(cli("apply", *map(str, self.workflow_files(tmp))), 0)
        self.assertEqual(cli("check", *map(str, self.workflow_files(tmp))), 0)
        self.assertEqual(cli("apply", *map(str, self.workflow_files(tmp))), 0)   # idempotent on disk
        for name, text in committed.items():
            after = (tmp / name).read_text(encoding="utf-8")
            for line in difflib.unified_diff(text.splitlines(), after.splitlines(), lineterm="", n=0):
                if line.startswith(("---", "+++", "@@")):
                    continue
                body = line[1:].strip()
                if line.startswith("+"):
                    self.assertTrue(body == rg.COMMENT or body.startswith("if: " + N), f"{name}: unexpected added line {line!r}")
                else:   # removed lines can only be the previous job-level `if:` (legacy guard or the user's own) or the old comment
                    self.assertTrue(body.startswith("if:") or body in (OLD_COMMENT, rg.COMMENT), f"{name}: unexpected removed line {line!r}")

    def test_external_guarded_directory_if_provided(self):
        """Optional: RRL_GUARDED_WORKFLOWS_DIR=<dir with already-guarded workflows> (e.g. a patched snapshot)."""
        d = os.environ.get("RRL_GUARDED_WORKFLOWS_DIR")
        if not d:
            self.skipTest("RRL_GUARDED_WORKFLOWS_DIR not set")
        self.assertGreater(self.check_dir(Path(d)), 0)
        self.assertEqual(cli("check", *map(str, self.workflow_files(Path(d)))), 0)


if __name__ == "__main__":
    unittest.main()
