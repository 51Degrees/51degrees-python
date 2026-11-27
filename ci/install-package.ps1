$ErrorActionPreference = "Stop"

# The packages with native code are built from source as they install, and
# every warning in that build is an error, as in every build 51Degrees runs.
# See ci/dispatch.ps1.
$env:_51DEGREES_WARNINGS_AS_ERRORS = 'true'

# Installs every package the build step made, whichever product it is from,
# so the integration tests run against the packages about to be published.
./python/install-package.ps1

exit $LASTEXITCODE
