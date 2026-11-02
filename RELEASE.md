# Release Process

<!-- gearu:release:start -->
## Gearu Release Process

Gearu prepares and verifies the repository, creates an immutable tag, and can
create the GitHub Release that starts this repository's publication workflow.
It does not publish directly to package registries.

Full documentation: <https://owebeeone.github.io/gearu/>

### Install

Install the released tool with:

```sh
uv tool install gearu
```

Upgrade an existing installation with:

```sh
uv tool upgrade gearu
```

To test the unreleased `main` branch, install it directly from its repository:

```sh
uv tool install git+https://github.com/owebeeone/gearu.git
```

Verify the installation with `gearu --version`.

### Preconditions

- Read `gearu.toml` and this repository's release workflow.
- Choose an explicit release version or an explicit major, minor, or patch bump.
  Gearu does not infer release intent from commits.
- Use a clean checkout on the branch configured by `project.branch`.
- Synchronize configured release and source branches with their remote.
- Release required cross-repository dependencies first.
- Install and authenticate `gh` before requesting GitHub Release creation.

### Plan

Always inspect the read-only plan first:

```sh
gearu plan VERSION
```

Or ask Gearu to select the next version:

```sh
gearu plan --bump patch
gearu plan --bump minor
gearu plan --bump major
```

Gearu compares configured package versions with valid local and remote release
tags, then bumps the highest version. It reads remote tags directly and does not
fetch or create local tags while planning.

For a release candidate, use a numbered version such as `1.2.3-rc.1`.

Override a configured dependency tag only when the release intentionally uses a
different version:

```sh
gearu plan VERSION --dependency-tag DEPENDENCY=TAG
```

### Prepare the Local Release

After reviewing the plan:

```sh
gearu release VERSION
```

The release command can select the version itself:

```sh
gearu release --bump minor
```

This recalculates the next version at release time. To lock the version reviewed
in a prior bump plan, pass that plan's reported `VERSION` explicitly.

Gearu builds and tests in a temporary worktree. Only a successful candidate is
applied to the local release branch and tagged. This step does not change a
remote repository.

### Push and Create the GitHub Release

Push the exact release commit and tag atomically:

```sh
gearu release VERSION --push
```

Create the GitHub Release after that push:

```sh
gearu release VERSION --push --github-release
```

The final command starts workflows listening for `release.published`, including
package publication and documentation deployment where configured.

### Recovery

- If candidate checks fail, fix the problem and rerun; the normal checkout is
  left unchanged.
- If local preparation succeeds, rerun the same version with `--push`.
- If the push succeeds but GitHub Release creation fails, rerun with
  `--push --github-release`.
- If released contents must change, use a new patch or release-candidate version.
  Never move or replace the existing tag.
- If only a publication workflow fails, repair and rerun that workflow for the
  same GitHub Release.
<!-- gearu:release:end -->

## taut's checks

The 0.11 train also releases the dependency-free `taut-foundation` Rust crate.
Gearu versions `rust/taut-foundation/Cargo.toml` with the Python package and
verifies its canonical-source inventory and standalone Cargo package. Its
runtime files are generated from the canonical sources, never independently
maintained. The crate includes its own license, README and provenance.

For the initial crate publication, prepare and push with Gearu **without**
`--github-release`. Run `foundation.yml` in `owebeeone/taut-shape-rs` with the
exact release commit, version, and `publish=true`; that existing repository's
`crates-io` environment holds the bootstrap credential. The workflow verifies
the immutable Taut tag before publishing. First run it with `publish=false`
against the committed readiness source to check packaging and credential
presence. Presence cannot prove the token's new-crate scope; a failed bootstrap
publication blocks the Python release and the rest of the train.

Only after foundation is visible on crates.io, rerun Gearu with
`--push --github-release` to publish Taut to PyPI. Then release the three shape
libraries against registry dependencies. Never copy the bootstrap credential
to a checkout or publish from a local source tree.

`gearu.toml` runs `scripts/release_checks.py`, which took over from `scripts/release.py` in
v0.10.0. That script tagged as well as checking. gearu runs every step on its candidate, and
rereads only the metadata on the commit it tags: a tag-derived version needs no release commit.

After the metadata step, three chains run side by side: the tests; the parity gate; and the build
followed by the wheel's smoke test. Each step logs to its own file, and a failed step prints the end
of its log.
- The tests run one worker per CPU through `pytest-xdist`.
- They leave out the tests marked `gate`, which rerun the gate's runners: the parity step runs the
  whole gate itself.
- The gate builds its targets side by side, one per CPU by default (`tautc parity --jobs N`).

The tests step fails if any test skips, and the parity step runs `tautc parity --require-all`.
The qualified strict test environment is native Windows plus its Ubuntu WSL
mount of the same candidate. Set `TAUT_RELEASE_POSIX_PYTHON` to an absolute WSL
Python path with pytest; `TAUT_RELEASE_WSL_DISTRO` defaults to `Ubuntu`.
The `posix` marker assigns the three shell/PATH probes and the real symlink
probe to WSL. All remaining non-`gate` cases run natively, including MSVC,
Windows junctions and namespace semantics. Neither execution may skip.
The gate first collects every case, records IDs and candidate raw-file hashes,
then verifies the exact platform union and all setup/call/teardown results.
`TAUT_RELEASE_EVIDENCE_DIR` retains JSON/XML ledgers and logs outside the candidate.
The eight duplicate `gate` wrappers are recorded separately; the mandatory
parity command must execute all sixteen variants and all 88 rows per variant.

`release-inputs.json` pins the four sibling test inputs. Gearu materializes
committed clones with LF checkout and frozen TypeScript dependencies; publication
CI fetches the same immutable input revisions. The checked package itself
continues to install without any sibling repository.
Every language and forward-compat build must run, so every toolchain must be installed: `rustc`,
a C++ compiler, `swiftc`, `go`, a `node` that strips TypeScript types, a JDK and `kotlinc`.
- The JDK is found through `JAVA_HOME`, then Android Studio's bundled one, then `PATH`.
- `kotlinc` is found through `KOTLINC`, then Android Studio's Kotlin plugin, then `PATH`. It runs
  under the JDK found for it, so Android Studio's bundle needs no environment variables.

A missing toolchain fails the release; it does not skip its tests or its target.

To show that a tree is ready to tag without tagging it, run every step, preferably from a clean
clone:

```sh
uv run --no-project --python 3.13 --with pytest --with pytest-xdist --with build \
    --with twine python scripts/release_checks.py 0.10.0
```

The script takes the version in Python's form, which is what gearu passes as `{python_version}`:
`0.10.0`, or `0.10.0rc1` for the release candidate `v0.10.0-rc.1`.
