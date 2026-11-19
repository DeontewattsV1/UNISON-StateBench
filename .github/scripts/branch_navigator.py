"""Offline safety and classification tests; do not access GitHub."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch, call

SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/branch_navigator.py"
spec = importlib.util.spec_from_file_location("branch_navigator", SCRIPT)
bn = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = bn
spec.loader.exec_module(bn)

REPO = "example/demo"
SHA = "a" * 40
BASE_SHA = "b" * 40
MERGE_SHA = "c" * 40


def view(**kwargs):
    base = dict(headRefName="feature", baseRefName="main", headRefOid=SHA,
                isCrossRepository=False, isDraft=False, mergeStateStatus="CLEAN",
                reviewDecision="APPROVED", statusCheckRollup=[
                    {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"},
                    {"__typename": "StatusContext", "context": "lint", "state": "SUCCESS"}])
    base.update(kwargs)
    return base


def branch(**kwargs):
    obj = {"name": "feature", "commit": {"sha": SHA}, "protected": False}
    obj.update(kwargs)
    return obj


def pr(number=5):
    return {"number": number, "base": {"ref": "main"},
            "head": {"ref": "feature", "sha": SHA, "repo": {"full_name": REPO}}}


class GateTests(unittest.TestCase):
    def test_clean_green_pr_allowed(self):
        self.assertTrue(bn.pr_gate(view(), "feature", "main", SHA, REPO)[0])

    def test_empty_checks_cannot_mean_green(self):
        self.assertFalse(bn.pr_gate(view(statusCheckRollup=[]), "feature", "main", SHA, REPO)[0])

    def test_skipped_pending_failed_checks_hold(self):
        for conclusion in ("SKIPPED", "FAILURE", None):
            self.assertFalse(bn.pr_gate(view(statusCheckRollup=[
                {"__typename": "CheckRun", "name": "a", "status": "COMPLETED", "conclusion": conclusion}
            ]), "feature", "main", SHA, REPO)[0])

    def test_review_and_conflict_hold(self):
        for data in (view(reviewDecision="REVIEW_REQUIRED"), view(mergeStateStatus="DIRTY"),
                     view(isDraft=True), view(headRefOid="d" * 40), view(isCrossRepository=True)):
            self.assertFalse(bn.pr_gate(data, "feature", "main", SHA, REPO)[0])

    def test_confirmation_exact_and_sha_pinned(self):
        bn.require_mutation_inputs("merge", "feature", "main", SHA, "MERGE feature -> main")
        for phrase, sha in (("MERGE feature -> MAIN", SHA), ("MERGE feature -> main", "bad")):
            with self.assertRaises(bn.Hold):
                bn.require_mutation_inputs("merge", "feature", "main", sha, phrase)

    def test_no_unique_commits_cannot_merge(self):
        c = bn.categorize(branch(), {"ahead_by": 0, "behind_by": 4}, None, None, False, "main", REPO)
        self.assertEqual(c.status, "STALE")
        self.assertEqual(c.operation, "manual")

    def test_dependency_protected_block(self):
        for flag in (False, True):
            c = bn.categorize(branch(protected=flag), {"ahead_by": 1, "behind_by": 0}, pr(), view(), True, "main", REPO)
            self.assertEqual(c.status, "BLOCKED")

    def test_pending_vs_failed_are_distinct(self):
        pending = view(statusCheckRollup=[
            {"__typename": "CheckRun", "name": "build", "status": "IN_PROGRESS", "conclusion": None}
        ])
        failure = view(statusCheckRollup=[
            {"__typename": "CheckRun", "name": "build", "status": "COMPLETED", "conclusion": "FAILURE"}
        ])
        c1 = bn.categorize(branch(), {"ahead_by": 1, "behind_by": 0}, pr(), pending, False, "main", REPO)
        c2 = bn.categorize(branch(), {"ahead_by": 1, "behind_by": 0}, pr(), failure, False, "main", REPO)
        self.assertEqual(c1.status, "PENDING")
        self.assertEqual(c2.status, "BLOCKED")

    def test_ready_merge_and_sync(self):
        c = bn.categorize(branch(), {"ahead_by": 2, "behind_by": 0}, pr(), view(), False, "main", REPO)
        self.assertEqual((c.status, c.operation), ("READY", "merge"))
        c = bn.categorize(branch(), {"ahead_by": 2, "behind_by": 3}, pr(), view(), False, "main", REPO)
        self.assertEqual((c.status, c.operation), ("SYNC", "sync"))

    def test_summary_links_and_next(self):
        c = bn.Candidate("feature", SHA, 2, 0, "READY", "green", "merge", 5)
        report = bn.present_candidates(REPO, "main", [c])
        self.assertIn("NEXT", report)
        self.assertIn("github.com/example/demo/compare/main...feature", report)
        self.assertIn("MERGE feature -> main", report)

    def test_exact_pr_ignores_forks(self):
        remote = pr()
        remote["head"]["repo"]["full_name"] = "some-fork/demo"
        self.assertIsNone(bn.exact_pr([remote], REPO, "main", "feature"))


class MutationTests(unittest.TestCase):
    @patch.object(bn, "repo_info", return_value={"delete_branch_on_merge": True})
    def test_auto_delete_setting_refuses_merge(self, _):
        with self.assertRaisesRegex(bn.Hold, "auto-delete"):
            bn.do_merge(REPO, "feature", "main", SHA, "5", "squash")

    @patch.object(bn, "branch_info")
    @patch.object(bn, "repo_info", return_value={"default_branch": "main"})
    def test_source_sha_cannot_change(self, _, get_branch):
        get_branch.side_effect = [branch(commit={"sha": "d" * 40}), {"commit": {"sha": BASE_SHA}}]
        with self.assertRaisesRegex(bn.Hold, "advanced"):
            bn.verify_preconditions(REPO, "feature", "main", SHA)

    @patch.object(bn, "api")
    def test_postmerge_ci_requires_real_push_workflow(self, get_api):
        get_api.side_effect = [
            {"total_count": 1, "check_runs": [{"name": "tests", "status": "completed", "conclusion": "success"}]},
            {"statuses": [], "state": "pending"},
            {"total_count": 0, "workflow_runs": []},
        ]
        green, reason = bn.postmerge_ci_green(REPO, BASE_SHA)
        self.assertFalse(green)
        self.assertIn("no successful push-triggered", reason)

    @patch.object(bn, "api")
    def test_postmerge_ci_holds_on_red_workflow(self, get_api):
        get_api.side_effect = [
            {"total_count": 1, "check_runs": [{"name": "tests", "status": "completed", "conclusion": "success"}]},
            {"statuses": [], "state": "pending"},
            {"total_count": 1, "workflow_runs": [{"name": "ci", "head_sha": BASE_SHA, "status": "completed", "conclusion": "failure"}]},
        ]
        self.assertFalse(bn.postmerge_ci_green(REPO, BASE_SHA)[0])

    @patch.object(bn, "api")
    @patch.object(bn, "branch_info")
    @patch.object(bn, "compare", return_value={"status": "identical"})
    @patch.object(bn, "open_prs", return_value=[])
    @patch.object(bn, "get_pr")
    @patch.object(bn, "repo_info", return_value={"default_branch": "main"})
    @patch.object(bn, "postmerge_ci_green", return_value=(True, "all green"))
    def test_cleanup_only_after_merge_and_green(self, ci, _, get_pr, prs, comp, branch_info, api):
        get_pr.return_value = {**pr(), "merged_at": "2026-11-19T00:00:00Z", "merge_commit_sha": MERGE_SHA}
        branch_info.side_effect = [branch(), {"commit": {"sha": BASE_SHA}},
                                   {"commit": {"sha": BASE_SHA}}, branch(), {"commit": {"sha": BASE_SHA}}]
        result = bn.cleanup(REPO, "feature", "main", SHA, "5")
        self.assertIn("Deleted merged source", result)
        self.assertTrue(any(c.args[1] == "DELETE" for c in api.call_args_list))

    @patch.object(bn, "api")
    @patch.object(bn, "branch_info")
    @patch.object(bn, "open_prs", return_value=[{"number": 6, "base": {"ref": "feature"}}])
    @patch.object(bn, "get_pr")
    @patch.object(bn, "repo_info", return_value={"default_branch": "main"})
    def test_cleanup_rejects_stacked_prs(self, _, get_pr, prs, branch_info, api):
        get_pr.return_value = {**pr(), "merged_at": "2026-11-19T00:00:00Z", "merge_commit_sha": MERGE_SHA}
        with self.assertRaisesRegex(bn.Hold, "base of open PR"):
            bn.cleanup(REPO, "feature", "main", SHA, "5")
        api.assert_not_called()

    @patch.object(bn, "api")
    @patch.object(bn, "open_prs", return_value=[])
    @patch.object(bn, "get_pr")
    @patch.object(bn, "repo_info", return_value={"default_branch": "main"})
    def test_unmerged_pr_never_deleted(self, _, get_pr, prs, api):
        get_pr.return_value = {**pr(), "merged_at": None, "merge_commit_sha": None}
        with self.assertRaisesRegex(bn.Hold, "not confirmed merged"):
            bn.cleanup(REPO, "feature", "main", SHA, "5")
        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
