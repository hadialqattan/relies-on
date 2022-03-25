"""Relies-on module."""
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, List

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

    """A dataclass for filtering workflow runs.

    In all docstring params below we refer to the workflow
    which we want to check its status (relay on its status) as WFlow.

    :param owner: the username of the repository owner.
    :param repo: the repository name.
    :param workflow_name: the WFlow name.
    :param branch: the branch name where WFlow runs.
    :param event: the trigger event type which triggers WFlow.
    :param exclude_pull_requests: If true runs on pull requests will be omitted.
    :raises SystemExit: when an invalid trigger `event` provided.
    """

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

    """A minimalist client for Github's API.

    :param filter_: a `Filter` object for filtring the workflow runs.
    """

    ROOT_ENDPOINT: str = "https://api.github.com"

    def __init__(self, filter_: Filter) -> None:
        self._runs_endpoint = f"/repos/{filter_.owner}/{filter_.repo}/actions/runs"
        self._repo_endpoint = f"/repos/{filter_.owner}/{filter_.repo}"
        self.filter = filter_

    def _build_query_params(self, query_params: Dict[str, object]) -> str:
        #: builds and returns stringified query params
        #: based on the given key-value `query_params` dict.
        params: str = ""
        for key, value in query_params.items():
            if value:
                params += ("&" if params else "") + f"{key}={value}"
        if params:
            params = "?" + params
        return params

    def _build_url(self, endpoint: str, query_params: Dict[str, object]) -> str:
        #: builds and returns stringified complete url
        #: based on the given `endpoint` and the `query_params` dict.
        return self.ROOT_ENDPOINT + endpoint + self._build_query_params(query_params)

    def _make_request(self, endpoint_url: str) -> Any:
        #: makes a GET request safely and returns jsonified results
        #: based on the given `endpoint_url` (complete url).
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
        #: A decorator outputs the current filtring (`Filter`/`self.filter`)
        #: report in case of SystemExit occurrence.
        def wrapper(self, *args, **kwargs) -> Any:
            try:
                return method(  # pylint: disable=not-callable
                    self, *args, **kwargs
                )  # type: ignore[call-arg]
            except SystemExit as err:
                print(str(self.filter), file=sys.stderr)
                sys.exit(err.code)

        return wrapper

    @_report
    def _get_default_branch(self) -> str:
        #: returns the default branch name based on `self.filter.repository`.
        #: this method should be used when no `self.filter.branch` was specified.
        url: str = self._build_url(self._repo_endpoint, query_params={})
        repository: dict = self._make_request(url)
        default_branch: str = repository.get("default_branch", "")
        if not default_branch:
            print("\nThis repository has no default branch.", file=sys.stderr)
            print("Please use the `branch` action input.", file=sys.stderr)
            sys.exit(ERR_EXIT_CODE)
        return default_branch

    @_report
    def _get_runs(self) -> List[dict]:
        #: returns a list of filtered workflow runs
        #: based on `self.filter` PATH and QUERY params.
        if not self.filter.branch:
            self.filter.branch = self._get_default_branch()
        query_params = {
            "branch": self.filter.branch,
            "event": self.filter.event,
            "exclude_pull_requests": self.filter.exclude_pull_requests,
        }
        url: str = self._build_url(
            self._runs_endpoint,
            query_params,
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
        """Returns a list of filtered workflow runs base on `self.filter`
        values including the manual filtering params.

        :returns: a list of dicts of workflow runs.
        :raises SystemExit: when no workflow run exists
            based on `self.filter` values.
        """
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
    """Determine an exit code based on the given list of workflow `runs`.

    :param runs: a list of dicts of workflow runs.
    :returns: an exit code represents the status of the latest workflow run.
    """
    lastest_run: dict = runs[0]
    if (lastest_run["status"], lastest_run["conclusion"]) == ("completed", "success"):
        return SCC_EXIT_CODE
    return ERR_EXIT_CODE


def output_conclusion(report: str, exit_code: int) -> None:
    """Outputs a conclusion based on the given `report` and `exit_code`.

    :param report: a filtering report.
    :param exit_code: an exit code represents pass or fail status.
    """
    std = sys.stdout if exit_code == SCC_EXIT_CODE else sys.stderr
    status = "succeeded" if exit_code == SCC_EXIT_CODE else "failed"
    print("Based on the given arguments:", end="", file=std)
    print(report, end="", file=std)
    print(f"The latest run has {status}!", file=std)


def str2bool(val: str) -> bool:
    """A custom str to bool casting.

    For `n`, `no`, `f`, `false`, `off`, and `0`
    this function will return False otherwise True.

    :param val: a value to cast.
    :reutrns: casted `val` as bool.
    """
    val = val.lower()
    if val in {"n", "no", "f", "false", "off", "0"}:
        return False
    return True  # valid only in `relies_on.py` use case.


def main() -> int:  # pylint: disable=missing-function-docstring
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
