"""Relies-on testing module."""
# pylint: disable=C0116,W0613,W0212,W0201,R0913
import sys
from collections import OrderedDict
from contextlib import contextmanager
from io import StringIO
from typing import Iterator, List
from unittest import mock

import pytest

from relies_on import (
    ERR_EXIT_CODE,
    SCC_EXIT_CODE,
    Filter,
    GithubClient,
    get_exit_code,
    main,
    output_conclusion,
    str2bool,
)

MOCK = "relies_on.%s"
MOCK_GITHUB = MOCK % "GithubClient.%s"


@contextmanager
def std_redirect(is_stderr: bool) -> Iterator[StringIO]:
    """Redirect stdout/err to a variable.

    :param is_stderr: weather to capture `sys.stderr` or `sys.stdout`.
    :returns: Iterator of `StringIO` represents `sys.stdout/stderr`.
    """
    std_capture = StringIO()
    if is_stderr:
        default_std = sys.stderr
        sys.stderr = std_capture
    else:
        default_std = sys.stdout
        sys.stdout = std_capture
    yield std_capture
    if is_stderr:
        sys.stderr = default_std
    else:
        sys.stdout = default_std


class TestFilter:

    """`Filter` dataclass methods test cases."""

    def test_invalid_event(self):
        try:
            Filter(
                owner="",
                repo="",
                workflow_name="",
                branch="",
                event="INVALID_TRIGGER_EVENT",
                exclude_pull_requests=True,
            )
            assert False, "SystemExit should have been raised"
        except SystemExit as err:
            assert err.code == ERR_EXIT_CODE

    def test_str_dunder(self):
        kwargs = dict(
            owner="hadialqattan",
            repo="relies-on",
            workflow_name="CI",
            branch="main",
            event="push",
            exclude_pull_requests=True,
        )
        report = str(Filter(**kwargs))
        for k, val in kwargs.items():
            assert str(val) in report, f"{k!r} should have been included on the report."


class TestGithubClient:

    """`GithubClient` class methods test cases."""

    def setup_method(self, method):
        self.empty_filter: Filter = Filter("", "", "", "", "", True)
        self.ghc: GithubClient = GithubClient(self.empty_filter)

    @pytest.mark.parametrize(
        "query_params, expected",
        [
            pytest.param(
                OrderedDict(),
                "",
                id="no-params",
            ),
            pytest.param(
                OrderedDict({"event": "push", "branch": "main"}),
                "?event=push&branch=main",
                id="params",
            ),
        ],
    )
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_build_query_params(
        self, post_init, query_params: OrderedDict, expected: str
    ):
        results = self.ghc._build_query_params(query_params)
        assert results == expected

    @pytest.mark.parametrize(
        "endpoint, expected",
        [
            pytest.param(
                "/test/endpoint",
                GithubClient.ROOT_ENDPOINT + "/test/endpoint?test=r",
                id="endpoint",
            )
        ],
    )
    @mock.patch(MOCK_GITHUB % "_build_query_params", side_effect=["?test=r"])
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_build_url(
        self, post_init, _build_query_params, endpoint: str, expected: str
    ):
        results = self.ghc._build_url(endpoint, query_params={})
        assert results == expected

    @pytest.mark.parametrize(
        "status_code, data, expec_data",
        [
            pytest.param(
                200,
                {"data": "..."},
                {"data": "..."},
                id="success",
            ),
            pytest.param(
                404,
                {"data": "not-found"},
                {},
                id="not-found",
            ),
        ],
    )
    @mock.patch(MOCK % "req.get")
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_make_request(
        self, post_init, get, status_code: int, data: dict, expec_data: dict
    ):
        get.return_value.json.return_value = data
        type(get.return_value).status_code = mock.PropertyMock(return_value=status_code)
        with std_redirect(is_stderr=True) as stderr:
            try:
                assert self.ghc._make_request("DOES NOT MATTER") == expec_data
            except SystemExit as err:
                assert err.code == ERR_EXIT_CODE
                assert str(status_code) in stderr.getvalue()

    @pytest.mark.parametrize(
        "given_report, raise_exit",
        [
            pytest.param(
                "REPORT",
                False,
                id="no-err",
            ),
            pytest.param(
                "REPORT",
                True,
                id="raise SystemExit",
            ),
        ],
    )
    @mock.patch(MOCK % "Filter.__str__")
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_report(
        self, __post_init__, str_dunder, given_report: str, raise_exit: bool
    ):
        str_dunder.return_value = given_report
        with std_redirect(is_stderr=True) as stderr:
            MockGithubClient = type(  # noqa: N806
                "MockGithubClient", GithubClient.__bases__, dict(GithubClient.__dict__)
            )
            ghc: GithubClient = MockGithubClient(self.empty_filter)

            @ghc._report.__func__  # type: ignore # pylint: disable=E1101
            def function(self):
                if raise_exit:
                    raise sys.exit(ERR_EXIT_CODE)

            setattr(MockGithubClient, "function", function)
            try:
                ghc.function()  # type: ignore # pylint: disable=E1101
            except SystemExit as err:
                assert err.code == ERR_EXIT_CODE
                assert f"{given_report}\n" == stderr.getvalue()

    @pytest.mark.parametrize(
        "repo_data, expec_name",
        [
            pytest.param(
                {"default_branch": "master"},
                "master",
                id="master",
            ),
            pytest.param(
                {"default_branch": ""},
                "",
                id="no-default[1]",
            ),
            pytest.param(
                {"no default_branch key": ""},
                "",
                id="no-default[2]",
            ),
        ],
    )
    @mock.patch(MOCK_GITHUB % "_make_request")
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_get_default_branch(
        self, post_init, _make_request, repo_data: dict, expec_name: str
    ):
        _make_request.return_value = repo_data
        with std_redirect(is_stderr=True) as stderr:
            try:
                assert self.ghc._get_default_branch() == expec_name
            except SystemExit as err:
                assert err.code == ERR_EXIT_CODE
                assert stderr.getvalue()

    @pytest.mark.parametrize(
        "data, expec_data",
        [
            pytest.param(
                {"total_count": 0, "workflow_runs": []},
                None,
                id="no runs",
            ),
            pytest.param(
                {"total_count": 3, "workflow_runs": [1, 2, 3]},
                [1, 2, 3],
                id="runs",
            ),
        ],
    )
    @mock.patch(MOCK_GITHUB % "_get_default_branch", side_effect=["main"])
    @mock.patch(MOCK_GITHUB % "_make_request")
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_get_runs(
        self,
        post_init,
        _make_request,
        _get_default_branch,
        data: dict,
        expec_data: list,
    ):
        _make_request.return_value = data
        with std_redirect(is_stderr=True) as stderr:
            try:
                assert self.ghc._get_runs() == expec_data
            except SystemExit as err:
                assert err.code == ERR_EXIT_CODE
                assert stderr.getvalue()

    @pytest.mark.parametrize(
        "runs, expec_runs",
        [
            pytest.param(
                list(),
                None,
                id="no-runs",
            ),
            pytest.param(
                [{"repository": {"fork": True}}],
                None,
                id="fork",
            ),
            pytest.param(
                [{"name": "CD", "repository": {"fork": False}}],
                None,
                id="wrong-name",
            ),
            pytest.param(
                [{"name": "CI", "repository": {"fork": False}}],
                [{"name": "CI", "repository": {"fork": False}}],
                id="valid",
            ),
        ],
    )
    @mock.patch(MOCK_GITHUB % "_get_runs")
    @mock.patch(MOCK % "Filter.__post_init__")
    def test_get_filtered_runs(
        self, post_init, _get_runs, runs: list, expec_runs: list
    ):
        _get_runs.return_value = runs
        with std_redirect(is_stderr=True) as stderr:
            self.ghc.filter.workflow_name = "ci"
            try:
                assert self.ghc.get_filtered_runs() == expec_runs
            except SystemExit as err:
                assert err.code == ERR_EXIT_CODE
                assert stderr.getvalue()


class TestFunctions:

    """Functions which are on the global-scope test cases."""

    @pytest.mark.parametrize(
        "runs, expected_code",
        [
            pytest.param(
                [{"status": "completed", "conclusion": "success"}],
                SCC_EXIT_CODE,
                id="succeeded",
            ),
            pytest.param(
                [{"status": "completed", "conclusion": "failed"}],
                ERR_EXIT_CODE,
                id="failed[1]",
            ),
            pytest.param(
                [{"status": "waiting", "conclusion": "success"}],
                ERR_EXIT_CODE,
                id="failed[2]",
            ),
        ],
    )
    def test_get_exit_code(self, runs: List[dict], expected_code: int):
        exit_code = get_exit_code(runs)
        assert exit_code == expected_code

    @pytest.mark.parametrize(
        "exit_code, expected_substring",
        [
            pytest.param(ERR_EXIT_CODE, "failed", id="failed"),
            pytest.param(SCC_EXIT_CODE, "succeeded", id="succeeded"),
        ],
    )
    def test_output_conclusion(self, exit_code: int, expected_substring: str):
        with std_redirect(bool(exit_code)) as std:
            report = " {REPORT} "
            output_conclusion(report, exit_code)
            output = std.getvalue()
            assert report in output
            assert expected_substring in output

    @pytest.mark.parametrize(
        "value, expected_bool",
        [
            # Falsy values.
            pytest.param("n", False, id="n"),
            pytest.param("no", False, id="no"),
            pytest.param("f", False, id="f"),
            pytest.param("false", False, id="false"),
            pytest.param("off", False, id="off"),
            pytest.param("0", False, id="0"),
            # Truly values (major cases).
            pytest.param("y", True, id="y"),
            pytest.param("yes", True, id="yes"),
            pytest.param("t", True, id="t"),
            pytest.param("true", True, id="true"),
            pytest.param("on", True, id="on"),
            pytest.param("1", True, id="1"),
        ],
    )
    def test_str2bool(self, value: str, expected_bool: bool):
        assert str2bool(value) == expected_bool
        assert str2bool(value.upper()) == expected_bool

    # This is the only semi intgeration tests that we have (requests.get mocked).
    @pytest.mark.parametrize(
        "conclusion, expec_exit_code",
        [
            pytest.param("success", SCC_EXIT_CODE, id="success"),
            pytest.param("failure", ERR_EXIT_CODE, id="failure"),
        ],
    )
    @mock.patch(
        MOCK % "os.getenv",
        side_effect=["hadialqattan", "relies-on", "ci", "main", "push", "true"],
    )
    @mock.patch(MOCK % "req.get")
    def test_main(self, get, getenv, conclusion: str, expec_exit_code: int):
        with std_redirect(is_stderr=bool(expec_exit_code)) as stdio:
            get.return_value.json.return_value = {
                "total_count": 1,
                "workflow_runs": [
                    {
                        "repository": {"fork": False},
                        "name": "CI",
                        "status": "completed",
                        "conclusion": conclusion,
                    }
                ],
            }
            type(get.return_value).status_code = mock.PropertyMock(return_value=200)

            exit_code = main()
            assert exit_code == expec_exit_code

            if expec_exit_code == SCC_EXIT_CODE:
                assert "succeeded" in stdio.getvalue()
            else:
                assert "failed" in stdio.getvalue()
