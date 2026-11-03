@for %%X in (swig.exe) do (set SWIG_EXE=%%~$PATH:X)
@if defined SWIG_EXE (
@echo SWIG auto generated code being rebuilt.
swig -c++ -python hash_python.i
) else (
@echo SWIG not found. SWIG auto generated code will not be rebuilt.
)