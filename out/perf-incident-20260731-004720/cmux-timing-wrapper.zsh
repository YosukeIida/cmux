#!/bin/zsh

set -u
zmodload zsh/datetime

timing_log="${CMUX_TEST_PI_TIMING_LOG:?missing CMUX_TEST_PI_TIMING_LOG}"
cmux_cli="${CMUX_BUNDLED_CLI_PATH:?missing CMUX_BUNDLED_CLI_PATH}"
started_at="$EPOCHREALTIME"
print -r -- "$$ start $started_at ${(q+)@}" >> "$timing_log"
"$cmux_cli" "$@"
exit_code=$?
finished_at="$EPOCHREALTIME"
print -r -- "$$ end $finished_at $exit_code ${(q+)@}" >> "$timing_log"
exit "$exit_code"
