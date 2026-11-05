# Shared by the scripts in this folder, which dot-source it. Reads the
# packages this repository publishes from packages.json, works out which
# products a pull request touches, and which packages a publish releases at
# which version.
#
# Each package has its own version, tagged '<package>/<version>'. A package is
# released when a file under its folder changed since its last tag, or when a
# package it depends on is being released, because its requirement on that
# package moves. This is the scheme in 51Degrees/rust#205, which the per
# language repositories follow.

# Reads packages.json. Kept as a function so the tests can give their own list.
function Get-Packages([string]$RepoPath) {
    return Get-Content -Raw (Join-Path $RepoPath 'ci/packages.json') |
        ConvertFrom-Json
}

# The folders whose changes count as a change to the package: its own folder,
# and any folder it takes files from at build time, such as a submodule it
# vendors.
function Get-PackagePaths($Package) {
    $paths = @($Package.Path)
    if ($Package.ExtraPaths) {
        $paths += $Package.ExtraPaths
    }
    return $paths
}

function Test-PathUnder([string]$Path, [string]$Folder) {
    return $Path -eq $Folder -or $Path.StartsWith("$Folder/")
}

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

# The names of the given packages and of every package that depends on one of
# them, directly or through another.
function Get-DependentClosure($Packages, [string[]]$Names) {
    $closure = [Collections.Generic.HashSet[string]]::new()
    foreach ($name in @($Names | Where-Object { $_ })) {
        $null = $closure.Add($name)
    }
    $grew = $true
    while ($grew -eq $true) {
        $grew = $false
        foreach ($package in $Packages) {
            if ($closure.Contains($package.Name) -eq $true) {
                continue
            }
            foreach ($dependency in $package.DependsOn) {
                if ($closure.Contains($dependency) -eq $true) {
                    $null = $closure.Add($package.Name)
                    $grew = $true
                    break
                }
            }
        }
    }
    return @($closure)
}

# The named packages, each after every package it depends on, so a release
# never publishes a package before the version it requires exists.
function Sort-ByDependency($Packages, [string[]]$Names) {
    $remaining = [Collections.Generic.List[string]]::new([string[]]@($Names))
    $sorted = [Collections.Generic.List[string]]::new()
    while ($remaining.Count -gt 0) {
        $ready = @($remaining | Where-Object {
            $name = $_
            $package = $Packages | Where-Object { $_.Name -eq $name }
            @($package.DependsOn | Where-Object {
                $remaining.Contains($_) -eq $true
            }).Count -eq 0
        } | Sort-Object)
        if ($ready.Count -eq 0) {
            throw "packages.json has a dependency cycle among: $($remaining -join ', ')"
        }
        foreach ($name in $ready) {
            $sorted.Add($name)
            $null = $remaining.Remove($name)
        }
    }
    return @($sorted)
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

# The parts of a version such as 4.5.38, or $null for anything else.
function ConvertTo-VersionParts([string]$Text) {
    $match = [regex]::Match($Text, '^(\d+)\.(\d+)\.(\d+)$')
    if ($match.Success -eq $false) {
        return $null
    }
    return [version]::new([int]$match.Groups[1].Value,
        [int]$match.Groups[2].Value, [int]$match.Groups[3].Value)
}

# The package's released versions, read from its '<package>/<version>' tags,
# highest last. The '/' after the name keeps fiftyone_ipintelligence from
# reading the tags of fiftyone_ipintelligence_cloud.
function Get-ReleasedVersions([string]$RepoPath, [string]$Name,
        [switch]$AtHead) {
    # Tags are found by prefix, not with a 'name/*' pattern: PowerShell on
    # Linux and macOS expands a '*' in an argument to a native command into
    # matching files, so from a folder holding a 'location' folder git would
    # be handed file names and find no tags.
    $arguments = @('-C', $RepoPath, 'for-each-ref',
        '--format=%(refname:strip=2)', "refs/tags/$Name/")
    if ($AtHead -eq $true) {
        $arguments += @('--points-at', 'HEAD')
    }
    $versions = foreach ($tag in (& git @arguments)) {
        ConvertTo-VersionParts $tag.Substring($Name.Length + 1)
    }
    return @($versions | Where-Object { $null -ne $_ } | Sort-Object)
}

# What a publish of HEAD releases: one entry per package, in the order to
# publish them, each with the version it is released at and why.
#
# A package already tagged at HEAD was released from this commit, so it is
# left out, which makes a second publish of the same commit release nothing.
# A package with no tag has never been released and starts at its FirstVersion
# from packages.json. Packages that are not published, the examples, are never
# in the plan; a change to them is tested but releases nothing.
function Get-ReleasePlan([string]$RepoPath, $Packages = $null) {
    # 'git diff --quiet' exits 1 to say a package changed. That is an answer,
    # not a failure, but a caller that stops on a failing native command, as
    # publish-package.ps1 does, stopped there and failed the publish. Set for
    # this function only.
    $PSNativeCommandUseErrorActionPreference = $false
    if ($null -eq $Packages) {
        $Packages = Get-Packages $RepoPath
    }
    $published = @($Packages | Where-Object { $_.Publish -eq $true })

    $previous = @{}
    $reasons = @{}
    foreach ($package in $published) {
        $atHead = Get-ReleasedVersions $RepoPath $package.Name -AtHead
        if ($atHead.Count -gt 0) {
            continue
        }
        $released = Get-ReleasedVersions $RepoPath $package.Name
        if ($released.Count -eq 0) {
            if ([string]::IsNullOrEmpty($package.FirstVersion) -eq $true) {
                throw "$($package.Name) has never been released and " +
                    "packages.json gives it no FirstVersion."
            }
            $previous[$package.Name] = $null
            $reasons[$package.Name] = 'first release'
            continue
        }
        $last = $released[-1]
        $previous[$package.Name] = $last
        $tag = "$($package.Name)/$last"
        & git -C $RepoPath diff --quiet $tag HEAD -- (Get-PackagePaths $package)
        if ($LASTEXITCODE -eq 1) {
            $reasons[$package.Name] = "changed since $last"
        }
        $global:LASTEXITCODE = 0
    }

    # A dependent is released with its dependency, as long as it was not
    # already released from this commit.
    $candidates = @($published.Name | Where-Object {
        $previous.ContainsKey($_) -eq $true
    })
    $changed = @($reasons.Keys)
    $toRelease = @(Get-DependentClosure $published $changed | Where-Object {
        $candidates -contains $_
    })

    foreach ($name in (Sort-ByDependency $published $toRelease)) {
        $package = $published | Where-Object { $_.Name -eq $name }
        $last = $previous[$name]
        if ($null -eq $last) {
            $version = $package.FirstVersion
        } else {
            $version = "$($last.Major).$($last.Minor).$($last.Build + 1)"
        }
        $reason = $reasons[$name]
        if ($null -eq $reason) {
            $reason = 'a package it depends on is released'
        }
        [pscustomobject]@{
            Name = $name
            Path = $package.Path
            Version = $version
            Previous = $last
            Reason = $reason
        }
    }
}
