import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, FrozenSet, List

import requests as req

ERR_EXIT_CODE: int = 1
SCC_EXIT_CODE: int = 0

TRIGGER_EVENTS: FrozenSet[str] = frozenset(
    {
        "branch_protection_rule",
        "check_run",
        "check_suite",
        "create",
        "delete",
        "deployment",
        "deployment_status",
        "discussion",
        "discussion_comment",
        "fork",
        "gollum",
        "issue_comment",
        "issues",
        "label",
        "milestone",
        "page_build",
        "project",
        "project_card",
        "project_column",
        "public",
        "pull_request",
        "pull_request_comment",
        "pull_request_review",
        "pull_request_review_comment",
        "pull_request_target",
        "push",
        "registry_package",
        "release",
        "repository_dispatch",
        "schedule",
        "status",
        "watch",
        "workflow_call",
        "workflow_dispatch",
        "workflow_run",
    }
)


@dataclass
class Filter:
    def __post_init__(self) -> None:
        if self.event and self.event not in TRIGGER_EVENTS:
            print(str(self), end="")
            print(
                f"{self.event!r} trigger event is not a valid trigger event.",
                file=sys.stderr,
            )
            sys.exit(ERR_EXIT_CODE)

    # PATH PARAMS
    owner: str
    repo: str

    # MANUAL PARAMS
    workflow_name: str

    # QUERY PARAMS
    branch: str
    event: str
    exclude_pull_requests: bool

    def __str__(self) -> str:
        return (
            f"\nRepository: {self.owner}/{self.repo}\n"
            f"Workflow name: {self.workflow_name}\n"
            f"Branch name: {self.branch}\n"
            f"Trigger event: {self.event}\n"
            f"Exclude PRs: {self.exclude_pull_requests}"
            f" {'(default)' if self.exclude_pull_requests else ''}\n\n"
        )


class GithubClient:

    ROOT_ENDPOINT: str = "https://api.github.com"

    def __init__(self, filter_: Filter) -> None:
        self._runs_endpoint = f"/repos/{filter_.owner}/{filter_.repo}/actions/runs"
        self._repo_endpoint = f"/repos/{filter_.owner}/{filter_.repo}"
        self.filter = filter_

    def _build_query_params(self, **query_params: dict) -> str:
        params: str = ""
        for key, value in query_params.items():
            if value:
                params += ("&" if params else "") + f"{key}={value}"
        if params:
            params = "?" + params
        return params

    def _build_url(self, endpoint: str, **query_params) -> str:
        return self.ROOT_ENDPOINT + endpoint + self._build_query_params(**query_params)

    def _make_request(self, endpoint_url: str) -> Any:
        try:
            res = req.get(endpoint_url, timeout=5)
            assert (
                res.status_code == 200
            ), f"\nUnexpected status code: {res.status_code}.\n"
            return res.json()
        except (req.ConnectionError, req.Timeout, AssertionError) as err:
            print(err, file=sys.stderr)
            sys.exit(ERR_EXIT_CODE)

    def _report(method: Callable[["GithubClient"], Any]) -> Any:  # type: ignore[misc] # noqa: N805,E501
        def wrapper(self, *args, **kwargs) -> Any:
            try:
                return method(  # pylint: disable=E1102
                    self, *args, **kwargs
                )  # type: ignore[call-arg]
            except SystemExit as err:
                print(str(self.filter), file=sys.stderr)
                sys.exit(err.code)

        return wrapper

    @_report
    def _get_default_branch(self) -> str:
        url: str = self._build_url(self._repo_endpoint)
        repository: dict = self._make_request(url)
        default_branch: str = repository.get("default_branch", "")
        if not default_branch:
            print("\nThis repository has no default branch.", file=sys.stderr)
            print("Please use the `branch` action input.", file=sys.stderr)
            sys.exit(ERR_EXIT_CODE)
        return default_branch

    @_report
    def _get_runs(self) -> List[dict]:
        if not self.filter.branch:
            self.filter.branch = self._get_default_branch()
        query_params = {
            "branch": self.filter.branch,
            "event": self.filter.event,
            "exclude_pull_requests": self.filter.exclude_pull_requests,
        }
        url: str = self._build_url(
            self._runs_endpoint,
            **query_params,
        )
        data: dict = self._make_request(url)
        if not data["total_count"]:
            print(
                "\nNo workflow runs were found based on the given arguments:",
                file=sys.stderr,
            )
            sys.exit(ERR_EXIT_CODE)
        return data["workflow_runs"]

    @_report
    def get_filtered_runs(self) -> List[dict]:
        runs: List[dict] = self._get_runs()
        filtered_runs: List[dict] = []
        for run in runs:
            if run["repository"]["fork"]:
                continue
            if run["name"].lower() == self.filter.workflow_name.lower():
                filtered_runs.append(run)
        if not filtered_runs:
            print(
                "\nNo workflow runs were found based on the given arguments:",
                file=sys.stderr,
            )
            sys.exit(ERR_EXIT_CODE)
        return filtered_runs


def get_exit_code(runs: List[dict]) -> int:
    lastest_run: dict = runs[0]
    if (lastest_run["status"], lastest_run["conclusion"]) == ("completed", "success"):
        return SCC_EXIT_CODE
    return ERR_EXIT_CODE


def output_conclusion(report: str, exit_code: int) -> None:
    std = sys.stdout if exit_code == SCC_EXIT_CODE else sys.stderr
    status = "succeeded" if exit_code == SCC_EXIT_CODE else "failed"
    print("Based on the given arguments:", end="", file=std)
    print(report, end="", file=std)
    print(f"The latest run has {status}!", file=std)


def str2bool(val: str) -> bool:
    val = val.lower()
    if val in {"n", "no", "f", "false", "off", "0"}:
        return False
    return True  # valid only in `relies_on.py` use case.


def main() -> int:
    filter_ = Filter(
        owner=os.getenv("INPUT_OWNER", "").lower(),
        repo=os.getenv("INPUT_REPOSITORY", "").lower(),
        workflow_name=os.getenv("INPUT_WORKFLOW", "").lower(),
        branch=os.getenv("INPUT_BRANCH", "").lower(),
        event=os.getenv("INPUT_EVENT", "").lower(),
        exclude_pull_requests=str2bool(
            os.getenv("INPUT_EXCLUDE_PULL_REQUESTS", "true")
        ),
    )
    gh_client = GithubClient(filter_)
    runs: List[dict] = gh_client.get_filtered_runs()
    exit_code: int = get_exit_code(runs)
    output_conclusion(str(filter_), exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
