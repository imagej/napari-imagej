#!/bin/sh
dir=$(dirname "$0")
cd "$dir/.."
echo "--> blacking"
black src tests
echo "--> flaking"
flake8 src tests
echo "--> isorting"
isort src tests
echo "--> Done!"
