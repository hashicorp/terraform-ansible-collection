# Release Guide

This guide is for maintainers preparing and publishing a new
`hashicorp.terraform` collection release. It is intentionally kept outside the
Ansible plugin documentation so it does not affect generated module docs.

Do not include tokens, organization names, private support details, unpublished
customer information, or other sensitive data in release pull requests, changelog
entries, tags, GitHub Releases, workflow logs, or issue comments. This is a
public repository.

## Preconditions

- All feature and fix pull requests for the release have been merged to `main`.
- Each user-visible change has an appropriate changelog fragment under
  `changelogs/fragments/`.
- CI is green on `main`, including changelog, build/import, linting, sanity,
  unit, integration, and docs checks where applicable.
- Any live verification was done with credentials supplied through local
  environment variables or GitHub secrets, never committed files.

## Release Flow

1. Merge all feature and fix pull requests, including their changelog fragments,
   to `main`.
2. Open a release preparation pull request from a fresh branch off `main`.
3. Bump `version` in `galaxy.yml` to the release version.
4. Generate the release changelog from the fragments:

   ```bash
   antsibull-changelog release --version 2.2.0 --date 2026-09-02
   ```

   Replace `2.2.0` and `2026-09-02` with the actual release version and release
   date. This updates `CHANGELOG.rst` and `changelogs/changelog.yaml`, and removes
   merged fragments because `changelogs/config.yaml` sets `keep_fragments: false`.
5. Review the generated changelog for accuracy, public wording, and formatting.
   Make sure new modules, breaking changes, deprecations, security fixes, known
   issues, and documentation changes are in the correct sections.
6. Run the relevant local validation before merging the release preparation PR:

   ```bash
   black --check plugins tests
   isort --check plugins tests
   flake8 plugins tests
   antsibull-changelog lint
   ansible-galaxy collection build --force
   ```

   Also run focused unit, sanity, docs, or integration checks for the changed
   areas when the release includes code or documentation changes. Do not commit
   any generated collection tarball from `ansible-galaxy collection build`.
7. Merge the release preparation PR to `main` after review and green CI.
8. Confirm `main` contains the intended `galaxy.yml` version and generated
   changelog entries. `changelogs/fragments/` should not contain released
   fragments after the release command has run.
9. Create and push a signed release tag from the release commit on `main`.
   Use the repository's current tag convention and make sure the GitHub Release
   points to the same tag. Recent releases use the bare version as the tag name,
   for example:

   ```bash
   git tag -s 2.2.0 -m "Release 2.2.0"
   git push origin 2.2.0
   ```

10. Create and publish a GitHub Release for the tag. Use the public changelog
    content as the release notes, and do not paste secrets, private URLs, or
    internal-only verification details.
11. Monitor the `Release hashicorp.terraform` workflow in GitHub Actions. The
    workflow publishes to Automation Hub when a GitHub Release is published; it
    can also be started manually with the `ah_publish` input.
12. Verify the published collection version is available from the expected
    distribution channel and that installation works in a clean environment.
13. If anything fails after publishing, document the failure publicly only at the
    level needed for users, fix forward with a new patch release, and avoid
    deleting or rewriting public tags unless maintainers explicitly agree.

## Post-Release Checks

- Confirm the GitHub Release, tag, `CHANGELOG.rst`, and `galaxy.yml` all show the
  same version.
- Confirm the Automation Hub release workflow completed successfully.
- Confirm any follow-up issues or pull requests are opened for deferred work.
- Confirm the next development change will add a fresh changelog fragment.
