# API Specific CI/CD Approach
This API complies with the `common-ci` approach.

The following secrets and organization variables are required:
* `_51DEGREES_ACCESS_TOKEN` - GitHub [access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#about-personal-access-tokens) for cloning repos, creating PRs, etc.
    * Example: `github_pat_l0ng_r4nd0m_s7r1ng`
* `_51DEGREES_RESOURCE_KEY_BESPOKE` - [resource key](https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=ci-readme.md&utm_term=api-specific-ci-cd-approach) for the integration tests. It is an organization variable. common-ci exports it.
    * Example: `R4nd0m-S7r1ng`
* `_51DEGREES_RESOURCE_KEY_BASIC` - resource key of the Basic product, an organization variable. The Basic Human Confidence test and the 51Did tier test read it, and skip naming it when it is not set.
* `_51DEGREES_LICENSE_KEY_BESPOKE` - cloud license key for the license-key tests, an organization secret, which skip naming it when it is not set.
* `_51DEGREES_RESOURCE_KEY_51DID` and `_51DEGREES_LICENSE_KEY_51DID` - the 51Did live tests' resource key and the license key of the same account. The resource key is an organization variable and the license key an organization secret. With a resource key of another account, such as `_51DEGREES_RESOURCE_KEY_BESPOKE`, the licensed redeem comes back unreadable.
* `_51DEGREES_PYPI_TOKEN` - [PyPI token](https://pypi.org/help/#apitoken) for publishing packages
    * Example: `pypi-sUp3r-l0nG_r4nd0m-s7r1Ng`
