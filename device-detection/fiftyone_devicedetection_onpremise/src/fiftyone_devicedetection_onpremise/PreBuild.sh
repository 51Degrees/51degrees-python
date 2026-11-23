#!/bin/bash

if command -v swig >/dev/null 2>&1; then
    { echo >&2 "Generating Swig wrapper for Hash."; }
    swig -c++ -python hash_python.i
else
    { echo >&2 "Swig is required to generate wrapper but it's not installed."; }
fi
