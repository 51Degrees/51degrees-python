# API Specific CI/CD Approach
This API complies with the `common-ci` approach.

The secrets each workflow passes are named in [.github/workflows](../.github/workflows).

The following secrets are required:
* `ACCESS_TOKEN` - GitHub [access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#about-personal-access-tokens) for cloning repos, creating PRs, etc.
    * Example: `github_pat_l0ng_r4nd0m_s7r1ng`
* `_51DEGREES_RESOURCE_KEY_BESPOKE` - [resource key](https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=ci-readme.md&utm_term=api-specific-ci-cd-approach) for the cloud tests. It must include the IP Intelligence (`ip`) product, or every cloud test fails as if the service were broken.
    * Example: `R4nd0m-S7r1ng`
* `PYPI_TOKEN` - [PyPI token](https://pypi.org/help/#apitoken) for publishing packages
    * Example: `pypi-sUp3r-l0nG_r4nd0m-s7r1Ng`

The following secret is also required:
* `_51DEGREES_LICENSE_KEY` - [license key](https://51degrees.com/pricing?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=ci-readme.md&utm_term=api-specific-ci-cd-approach) for downloading the data files from the Distributor (the Enterprise IP Intelligence data file). common-ci reads it.
    * Example: `V3RYL0NGR4ND0M57R1NG`
