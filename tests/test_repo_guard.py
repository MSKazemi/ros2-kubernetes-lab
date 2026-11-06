"""Tests for scripts/ci/repo_guard.py (job-level repository guard for workflows).

stdlib unittest, offline, writes only inside temporary directories.
Run: python3 -m unittest discover -s tests -p 'test_repo_guard.py' -t .
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import itertools
import os
import re
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

PUBLIC = "MSKazemi/robo-resilience-lab"
PRIVATE = "MSKazemi/robo-resilience-lab-private"

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


def evaluate(expr: str, event: str, ref: str, repo: str) -> bool:
    """Evaluate the tiny GitHub-expression subset used in job conditions."""
    expr = rg.unwrap(expr)
    py = expr.replace("&&", " and ").replace("||", " or ")
    py = re.sub(r"\bgithub\.event_name\b", "EVENT", py)
    py = re.sub(r"\bgithub\.ref\b", "REF", py)
    py = re.sub(r"\bgithub\.repository\b", "REPO", py)
    return bool(eval(py, {"__builtins__": {}}, {"EVENT": event, "REF": ref, "REPO": repo}))  # noqa: S307


@unittest.skipIf(yaml is None, "PyYAML not installed")
class ApplyTests(unittest.TestCase):
    def test_every_job_guarded_and_yaml_valid(self):
        new, changed = rg.apply_text(SAMPLE, PUBLIC)
        self.assertEqual(changed, 2)
        jobs = yaml.safe_load(new)["jobs"]
        for job_id, job in jobs.items():
            self.assertTrue(rg.is_guarded(job.get("if"), PUBLIC), job_id)

    def test_existing_condition_is_parenthesised_not_replaced(self):
        new, _ = rg.apply_text(SAMPLE, PUBLIC)
        cond = yaml.safe_load(new)["jobs"]["publish"]["if"]
        self.assertEqual(
            cond,
            "github.repository == 'MSKazemi/robo-resilience-lab' && "
            "(github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch')",
        )
        self.assertEqual(
            rg.original_condition(cond, PUBLIC),
            "github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'",
        )

    def test_step_level_if_untouched(self):
        new, _ = rg.apply_text(SAMPLE, PUBLIC)
        self.assertIn("        if: github.ref == 'refs/heads/main'\n", new)
        steps = yaml.safe_load(new)["jobs"]["verify"]["steps"]
        self.assertEqual(steps[0]["if"], "github.ref == 'refs/heads/main'")

    def test_everything_else_is_preserved(self):
        new, _ = rg.apply_text(SAMPLE, PUBLIC)
        before, after = yaml.safe_load(SAMPLE), yaml.safe_load(new)
        for job_id in before["jobs"]:
            b, a = dict(before["jobs"][job_id]), dict(after["jobs"][job_id])
            a_if, b_if = a.pop("if", None), b.pop("if", None)
            self.assertEqual(a, b, job_id)  # needs, runs-on, steps identical
            self.assertIsNotNone(a_if)
            self.assertEqual(rg.original_condition(a_if, PUBLIC), b_if)
        self.assertEqual(before[True], after[True])  # `on:` trigger block unchanged

    def test_idempotent(self):
        once, _ = rg.apply_text(SAMPLE, PUBLIC)
        twice, changed = rg.apply_text(once, PUBLIC)
        self.assertEqual(changed, 0)
        self.assertEqual(once, twice)

    def test_semantics_truth_table(self):
        """In the public repo behaviour is unchanged; in any other repo nothing runs."""
        new, _ = rg.apply_text(SAMPLE, PUBLIC)
        jobs_after = yaml.safe_load(new)["jobs"]
        jobs_before = yaml.safe_load(SAMPLE)["jobs"]
        events = ["push", "pull_request", "workflow_dispatch"]
        refs = ["refs/heads/main", "refs/heads/feature", "refs/pull/1/merge"]
        for event, ref in itertools.product(events, refs):
            original = jobs_before["publish"]["if"]
            patched = jobs_after["publish"]["if"]
            self.assertEqual(evaluate(patched, event, ref, PUBLIC), evaluate(original, event, ref, PUBLIC))
            for other in (PRIVATE, "someone-else/fork", "MSKazemi/other"):
                self.assertFalse(evaluate(patched, event, ref, other))
                self.assertFalse(evaluate(jobs_after["verify"]["if"], event, ref, other))
            self.assertTrue(evaluate(jobs_after["verify"]["if"], event, ref, PUBLIC))

    def test_unsupported_constructs_refuse_instead_of_guessing(self):
        for bad in ("if: |\n      github.ref == 'x'", "if: \"github.ref == 'x'\"", "if: github.ref == 'x' # why"):
            text = f"jobs:\n  j:\n    name: J\n    {bad}\n    runs-on: x\n    steps: []\n"
            with self.assertRaises(rg.Unsupported, msg=bad):
                rg.apply_text(text, PUBLIC)

    def test_expression_wrapper_is_unwrapped(self):
        text = "jobs:\n  j:\n    name: J\n    if: ${{ github.ref == 'refs/heads/main' }}\n    runs-on: x\n    steps: []\n"
        new, _ = rg.apply_text(text, PUBLIC)
        cond = yaml.safe_load(new)["jobs"]["j"]["if"]
        self.assertTrue(cond.endswith("&& (github.ref == 'refs/heads/main')"))


G = "github.repository == 'MSKazemi/robo-resilience-lab'"


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
        "'MSKazemi/robo-resilience-lab' == github.repository && success()",
        G + " && github.event.head_commit.message != ' || true && ('",      # operators inside a string literal
        "github.ref == 'it''s a || b' && " + G,                              # escaped quote inside a literal
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
        "github.repository != 'MSKazemi/robo-resilience-lab'",
        "github.repository == 'MSKazemi/robo-resilience-lab-private'",
        "github.repository == 'mskazemi/other'",
        'github.event.head_commit.message == "' + G + '"',
        "github.event.head_commit.message == 'github.repository == ''MSKazemi/robo-resilience-lab'''",
        "github.ref == 'x' && github.event.head_commit.message == '&& github.repository == ''MSKazemi/robo-resilience-lab'''",
        "always() || " + G + " && success()",
        "github['repository'] == 'MSKazemi/robo-resilience-lab'",   # a form we do not understand fails closed
        G + " &&",                                                   # syntax error fails closed
        G + " && (github.ref == 'x'",
        "${{ github.repository == 'MSKazemi/robo-resilience-lab' }} && ${{ true }}",
        None,
        True,
        42,
    ]

    def test_guarded_forms(self):
        for expr in self.GUARDED:
            with self.subTest(expr=expr):
                self.assertTrue(rg.is_guarded(expr, PUBLIC))

    def test_unguarded_forms(self):
        for expr in self.UNGUARDED:
            with self.subTest(expr=expr):
                self.assertFalse(rg.is_guarded(expr, PUBLIC))

    def test_precedence_matches_the_evaluator_for_the_dangerous_case(self):
        expr = G + " && github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'"
        self.assertFalse(rg.is_guarded(expr, PUBLIC))
        # it really does run in a different repository on a dispatch event
        self.assertTrue(evaluate(expr, "workflow_dispatch", "refs/heads/x", PRIVATE))

    def test_is_guarded_agrees_with_the_evaluator_on_generated_conditions(self):
        """Property check: if is_guarded says yes, the condition is False in every other repository."""
        atoms = ["github.ref == 'refs/heads/main'", "github.event_name == 'push'", G]
        seen_guarded = 0
        for a, b, c in itertools.product(atoms, repeat=3):
            for o1, o2 in itertools.product([" && ", " || "], repeat=2):
                for wrap in ("{}", "({})", "!({})"):
                    expr = wrap.format(a + o1 + b + o2 + c)
                    guarded = rg.is_guarded(expr, PUBLIC)
                    seen_guarded += guarded
                    if guarded:
                        for event, ref in itertools.product(["push", "pull_request", "workflow_dispatch"],
                                                            ["refs/heads/main", "refs/heads/x"]):
                            self.assertFalse(evaluate(expr, event, ref, PRIVATE), expr)
        self.assertGreater(seen_guarded, 0)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_apply_wraps_an_unsafe_existing_condition_so_the_result_is_safe(self):
        unsafe = G + " && github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'"
        text = "jobs:\n  j:\n    name: J\n    if: " + unsafe + "\n    runs-on: x\n    steps: []\n"
        new, changed = rg.apply_text(text, PUBLIC)
        self.assertEqual(changed, 1)
        cond = yaml.safe_load(new)["jobs"]["j"]["if"]
        self.assertTrue(rg.is_guarded(cond, PUBLIC))
        self.assertEqual(rg.original_condition(cond, PUBLIC), unsafe)
        for event, ref in itertools.product(["push", "workflow_dispatch"], ["refs/heads/main", "refs/heads/x"]):
            self.assertFalse(evaluate(cond, event, ref, PRIVATE))
            self.assertEqual(evaluate(cond, event, ref, PUBLIC), evaluate(unsafe, event, ref, PUBLIC))
        self.assertEqual(rg.apply_text(new, PUBLIC), (new, 0))  # idempotent

    def test_original_condition_only_accepts_shapes_written_by_apply(self):
        self.assertIsNone(rg.original_condition(G, PUBLIC))
        self.assertEqual(rg.original_condition(G + " && (a == 'b')", PUBLIC), "a == 'b'")
        for odd in (G + " && a && b", "(" + G + ") && a", G + " && (a) || (b)"):
            with self.assertRaises(ValueError, msg=odd):
                rg.original_condition(odd, PUBLIC)

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
            "format('{{0}}', x)": "format('{{0}}', x)",   # braces only inside a literal: nothing to strip
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
        two = "${{ " + G + " }} && ${{ true }}"
        self.assertFalse(rg.is_guarded(two, PUBLIC))
        self.assertFalse(rg.is_guarded("${{ a }} && ${{ b }}", PUBLIC))
        self.assertTrue(rg.is_guarded("${{ " + G + " }}", PUBLIC))
        self.assertTrue(rg.is_guarded("${{" + G + "}}", PUBLIC))

    def test_compose_wraps_a_wrapped_condition_without_corrupting_it(self):
        self.assertEqual(rg.compose(PUBLIC, "${{ a }}"), G + " && (a)")
        self.assertEqual(rg.compose(PUBLIC, "${{a}}"), G + " && (a)")
        self.assertEqual(rg.compose(PUBLIC, "${{ format('{{0}}', x) }}"), G + " && (format('{{0}}', x))")
        self.assertEqual(rg.compose(PUBLIC, "a"), G + " && (a)")
        with self.assertRaises(rg.ExprError):
            rg.compose(PUBLIC, "${{ a }} && ${{ b }}")

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_apply_text_on_valid_wrappers_is_correct_and_idempotent(self):
        for cond, inner in (("${{ a }}", "a"), ("${{a}}", "a"), ("${{ format('{{0}}', x) }}", "format('{{0}}', x)"), ("a", "a")):
            with self.subTest(cond=cond):
                new, changed = rg.apply_text(self.wf(cond), PUBLIC)
                self.assertEqual(changed, 1)
                got = yaml.safe_load(new)["jobs"]["j"]["if"]
                self.assertEqual(got, G + " && (" + inner + ")")
                self.assertTrue(rg.is_guarded(got, PUBLIC))
                self.assertEqual(rg.apply_text(new, PUBLIC), (new, 0))

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_an_already_guarded_wrapped_condition_is_left_alone(self):
        text = self.wf("${{ " + G + " && a }}")
        self.assertEqual(rg.apply_text(text, PUBLIC), (text, 0))

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_apply_refuses_two_wrappers_naming_file_and_job(self):
        tmp = Path(tempfile.mkdtemp(prefix="rg-unwrap-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        f = tmp / "bad.yml"
        original = self.wf("${{ a }} && ${{ b }}")
        f.write_text(original, encoding="utf-8")
        with self.assertRaises(rg.Unsupported):
            rg.apply_text(original, PUBLIC)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = rg.main(["apply", str(f)])
        self.assertNotEqual(code, 0)
        self.assertEqual(code, 2)
        self.assertIn("bad.yml", err.getvalue())
        self.assertIn("job 'j'", err.getvalue())
        self.assertEqual(f.read_text(encoding="utf-8"), original)       # the job was not rewritten

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_check_reports_it_as_unguarded(self):
        tmp = Path(tempfile.mkdtemp(prefix="rg-unwrap-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        f = tmp / "bad.yml"
        f.write_text(self.wf("${{ " + G + " }} && ${{ true }}"), encoding="utf-8")
        problems = rg.check_file(f, PUBLIC)
        self.assertEqual(len(problems), 1)
        self.assertIn("job 'j'", problems[0])
        self.assertIn("unsupported", problems[0])
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(rg.main(["check", str(f)]), 1)

    @unittest.skipIf(yaml is None, "PyYAML not installed")
    def test_other_jobs_in_a_file_are_not_written_when_one_is_unsupported(self):
        text = self.wf("${{ a }} && ${{ b }}") + "  k:\n    name: K\n    runs-on: x\n    steps: []\n"
        with self.assertRaises(rg.Unsupported):
            rg.apply_text(text, PUBLIC)


@unittest.skipIf(yaml is None, "PyYAML not installed")
class CheckTests(unittest.TestCase):
    def _write(self, text: str) -> Path:
        d = Path(tempfile.mkdtemp(prefix="rg-test-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        p = d / "wf.yml"
        p.write_text(text, encoding="utf-8")
        return p

    def test_unguarded_job_is_reported(self):
        problems = rg.check_file(self._write(SAMPLE), PUBLIC)
        self.assertEqual(len(problems), 2)

    def test_guard_only_inside_a_disjunction_does_not_count(self):
        text = (
            "jobs:\n  j:\n    name: J\n"
            "    if: github.ref == 'x' || github.repository == 'MSKazemi/robo-resilience-lab'\n"
            "    runs-on: x\n    steps: []\n"
        )
        self.assertEqual(len(rg.check_file(self._write(text), PUBLIC)), 1)

    def test_guard_for_another_repo_does_not_count(self):
        new, _ = rg.apply_text(SAMPLE, PRIVATE)
        self.assertEqual(len(rg.check_file(self._write(new), PUBLIC)), 2)

    def test_patched_sample_passes(self):
        new, _ = rg.apply_text(SAMPLE, PUBLIC)
        self.assertEqual(rg.check_file(self._write(new), PUBLIC), [])

    def test_cli_exit_codes(self):
        bad = self._write(SAMPLE)
        self.assertEqual(cli("check", str(bad)), 1)
        self.assertEqual(cli("apply", str(bad)), 0)
        self.assertEqual(cli("check", str(bad)), 0)


def cli(*argv: str) -> int:
    """Run repo_guard.main with its console output suppressed."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return rg.main(list(argv))


def strip_guard(cond):
    """The condition without the repository guard; None if there was none. Works guarded or not."""
    if cond is None:
        return None
    return rg.original_condition(cond, PUBLIC) if rg.is_guarded(cond, PUBLIC) else cond


@unittest.skipIf(yaml is None, "PyYAML not installed")
class RealWorkflowTests(unittest.TestCase):
    """Invariants of the guard on the repository's own workflows, in BOTH states:
    unguarded (today's live tree) and already guarded (after the guard patch has landed)."""

    def workflow_files(self, wf_dir: Path) -> list[Path]:
        return sorted([*wf_dir.glob("*.yml"), *wf_dir.glob("*.yaml")])

    def check_dir(self, wf_dir: Path) -> int:
        files = self.workflow_files(wf_dir)
        for f in files:
            original = f.read_text(encoding="utf-8")
            new, _ = rg.apply_text(original, PUBLIC)
            again, changed_again = rg.apply_text(new, PUBLIC)
            self.assertEqual((again, changed_again), (new, 0), f"{f.name}: apply is not idempotent")
            before, after = yaml.safe_load(original), yaml.safe_load(new)
            self.assertEqual(before[True], after[True], f.name)  # `on:` triggers unchanged
            self.assertEqual({k: v for k, v in before.items() if k != "jobs"},
                             {k: v for k, v in after.items() if k != "jobs"}, f.name)
            self.assertEqual(list(before["jobs"]), list(after["jobs"]), f.name)
            for job_id, job in before["jobs"].items():
                got = dict(after["jobs"][job_id])
                cond = got.pop("if")
                self.assertTrue(rg.is_guarded(cond, PUBLIC), f"{f.name}:{job_id}")
                # the pre-guard condition is preserved exactly (None when the job had no `if`)
                self.assertEqual(strip_guard(cond), strip_guard(job.get("if")), f"{f.name}:{job_id}")
                self.assertEqual(got, {k: v for k, v in job.items() if k != "if"}, f"{f.name}:{job_id}")
                needs = job.get("needs", [])
                for dep in [needs] if isinstance(needs, str) else needs:
                    self.assertTrue(rg.is_guarded(after["jobs"][dep]["if"], PUBLIC), f"{f.name}:{job_id}->{dep}")
        return len(files)

    def test_current_workflows_in_whatever_state_they_are(self):
        wf_dir = REPO / ".github" / "workflows"
        if not self.workflow_files(wf_dir):
            self.skipTest("no workflows in this tree")
        self.check_dir(wf_dir)

    def test_already_guarded_copy(self):
        """Guard a scratch copy of the real workflows, then check invariants on that guarded copy."""
        src = REPO / ".github" / "workflows"
        files = self.workflow_files(src)
        if not files:
            self.skipTest("no workflows in this tree")
        tmp = Path(tempfile.mkdtemp(prefix="rg-guarded-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        for f in files:
            guarded, _ = rg.apply_text(f.read_text(encoding="utf-8"), PUBLIC)
            (tmp / f.name).write_text(guarded, encoding="utf-8")
        self.assertEqual(cli("check", *map(str, self.workflow_files(tmp))), 0)
        self.assertEqual(self.check_dir(tmp), len(files))
        # applying the CLI to the guarded copy changes nothing
        before = {f.name: f.read_bytes() for f in self.workflow_files(tmp)}
        self.assertEqual(cli("apply", *map(str, self.workflow_files(tmp))), 0)
        self.assertEqual(before, {f.name: f.read_bytes() for f in self.workflow_files(tmp)})

    def test_external_guarded_directory_if_provided(self):
        """Optional: RRL_GUARDED_WORKFLOWS_DIR=<dir with already-guarded workflows> (e.g. a patched snapshot)."""
        d = os.environ.get("RRL_GUARDED_WORKFLOWS_DIR")
        if not d:
            self.skipTest("RRL_GUARDED_WORKFLOWS_DIR not set")
        n = self.check_dir(Path(d))
        self.assertGreater(n, 0)
        self.assertEqual(cli("check", *map(str, self.workflow_files(Path(d)))), 0)


if __name__ == "__main__":
    unittest.main()
