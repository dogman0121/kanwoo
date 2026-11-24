#!/usr/bin/env bash

usage() {
  printf 'Usage: bash dev.sh [--mode=all|backend|frontend]\n'
}

run_service() {
  local service=$1
  shift
  cd -- "$root_dir/$service" || exit 1
  exec "$@"
}

stop_services() {
  local status=$1
  trap '' INT TERM
  kill -TERM -- "-$backend_pid" "-$frontend_pid" 2>/dev/null
  wait "$backend_pid" "$frontend_pid" 2>/dev/null
  exit "$status"
}

mode=all
if (( $# == 1 )); then
  case "$1" in
    --mode=*) mode=${1#--mode=} ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
  esac
elif (( $# > 1 )); then
  usage >&2
  exit 1
fi

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || exit 1

case "$mode" in
  backend)
    run_service backend poetry run dev
    ;;
  frontend)
    run_service frontend npm run dev
    ;;
  all)
    # Give each service a process group so shutdown also reaches its children.
    set -m
    run_service backend poetry run dev &
    backend_pid=$!
    run_service frontend npm run dev &
    frontend_pid=$!
    trap 'stop_services 130' INT
    trap 'stop_services 143' TERM

    wait "$backend_pid"
    backend_status=$?
    wait "$frontend_pid"
    frontend_status=$?
    if (( backend_status != 0 )); then
      exit "$backend_status"
    fi
    exit "$frontend_status"
    ;;
  *)
    printf 'Invalid mode: %s\n' "$mode" >&2
    usage >&2
    exit 1
    ;;
esac
