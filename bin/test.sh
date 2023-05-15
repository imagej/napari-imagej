#!/bin/sh

dir=$(dirname "$0")
cd "$dir/.."

modes="
| Testing ImageJ2 + original ImageJ |NAPARI_IMAGEJ_INCLUDE_IMAGEJ_LEGACY=TRUE
|    Testing ImageJ2 standalone     |NAPARI_IMAGEJ_INCLUDE_IMAGEJ_LEGACY=FALSE
|  Testing Fiji Is Just ImageJ(2)   |NAPARI_IMAGEJ_IMAGEJ_DIRECTORY_OR_ENDPOINT=sc.fiji:fiji:2.12.0
"

echo "$modes" | while read mode
do
  test "$mode" || continue
  msg="${mode%|*}|"
  expr=${mode##*|}
  var=${expr%=*}
  value=${expr##*=}
  echo "-------------------------------------"
  echo "$msg"
  echo "-------------------------------------"
  export $var="$value"
  if [ $# -gt 0 ]
  then
    python -m pytest -p no:faulthandler $@
  else
    python -m pytest -p no:faulthandler tests
  fi
  code=$?
  if [ $code -ne 0 ]
  then
    # HACK: `while read` creates a subshell, which can't modify the parent
    # shell's variables. So we save the failure code to a temporary file.
    echo $code >exitCode.tmp
  fi
  unset $var
done
exitCode=0
if [ -f exitCode.tmp ]
then
  exitCode=$(cat exitCode.tmp)
  rm -f exitCode.tmp
fi
exit "$exitCode"
