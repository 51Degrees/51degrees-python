# Shared by the step scripts in this folder, which dot-source it.
#
# Each product folder keeps the ci/ scripts it had as its own repository, and
# they know that product's packages, assets and test quirks. common-ci calls
# the scripts in this folder, at the root; each runs the same step of every
# product the change affects, with that product's own script and the product
# folder as its repository. A product that never had the step is skipped.

. (Join-Path $PSScriptRoot 'packages.ps1')

# Runs $Step for each affected product. Every product is run even when an
# earlier one fails, so one run reports every broken product, and the step
# fails at the end if any did. A pull request's changes are measured from
# the Branch in $Options, the branch it merges into.
function Invoke-ProductStep([string]$Step, [string]$RepoName,
        [Collections.IDictionary]$Options) {
    $failed = [Collections.Generic.List[string]]::new()
    $branch = $Options.Branch ? $Options.Branch : 'main'
    foreach ($product in (Get-AffectedProducts $RepoName $branch)) {
        $script = Join-Path $RepoName $product 'ci' "$Step.ps1"
        if ((Test-Path $script) -eq $false) {
            Write-Output "$product has no $Step step"
            continue
        }
        $productOptions = @{}
        foreach ($option in $Options.GetEnumerator()) {
            $productOptions[$option.Key] = $option.Value
        }
        $productOptions['RepoName'] = Join-Path $RepoName $product

        Write-Output "::group::$Step for $product"
        try {
            ./steps/run-script.ps1 $script $productOptions
        } catch {
            Write-Output "::error title=$Step failed::$product`: $_"
            $failed.Add($product)
        } finally {
            Move-ProductTestResults $RepoName $product
            Write-Output "::endgroup::"
        }
    }
    if ($failed.Count -gt 0) {
        throw "$Step failed for: $($failed -join ', ')"
    }
}

# common-ci collects test results from <repository>/test-results, and a
# product's own scripts write them under its folder, where they would not be
# found. Move them up, keeping the unit/integration/performance folders.
function Move-ProductTestResults([string]$RepoName, [string]$Product) {
    $results = Join-Path $RepoName $Product 'test-results'
    if ((Test-Path $results) -eq $false) {
        return
    }
    foreach ($kind in (Get-ChildItem -Directory $results)) {
        $target = New-Item -ItemType Directory -Force `
            (Join-Path $RepoName 'test-results' $kind.Name)
        Get-ChildItem $kind.FullName | Move-Item -Destination $target -Force
    }
    Remove-Item -Recurse -Force $results
}
