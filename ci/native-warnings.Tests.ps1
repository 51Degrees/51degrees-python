# Tests that the two on-premise packages build their native code, the SWIG
# wrapper, the C++ and the C, with the warnings of -Wall -Wextra and /W4 on and
# treated as errors, and that nothing turns a warning off: no -Wno-* or /wd
# flag, no lower warning level, no C runtime define that turns deprecation
# warnings off, no commented out -Werror or /WX, and no pragma in a wrapper
# other than those SWIG writes and the interface file lists.
# setup.py, the interface files and the wrappers are read as text.

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
    }

    It 'turns no warning off and lowers no warning level' {
        $switches = @($script:Code | Where-Object {
            $_ -match "-Wno-|/wd\d|/w[1-4]\d|'-w'|'/w'|'/W[0-3]'|/external:W0"
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

    It 'asks for -Wall, -Wextra and -Werror for the C++ and the C' {
        Get-Count "'-Wall'" | Should -BeGreaterOrEqual 2
        Get-Count "'-Wextra'" | Should -BeGreaterOrEqual 2
        Get-Count "'-Werror'" | Should -BeGreaterOrEqual 2
    }

    It 'asks for /W4 and /WX for the C++ and the C, and /WX for the link' {
        Get-Count "'/W4'" | Should -BeGreaterOrEqual 2
        Get-Count "'/WX'" | Should -BeGreaterOrEqual 3
    }

    It 'takes the warning level setuptools gives MSVC out, so /W4 is the only one' {
        # cl warns (D9025) when /W4 overrides another level, and /WX does not
        # make that an error.
        Get-Count '^\s*def remove_msvc_warning_level\(compiler\):' |
            Should -Be 1
        Get-Count 'compiler\.compile_options,\s*compiler\.compile_options_debug' |
            Should -Be 1
        Get-Count '^\s*remove_msvc_warning_level\(self\.compiler\)' |
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
