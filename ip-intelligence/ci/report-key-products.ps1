param (
    [Parameter(Mandatory=$true)]
    [AllowEmptyString()]
    [string]$ResourceKey
)

# Says what the test resource key is entitled to, so a run that finds no IP
# data is read as an entitlement gap rather than as broken code. A key that
# does not carry a product answers "paid feature" for its properties, and a
# key that carries no component at all leaves the request with no element
# data for it, and both look like a broken service when they are the
# entitlement working correctly.
#
# Only product names, tiers and property counts are printed. The key itself
# is never written anywhere, because a build log is readable by anyone who
# can read the repository.

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

if ([string]::IsNullOrWhiteSpace($ResourceKey)) {
    Write-Output "No resource key was given, so there is nothing to report."
    exit 0
}

$uri = "https://cloud.51degrees.com/api/v4/accessibleproperties?resource=$ResourceKey"
try {
    $answer = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
} catch {
    # A failure here says nothing about the tests that follow, so it reports
    # and returns rather than stopping the build.
    Write-Output "Could not ask the cloud what the test resource key carries. $($_.Exception.Message)"
    exit 0
}

if ($null -eq $answer.Products) {
    Write-Output "The cloud answered with no products at all for the test resource key."
    exit 0
}

Write-Output "What the test resource key carries:"
foreach ($name in ($answer.Products | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name | Sort-Object)) {
    $product = $answer.Products.$name
    $count = 0
    if ($null -ne $product.Properties) { $count = @($product.Properties).Count }
    $word = if ($count -eq 1) { "property" } else { "properties" }
    Write-Output ("  {0,-24} {1,-16} {2} {3}" -f $name, $product.DataTier, $count, $word)
}

if ($null -eq $answer.Products.ip) {
    Write-Output "::warning title=No IP product::The test resource key carries no 'ip' product, so every IP intelligence cloud test in this run is checking an unentitled key. A request for IP properties comes back with no element data for 'ip' at all, which reads like a broken service."
}

exit 0
