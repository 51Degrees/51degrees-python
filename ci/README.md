# API Specific CI/CD Approach
This API complies with the `common-ci` approach.

The secrets each workflow passes are named in [.github/workflows](../.github/workflows).

The following secrets are required:
* `ACCESS_TOKEN` - GitHub [access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#about-personal-access-tokens) for cloning repos, creating PRs, etc.
    * Example: `github_pat_l0ng_r4nd0m_s7r1ng`
* `_51DEGREES_RESOURCE_KEY_BESPOKE` - [resource key](https://51degrees.com/documentation/_info__resource_keys.html) for the cloud tests. It must include the IP Intelligence (`ip`) product, or every cloud test fails as if the service were broken.
    * Example: `R4nd0m-S7r1ng`
* `PYPI_TOKEN` - [PyPI token](https://pypi.org/help/#apitoken) for publishing packages
    * Example: `pypi-sUp3r-l0nG_r4nd0m-s7r1Ng`

The following secrets are optional:
* `IPI_DATA_FILE_URL` - URL for downloading the Enterprise IP Intelligence data file. When it is set, the tests use that file instead of the Lite file, which is downloaded without a key.
* `IP_INTELLIGENCE_KEY` - [licence key](https://51degrees.com/pricing) passed with the Enterprise data file download.
    * Example: `V3RYL0NGR4ND0M57R1NG`
* `TEST_PYPI_TOKEN` - [TestPyPI token](https://test.pypi.org/help/#apitoken) used by the publish workflow.
