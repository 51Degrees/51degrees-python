# Tests that the two on-premise packages build their native code, the SWIG
# wrapper, the C++ and the C, with the warnings of -Wall -Wextra and /W4 on,
# treated as errors (-Werror, /WX) when _51DEGREES_WARNINGS_AS_ERRORS is "true"
# and only then, and that nothing turns a warning off: no -Wno-* or /wd flag,
# no lower warning level, no C runtime define that turns deprecation warnings
# off, no commented out -Werror or /WX, and no pragma in a wrapper other than
# those SWIG writes and the interface file lists.
# The interface files and the wrappers are read as text. setup.py is read as
# text, and is also run by native-build-flags.py for each platform with the
# variable set and unset, which gives back the flags it would build with.

BeforeDiscovery {
    $script:Packages = @(
        @{
            Name = 'fiftyone_devicedetection_onpremise'
            Folder = 'device-detection/fiftyone_devicedetection_onpremise'
            Interface = 'hash_python.i'
            Wrapper = 'hash_python_wrap.cxx'
        },
        @{
            Name = 'fiftyone_ipintelligence_onpremise'
            Folder = 'ip-intelligence/fiftyone_ipintelligence_onpremise'
            Interface = 'ipi_python.i'
            Wrapper = 'ipi_python_wrap.cxx'
        }
    )
}

Describe '<Name> native build flags' -ForEach $Packages {
    BeforeAll {
        $root = Join-Path $PSScriptRoot '..' $Folder
        $script:Lines = @(Get-Content -LiteralPath (Join-Path $root 'setup.py'))
        # The lines that are code, with any comment at the end taken off.
        $script:Code = @($script:Lines |
            Where-Object { $_ -notmatch '^\s*#' } |
            ForEach-Object { $_ -replace '\s#.*$', '' })
        $script:Comments = @($script:Lines | Where-Object { $_ -match '^\s*#' })

        function Get-Count([string]$Pattern) {
            @($script:Code | Where-Object { $_ -match $Pattern }).Count
        }

        $script:SetupPy = Join-Path $root 'setup.py'
        $script:Python = $IsWindows ? 'python' : 'python3'

        # The flags setup.py builds with on $Platform with
        # _51DEGREES_WARNINGS_AS_ERRORS set to $Value, or unset when it is
        # empty.
        function Get-BuildFlags([string]$Platform, [string]$Value) {
            $name = '_51DEGREES_WARNINGS_AS_ERRORS'
            $before = [Environment]::GetEnvironmentVariable($name)
            try {
                [Environment]::SetEnvironmentVariable($name,
                    $Value ? $Value : $null)
                $json = & $script:Python -I `
                    (Join-Path $PSScriptRoot 'native-build-flags.py') `
                    $script:SetupPy $Platform
                if ($LASTEXITCODE -ne 0) {
                    throw "native-build-flags.py failed for $script:SetupPy"
                }
            } finally {
                [Environment]::SetEnvironmentVariable($name, $before)
            }
            $json | ConvertFrom-Json
        }
    }

    It 'turns no warning off and lowers no warning level' {
        $switches = @($script:Code | Where-Object {
            $_ -match "['`"]-Wno-[a-z]|/wd\d|/w[1-4]\d|'-w'|'/w'|'/W[0-3]'|/external:W0"
        })
        $switches | Should -BeNullOrEmpty
    }

    It 'defines nothing that turns off the C runtime deprecation warnings' {
        $defines = @($script:Code | Where-Object {
            $_ -match '_CRT_SECURE_NO_WARNINGS|(?<!SWIG_NO)_CRT_SECURE_NO_DEPRECATE|_CRT_NONSTDC_NO_DEPRECATE'
        })
        $defines | Should -BeNullOrEmpty
    }

    It 'has no -Werror or /WX commented out' {
        $commented = @($script:Comments | Where-Object {
            $_ -match "'(-Werror|/WX)'"
        })
        $commented | Should -BeNullOrEmpty
    }

    # The builds 51Degrees runs set _51DEGREES_WARNINGS_AS_ERRORS to true, and
    # every warning is an error there. An install from source anywhere else
    # leaves it unset, so a warning shows but never stops the install. Either
    # way the warnings of -Wall -Wextra and /W4 are on.
    It '<Platform>, _51DEGREES_WARNINGS_AS_ERRORS "<Value>": warnings on, errors <Errors>' -ForEach @(
        foreach ($platform in 'win32', 'linux', 'darwin') {
            @{ Platform = $platform; Value = 'true'; Errors = $true }
            @{ Platform = $platform; Value = 'TRUE'; Errors = $true }
            @{ Platform = $platform; Value = 'True'; Errors = $true }
            @{ Platform = $platform; Value = ''; Errors = $false }
            @{ Platform = $platform; Value = 'false'; Errors = $false }
            @{ Platform = $platform; Value = '1'; Errors = $false }
            @{ Platform = $platform; Value = 'yes'; Errors = $false }
        }
    ) {
        $flags = Get-BuildFlags $Platform $Value
        # The wrapper, the C++ and the C.
        $compiles = @($flags.extensions + $flags.libraries |
            ForEach-Object { , @($_.compile) })
        $compiles.Count | Should -Be 3
        $link = @($flags.extensions[0].link)
        if ($Platform -eq 'win32') {
            $levels = @('/W4')
            $errorFlag = '/WX'
        } else {
            $levels = @('-Wall', '-Wextra')
            $errorFlag = '-Werror'
        }
        foreach ($compile in $compiles) {
            foreach ($level in $levels) {
                $compile | Should -Contain $level
            }
            @($compile | Where-Object {
                $_ -match '^-Wno-|^/wd|^/W[0-3]$|^-w$|^/w$'
            }) | Should -BeNullOrEmpty
            if ($Errors) {
                $compile | Should -Contain $errorFlag
            } else {
                $compile | Should -Not -Contain $errorFlag
            }
        }
        if ($Platform -eq 'win32') {
            if ($Errors) {
                $link | Should -Contain '/WX'
            } else {
                $link | Should -Not -Contain '/WX'
            }
        }
    }

    It 'takes the warning options the compiler is given before ours out' {
        # setuptools gives MSVC /W3, and cl warns (D9025) when /W4 overrides
        # it, which /WX does not make an error. Python's own build flags can
        # give GCC and Clang a -Wno-<name>.
        Get-Count '^\s*def remove_inherited_warning_options\(compiler\):' |
            Should -Be 1
        Get-Count '^\s*for options in \(compiler\.compile_options,$' |
            Should -Be 1
        Get-Count '^\s*compiler\.compile_options_debug\):$' |
            Should -Be 1
        Get-Count 'not o\.startswith\("-Wno-"\)' | Should -Be 1
        Get-Count '^\s*remove_inherited_warning_options\(self\.compiler\)' |
            Should -Be 2
        Get-Count '^\s*cmdclass=\{"build_ext":\s*NoSuffixBuilder,\s*"build_clib":\s*LibraryBuilder\}' |
            Should -Be 1
    }

    It 'gives the wrapper its own flags' {
        Get-Count '^\s*extra_compile_args=extra_compile_args,' |
            Should -Be 1
    }
}

Describe '<Name> SWIG wrapper' -ForEach $Packages {
    BeforeAll {
        $source = Join-Path $PSScriptRoot '..' $Folder 'src' $Name
        $script:Interface = Get-Content -Raw `
            -LiteralPath (Join-Path $source $Interface)
        $script:WrapperLines = @(Get-Content `
            -LiteralPath (Join-Path $source $Wrapper))
    }

    It 'asks SWIG to leave on the warnings it would turn off' {
        foreach ($name in 'SWIG_MSC_UNSUPPRESS_4505',
                'SWIG_NO_CRT_SECURE_NO_DEPRECATE',
                'SWIG_NO_SCL_SECURE_NO_DEPRECATE') {
            $script:Interface | Should -Match "(?m)^#define $name\s*$"
        }
    }

    It 'has no pragma other than those the interface file lists' {
        # The pragmas SWIG writes that no SWIG setting removes, each listed in
        # the interface file comment with the reason it changes nothing here,
        # and the 4505 one, which SWIG_MSC_UNSUPPRESS_4505 leaves out.
        $known = @(
            '#pragma warning(disable : 4505)'
            '#pragma warning disable 592'
            '#pragma GCC diagnostic push'
            '#pragma GCC diagnostic pop'
            '#pragma GCC diagnostic ignored "-Wregister"'
            '#pragma GCC diagnostic ignored "-Wdeprecated"'
            '#pragma GCC diagnostic ignored "-Wdeprecated-declarations"'
            '#pragma warning(push)'
            '#pragma warning(pop)'
            '#pragma warning(disable: 4996)'
        )
        $other = @($script:WrapperLines |
            Where-Object { $_ -match '^\s*#\s*pragma\b' } |
            ForEach-Object {
                ($_ -replace '/\*.*$', '' -replace '^\s*#\s*', '#').Trim()
            } |
            Where-Object { $_ -notin $known })
        $other | Should -BeNullOrEmpty
    }

    It 'lists each SWIG pragma in the interface file comment' {
        foreach ($text in '-Wregister', '4505', '592', '-Wdeprecated',
                '4996') {
            $script:Interface | Should -Match ([regex]::Escape($text))
        }
    }
}
