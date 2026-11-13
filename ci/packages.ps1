# Shared by the scripts in this folder, which dot-source it. Works out which
# products a pull request touches, and checks each package's tox.ini.
#
# Which packages a publish releases, and at which version, is worked out by
# common-ci's steps/release-plan.ps1 from ci/packages.json. common-ci runs
# these scripts from its own root, with this repository checked out inside
# it. A checkout of common-ci beside this repository is found too, or one
# elsewhere can be named with COMMON_CI.
$releasePlan = @(
    $env:COMMON_CI,
    (Join-Path $PSScriptRoot '..' '..'),
    (Join-Path $PSScriptRoot '..' '..' 'common-ci')) |
    Where-Object { $_ } |
    ForEach-Object { Join-Path $_ 'steps' 'release-plan.ps1' } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1
if ($null -eq $releasePlan) {
    throw "common-ci's steps/release-plan.ps1 was not found. Set COMMON_CI " +
        "to a checkout of common-ci."
}
. $releasePlan
Remove-Variable releasePlan

# Each tox.ini that does not install every package its package depends on,
# directly or through another, from this checkout, as a line naming what is
# missing. Taken from a package index instead, a dependency is tested at its
# last release rather than with the code it is released with.
function Get-ToxGaps([string]$RepoPath, $Packages = $null) {
    if ($null -eq $Packages) {
        $Packages = Get-Packages $RepoPath
    }
    $byName = @{}
    foreach ($package in $Packages) {
        $byName[$package.Name] = $package
    }
    $gaps = @()
    foreach ($package in $Packages) {
        $tox = Join-Path $RepoPath $package.Path 'tox.ini'
        if ((Test-Path $tox) -eq $false) {
            continue
        }
        $text = Get-Content -Raw $tox
        $needed = [Collections.Generic.HashSet[string]]::new()
        $queue = [Collections.Generic.Queue[string]]::new()
        foreach ($name in $package.DependsOn) {
            $queue.Enqueue($name)
        }
        while ($queue.Count -gt 0) {
            $name = $queue.Dequeue()
            if ($needed.Add($name) -eq $true) {
                foreach ($next in $byName[$name].DependsOn) {
                    $queue.Enqueue($next)
                }
            }
        }
        foreach ($name in $needed) {
            $relative = [IO.Path]::GetRelativePath(
                (Join-Path $RepoPath $package.Path),
                (Join-Path $RepoPath $byName[$name].Path)).Replace('\', '/')
            $pattern = '(?m)^\s*-e\s*' + [regex]::Escape($relative) + '/?\s*$'
            if ($text -notmatch $pattern) {
                $gaps += "$($package.Path)/tox.ini does not install $name from $relative"
            }
        }
    }
    return $gaps
}

# The products a set of changed files touches. A file in a package's folders
# touches that package's product and the product of every package depending on
# it, because a change to pipeline can break device-detection.
# A file in a product's folder but outside its packages, such as its ci/ or
# docs/, touches that product. A file outside every product, such as the root
# ci/ or a workflow, touches every product.
function Resolve-AffectedProducts($Packages, [string[]]$Changed) {
    $allProducts = @($Packages.Product | Select-Object -Unique)
    if (@($Changed).Count -eq 0) {
        return $allProducts
    }
    $changedPackages = [Collections.Generic.HashSet[string]]::new()
    $products = [Collections.Generic.HashSet[string]]::new()
    foreach ($path in $Changed) {
        $owner = $null
        foreach ($package in $Packages) {
            foreach ($folder in (Get-PackagePaths $package)) {
                if ((Test-PathUnder $path $folder) -eq $true) {
                    $owner = $package
                }
            }
        }
        if ($null -ne $owner) {
            $null = $changedPackages.Add($owner.Name)
            continue
        }
        $product = $allProducts | Where-Object {
            (Test-PathUnder $path $_) -eq $true
        }
        if ($null -eq $product) {
            return $allProducts
        }
        $null = $products.Add($product)
    }
    foreach ($name in (Get-DependentClosure $Packages @($changedPackages))) {
        $package = $Packages | Where-Object { $_.Name -eq $name }
        $null = $products.Add($package.Product)
    }
    # Keep the order of packages.json, so the logs read the same every run.
    return @($allProducts | Where-Object { $products.Contains($_) -eq $true })
}

# The products a pull request changes, or every product when the checkout is
# not a pull request (a publish, or a run on main), as 51degrees-cxx does.
function Get-AffectedProducts([string]$RepoPath) {
    # merge-base fails where there is no origin/main, which is an answer here.
    # Set for this function only, so a caller that stops on a failing native
    # command, as publish-package.ps1 does, is not stopped by it.
    $PSNativeCommandUseErrorActionPreference = $false
    $packages = Get-Packages $RepoPath
    $head = git -C $RepoPath rev-parse HEAD
    $base = git -C $RepoPath merge-base origin/main HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or $null -eq $base -or $base -eq $head) {
        $global:LASTEXITCODE = 0
        return @($packages.Product | Select-Object -Unique)
    }
    $changed = @(git -C $RepoPath diff --name-only $base $head)
    return Resolve-AffectedProducts $packages $changed
}

# What a build of HEAD makes: the release plan, or, when nothing changed since
# the last release, every published package at its released version. Nothing
# is published then, because package-update-required.ps1 finds the release
# plan empty, but the publish's tests still have the packages to install.
function Get-BuildPlan([string]$RepoPath, $Packages = $null) {
    if ($null -eq $Packages) {
        $Packages = Get-Packages $RepoPath
    }
    $plan = @(Get-ReleasePlan $RepoPath $Packages)
    if ($plan.Count -gt 0) {
        return $plan
    }
    $published = @($Packages | Where-Object { $_.Publish -eq $true })
    foreach ($name in (Sort-ByDependency $published @($published.Name))) {
        $package = $published | Where-Object { $_.Name -eq $name }
        $last = @(Get-ReleasedVersions $RepoPath $name)[-1]
        [pscustomobject]@{
            Name = $name
            Path = $package.Path
            Version = "$last"
            Previous = $last
            Reason = 'already released, built for the tests'
        }
    }
}
