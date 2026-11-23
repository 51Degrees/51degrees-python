$ErrorActionPreference = "Stop"

# Installs every package the build step made, whichever product it is from,
# so the integration tests run against the packages about to be published.
./python/install-package.ps1

exit $LASTEXITCODE
