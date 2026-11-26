# Shared by the step scripts in this folder, which dot-source it.
#
# Each product folder keeps the ci/ scripts it had as its own repository, and
# they know that product's packages, assets and test quirks. common-ci calls
# the scripts in this folder, at the root; each runs the same step of every
# product the change affects, with that product's own script and the product
# folder as its repository. A product that never had the step is skipped.

. (Join-Path $PSScriptRoot 'packages.ps1')

# Every warning in the native build is an error in the builds 51Degrees runs.
# setup.py reads the variable in warnings_are_errors(). common-ci runs these
# steps from workflows this repository calls, which take no env of its own,
# so the steps set it here.
$env:_51DEGREES_WARNINGS_AS_ERRORS = 'true'

# Runs $Step for each affected product, or for each of $Products when given.
# Every product is run even when an earlier one fails, so one run reports
# every broken product, and the step fails at the end if any did. A pull
# request's changes are measured from the Branch in $Options, the branch it
# merges into.
function Invoke-ProductStep([string]$Step, [string]$RepoName,
        [Collections.IDictionary]$Options, [string[]]$Products) {
    $failed = [Collections.Generic.List[string]]::new()
    if (-not $Products) {
        $branch = $Options.Branch ? $Options.Branch : 'main'
        $Products = Get-AffectedProducts $RepoName $branch
    }
    foreach ($product in $Products) {
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
            try {
                Move-ProductTestResults $RepoName $product
            } catch {
                Write-Output "::error title=$Step failed::$product`: $_"
                if ($failed.Contains($product) -eq $false) {
                    $failed.Add($product)
                }
            }
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
# common-ci compares one performance summary for each configuration, so a
# summary another product already wrote gets this product's figures added.
function Move-ProductTestResults([string]$RepoName, [string]$Product) {
    $results = Join-Path $RepoName $Product 'test-results'
    if ((Test-Path $results) -eq $false) {
        return
    }
    foreach ($kind in (Get-ChildItem -Directory $results)) {
        $target = New-Item -ItemType Directory -Force `
            (Join-Path $RepoName 'test-results' $kind.Name)
        foreach ($file in (Get-ChildItem $kind.FullName)) {
            $existing = Join-Path $target $file.Name
            if ($kind.Name -eq 'performance-summary' -and
                    $file.Extension -eq '.json' -and
                    (Test-Path $existing -PathType Leaf) -eq $true) {
                Add-PerformanceFigures $file.FullName $existing
            } else {
                Move-Item $file.FullName -Destination $target -Force
            }
        }
    }
    Remove-Item -Recurse -Force $results
}

# Adds the HigherIsBetter and LowerIsBetter figures of the summary at $Source
# to the one at $Destination. A figure already in $Destination fails, because
# one of the two would be lost.
function Add-PerformanceFigures([string]$Source, [string]$Destination) {
    $from = Get-Content -Raw $Source | ConvertFrom-Json -AsHashtable
    $into = Get-Content -Raw $Destination | ConvertFrom-Json -AsHashtable
    foreach ($section in 'HigherIsBetter', 'LowerIsBetter') {
        if ($null -eq $from[$section]) {
            continue
        }
        if ($null -eq $into[$section]) {
            $into[$section] = [ordered]@{}
        }
        foreach ($metric in $from[$section].Keys) {
            if ($into[$section].Contains($metric) -eq $true) {
                throw "$section.$metric is in both '$Source' and '$Destination'"
            }
            $into[$section][$metric] = $from[$section][$metric]
        }
    }
    $into | ConvertTo-Json -Depth 10 | Set-Content $Destination
}
