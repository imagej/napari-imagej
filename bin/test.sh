#!/bin/sh

dir=$(dirname "$0")
cd "$dir/.."

if [ $# -gt 0 ]
then
  python -m pytest $@
else
  python -m pytest tests/
fi
