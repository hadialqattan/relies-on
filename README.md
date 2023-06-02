<h1 align="center">
    <img width=321 src="./logo.png"/><br>
</h1>

<h4 align="center">
  A Github action to identify any workflows that must complete successfully before another workflow will run.
  </br>
  </br>
  <i>"Relies-on is to workflows as <code><a href="https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idneeds">needs</a></code> is to jobs" - Relies-on Author 😉</i>
</h4>

##

</br>
<p align="center">
    <a href="https://github.com/hadialqattan/relies-on/actions?query=workflow%3ACI"><img src="https://img.shields.io/github/actions/workflow/status/hadialqattan/relies-on/ci.yml?label=CI&logo=github&style=flat-square" alt="CI"></a>
    <a href="https://codecov.io/gh/hadialqattan/relies-on"><img src="https://img.shields.io/codecov/c/gh/hadialqattan/relies-on/main?token=J5B4U3N3X4&style=flat-square" alt="Codecov"></a>
  <a href="https://github.com/hadialqattan/relies-on/blob/main/LICENSE"><img src="https://img.shields.io/github/license/hadialqattan/relies-on.svg?color=dark-green&style=flat-square" alt="License"></a>
</p>

<p align="center">
    <a href="https://github.com/hadialqattan/relies-on/issues"><img src="https://img.shields.io/github/issues/hadialqattan/relies-on?style=flat-square" alt="Issues"></a>
    <a href="https://github.com/hadialqattan/relies-on/pulls"><img src="https://img.shields.io/github/issues-pr/hadialqattan/relies-on?style=flat-square" alt="Pull Requests"></a>
    <a href="https://github.com/hadialqattan/relies-on/commits/main"><img src="https://img.shields.io/github/last-commit/hadialqattan/relies-on.svg?style=flat-square" alt="Last Commit"></a>
</p>

##

## Why does Relies-on exist? 🛸

The main purpose of Relies-on is to identify any workflows that must complete
successfully before another workflow will run.

_(The idea behind this action is similar to Github's
<code><a href="https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idneeds">needs</a></code>
but at a workflows scale)._

As an example of a situation where Relies-on comes in handy, let's imagine that you have
two different workflows one called `CI` and another called `CD` assuming the `CD`
workflow will do a critical thing that mustn't be performed only if the latest run of
the `CI` workflow succeeded. One approach to solve this problem is to check the status
of the latest `CI` run manually, but the problem with this approach is the ability to
run the `CD` workflow (doing the critical thing) whether the latest `CI` workflow run
was succeeded or not, which is not totally safe because there is no actual restriction,
therefore Relies-on comes into existence.

## How could aliens use this action? 👽

Here's a simple example to get started (assuming we have another workflow called `CI`):

```yml
# This is a CD system. It should publish a new release
# if and only if the lastest run of the CI workflow has succeeded.
name: CD

on:
  push:
    tags:
      - "v*.*.*"

jobs:
  check_ci_status:
    name: Check the CI Workflow's Status
    runs-on: ubuntu-latest
    steps:
      - uses: hadialqattan/relies-on@v1.0.0
        with:
          workflow: CI

  deployment:
    name: Deployment job
    needs: check_ci_status
    ...
```

This would terminate the `CD` workflow if the latest `CI` workflow run faild.

**Optional action inputs (arguments):**

```yml
owner:
  The username of the owner of the repository containing the workflow. [default=currect
  repository owner username]

repository:
  The name of the repository containing the workflow. [default=current repository name]

workflow: The name of the workflow that would be checked.

branch:
  The name of the branch where the workflow runs. [default=repository's default branch
  (most likely master or main)]

event: The type of the event that triggers the workflow. [default= ]

exclude_pull_requests: If true pull requests based runs are omitted. [default=true]
# Falsy values: "n", "no", "f", "false", "off", "0"
# Truthy values: "y", "yes", "t", "true", "on", "1"
```

## Changelog 🆕

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- Please use the below template. -->
<!-- - [description by @username](https://github.com/hadialqattan/relies-on/pull/{pull_number}) -->

### [Unreleased]

### [1.0.0] - 2022-04-26

#### Added

- [First published version](https://github.com/marketplace/actions/relies-on), Happy 🍰
  Day 2022!
- [Semantically versioned](https://semver.org/spec/v2.0.0.html)
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) formatted.

## Authors 👤

Authors:

- Hadi Alqattan ([@hadialqattan](https://github.com/hadialqattan))
  <alqattanhadizaki@gmail.com>

Contributors:

<!-- Please write your name alphabetically and use the below template. -->
<!-- - First Last ([@username](https://github.com/username)) <example@email.com> -->

## Contributing ✨

A big welcome for considering contributing to make the project better. In general, we
follow the ["fork-and-pull"](https://github.com/susam/gitpr) Git workflow:

1. Fork the repository to your own Github account.
2. Clone the project to your machine.
3. Create a branch locally.
4. Commit changes to the branch.
5. Follow any formatting and testing guidelines specific to this repo
   (`pre-commit install`).
6. Push changes to your fork.
7. Open a PR in our repository.

## Code of Conduct ❤️

Everyone participating in the Relies-on project, and in particular in the issue tracker,
and pull requests is expected to treat other people with respect.

## License 🚓

This project is licensed under an [MIT](./LICENSE) license.

##

Give a ⭐️ if this project helped you!
