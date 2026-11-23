# API Specific CI/CD Approach
This API complies with the `common-ci` approach.

The following secrets are required:
* `_51DEGREES_ACCESS_TOKEN` - GitHub [access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#about-personal-access-tokens) for cloning repos, creating PRs, etc.
    * Example: `github_pat_l0ng_r4nd0m_s7r1ng`
* `_51DEGREES_RESOURCE_KEY_BESPOKE` - [resource key](https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=ci-readme.md&utm_term=api-specific-ci-cd-approach) for the integration tests. It is an organization secret. common-ci exports it.
    * Example: `R4nd0m-S7r1ng`
* `_51DEGREES_RESOURCE_KEY_BASIC` - resource key of the Basic product, an organization secret. The Basic Human Confidence test, which calls the staging cloud, and the 51Did tier test read it, and skip naming it when it is not set.
* `_51DEGREES_LICENSE_KEY_BESPOKE` - cloud license key for the license-key tests, an organization secret, which skip naming it when it is not set.
* `_51DEGREES_RESOURCE_KEY_51DID` and `_51DEGREES_LICENSE_KEY_51DID` - the 51Did live tests' resource key and the license key of the same account. The resource key and the license key are both organization secrets. With a resource key of another account, such as `_51DEGREES_RESOURCE_KEY_BESPOKE`, the licensed redeem comes back unreadable.
* `_51DEGREES_PYPI_TOKEN` - [PyPI token](https://pypi.org/help/#apitoken) for publishing packages
    * Example: `pypi-sUp3r-l0nG_r4nd0m-s7r1Ng`

The Human Confidence tests marked `staging` check what the production cloud does not serve yet, and the Cloud Human Confidence workflow (`.github/workflows/cloud-human-confidence.yml`) runs them against the staging cloud. Only CI uses these two names, which have no `_51DEGREES_` prefix. common-ci does not pass them on, so in the shared integration tests the staging tests skip.
* `CLOUD_STAGING_ENDPOINT` - the staging cloud's API base, ending `/api/v4/`, an organization variable. The staging tests have no default address and skip, naming it, when it is not set.
* `RESOURCE_KEY_BESPOKE_STAGING` - a Bespoke resource key the staging cloud knows, an organization secret.
