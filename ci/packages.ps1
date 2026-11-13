# Shared by the scripts in this folder, which dot-source it. Reads the
# packages this repository publishes from packages.json, works out which
# products a pull request touches, and which packages a publish releases at
# which version.
#
# Each package has its own version, tagged '<package>/<version>'. A package is
# released when a file that counts under its folders changed since its last
# tag, or when a package it depends on is being released, because its
# requirement on that package moves. This is the scheme in 51Degrees/rust#205,
# which the per language repositories follow.
#
# Every file counts except those matched by the package's Ignore globs in
# packages.json and, unless its IgnoreDefaults is false, by
# $ReleasePlanDefaultIgnore, so a change only to documentation, tests or
# examples releases nothing. release-plan-filter.ps1 then leaves out a
# manifest whose change is only to metadata such as links. These are the
# fields and the filter of common-ci's steps/release-plan.ps1.
#
# A submodule in Path or ExtraPaths changes as one path, its own, so any move
# of it counts. Neither the globs nor the filter see inside it.

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

# The files whose changes do not release a package, being documentation,
# tests, examples and LICENSE files wherever they sit and whatever their case,
# unless the package sets IgnoreDefaults to false. These are git glob
# pathspecs from the repository root, where '**/' matches any number of
# folders, none included.
$ReleasePlanDefaultIgnore = @(
    '**/*.md'
    '**/docs/**'
    '**/tests/**'
    '**/test/**'
    '**/examples/**'
    '**/LICENSE*'
)

# The pathspecs that leave out of a package's changes the files its Ignore
# globs match and, unless IgnoreDefaults is false, the default set.
# PowerShell on Linux and macOS replaces a native command's argument that
# holds a '*' with the files it matches, if any. Each of these starts with
# ':(', which no file in a checkout starts with, so git receives it as written.
function Get-PackageExcludes($Package) {
    $defaults = $Package.IgnoreDefaults
    if ($null -ne $defaults -and $defaults -isnot [bool]) {
        throw "$($Package.Name) gives IgnoreDefaults as '$defaults', where " +
            "packages.json must give true or false."
    }
    $excludes = @($Package.Ignore | Where-Object { $_ } |
        ForEach-Object { ":(exclude,glob)$_" })
    if ($defaults -ne $false) {
        # The defaults ignore case, as one language names a folder Tests or
        # Examples where another names it tests or examples.
        $excludes = @($ReleasePlanDefaultIgnore |
            ForEach-Object { ":(exclude,glob,icase)$_" }) + $excludes
    }
    return $excludes
}

# The files under the package's folders that changed since the given tag, as
# paths from the repository root, apart from those it ignores.
function Get-ChangedFiles([string]$RepoPath, $Package, [string]$From) {
    # A failure is reported below, naming the package, whatever the caller's
    # preference. Set for this function only.
    $PSNativeCommandUseErrorActionPreference = $false
    $pathspecs = @(Get-PackagePaths $Package) + @(Get-PackageExcludes $Package)
    $files = @(& git -C $RepoPath diff --name-only $From HEAD -- $pathspecs)
    if ($LASTEXITCODE -ne 0) {
        throw "git could not list the changes to $($Package.Name) since $From."
    }
    return $files
}

# The files that count among a package's changed files. The repository's
# ci/release-plan-filter.ps1 decides when there is one, and otherwise every
# file counts. A path the filter returns that it was not given stops the
# plan, because a filter that rewrote a path would otherwise release a
# package on a file that never changed.
function Select-CountedFiles([string]$RepoPath, $Package, [string]$From,
        [string[]]$Files) {
    $filter = Join-Path $RepoPath 'ci/release-plan-filter.ps1'
    if ($Files.Count -eq 0 -or (Test-Path $filter -PathType Leaf) -eq $false) {
        return $Files
    }
    $filter = (Resolve-Path $filter).ProviderPath
    $kept = @(& $filter -RepoPath $RepoPath -Package $Package -From $From `
        -Files $Files | Where-Object { $_ })
    foreach ($file in $kept) {
        if ($Files -cnotcontains $file) {
            throw "ci/release-plan-filter.ps1 returned '$file' for " +
                "$($Package.Name), which is not one of the files it was given."
        }
    }
    return $kept
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
        $files = @(Get-ChangedFiles $RepoPath $package $tag)
        $counted = @(Select-CountedFiles $RepoPath $package $tag $files)
        if ($counted.Count -gt 0) {
            $noun = 'files'
            if ($counted.Count -eq 1) {
                $noun = 'file'
            }
            $reasons[$package.Name] =
                "changed since $last ($($counted.Count) $noun)"
        }
        # A filter may leave an exit code that was an answer, which must not
        # read as a failure to the script that called this.
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
