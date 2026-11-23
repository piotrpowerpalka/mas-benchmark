#!/usr/bin/env bash
set -uo pipefail

# Umieść skrypt w katalogu scripts/ repozytorium.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$ROOT_DIR/logs"
RUN_SCRIPT="$ROOT_DIR/scripts/run-exp.sh"
STATUS_LOG="$LOGS_DIR/check-and-rerun.log"
DETAIL_LOG="$LOGS_DIR/check-and-rerun-details.log"

if [[ ! -f "$RUN_SCRIPT" || ! -d "$LOGS_DIR" ]]; then
    echo "BŁĄD: brak $RUN_SCRIPT lub $LOGS_DIR" >&2
    exit 1
fi

# run-exp.sh zapisuje wyniki zawsze w ROOT_DIR/logs.
if [[ "$(pwd -P)" != "$(cd "$LOGS_DIR" && pwd -P)" ]]; then
    echo "BŁĄD: uruchom skrypt z katalogu $LOGS_DIR" >&2
    exit 1
fi

# UWAGA: czyszczenie dotyczy całego hosta Docker, także innych projektów.
: > "$STATUS_LOG"
: > "$DETAIL_LOG"

cleanup_docker() {
    echo "Czyszczenie Dockera: wszystkie kontenery oraz nieużywane obrazy, sieci i wolumeny..." | tee -a "$DETAIL_LOG"

    if ! docker info >/dev/null 2>&1; then
        echo "BŁĄD: Docker nie działa lub brak uprawnień do demona Dockera." | tee -a "$DETAIL_LOG" >&2
        return 1
    fi

    # docker rm -f zatrzymuje i usuwa wszystkie kontenery (również uruchomione).
    local containers
    if ! containers="$(docker ps -aq)"; then
        echo "BŁĄD: nie udało się pobrać listy kontenerów." | tee -a "$DETAIL_LOG" >&2
        return 1
    fi
    if [[ -n "$containers" ]]; then
        # shellcheck disable=SC2086
        docker rm -f $containers >> "$DETAIL_LOG" 2>&1 || return 1
    fi

    # Usuwa nieużywane obrazy, sieci, cache i anonimowe wolumeny.
    # Nazwane wolumeny nie są usuwane przez docker system prune.
    docker system prune -af --volumes >> "$DETAIL_LOG" 2>&1 || return 1
    echo "Czyszczenie Dockera zakończone." | tee -a "$DETAIL_LOG"
}

if ! cleanup_docker; then
    echo "BŁĄD: czyszczenie Dockera nie powiodło się. Przerywam obliczenia." | tee -a "$DETAIL_LOG" >&2
    exit 1
fi

has_stats() {
    local directory="$1" file
    for file in "$directory"/stats_logs_docker-compose-*; do
        [[ -f "$file" ]] && return 0
    done
    return 1
}

# Nazwa generowana przez run-exp.sh:
# logs_PLATFORM-cC-nN-rR-msSIZE-TYPE-gG-m1GB-cpu1-pPERIOD-seedSEED
pattern='^logs_(prosody|tigase|jade|jason|uagents|uagents-agentverse)-c([0-9]+)-n([0-9]+)-r([0-9]+)-ms([0-9]+)-(inform|query|cfp)-g([0-9]+)-m([^/]+)-cpu([^/]+)-p([0-9]+)-seed([0-9]+)$'

ok=0
retried=0
failed=0
skipped=0

for dir in */; do
    [[ -d "$dir" ]] || continue
    name="${dir%/}"

    if has_stats "$dir"; then
        printf '%s; OK\n' "$name" | tee -a "$STATUS_LOG"
        ((ok+=1))
        continue
    fi

    if [[ ! "$name" =~ $pattern ]]; then
        printf '%s; SKIPPED_INVALID_NAME\n' "$name" | tee -a "$STATUS_LOG"
        ((skipped+=1))
        continue
    fi

    platform="${BASH_REMATCH[1]}"
    containers="${BASH_REMATCH[2]}"
    agents="${BASH_REMATCH[3]}"
    repeats="${BASH_REMATCH[4]}"
    message_size="${BASH_REMATCH[5]}"
    comm_type="${BASH_REMATCH[6]}"
    group_size="${BASH_REMATCH[7]}"
    mem="${BASH_REMATCH[8]}"
    cpu="${BASH_REMATCH[9]}"
    period="${BASH_REMATCH[10]}"
    seed="${BASH_REMATCH[11]}"

    if [[ "$mem" != "1GB" || "$cpu" != "1" ]]; then
        printf '%s; SKIPPED_UNSUPPORTED_RESOURCES\n' "$name" | tee -a "$STATUS_LOG"
        ((skipped+=1))
        continue
    fi

    cmd=(bash "$RUN_SCRIPT" "$containers" "$platform" "$comm_type" "$agents" "$repeats" "$message_size" false "$group_size" "$period" "$seed")
    printf '%s; RERUN_STARTED\n' "$name" | tee -a "$STATUS_LOG"
    printf '\n===== %s =====\n' "$name" >> "$DETAIL_LOG"
    printf 'COMMAND: ' >> "$DETAIL_LOG"
    printf '%q ' "${cmd[@]}" >> "$DETAIL_LOG"
    printf '\n' >> "$DETAIL_LOG"

    ((retried+=1))
    if "${cmd[@]}" >> "$DETAIL_LOG" 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi

    if has_stats "$dir"; then
        printf '%s; RERUN_OK; exit_code=%s\n' "$name" "$exit_code" | tee -a "$STATUS_LOG"
        ((ok+=1))
    else
        printf '%s; RERUN_FAILED; exit_code=%s\n' "$name" "$exit_code" | tee -a "$STATUS_LOG"
        ((failed+=1))
    fi
done

printf '\nPodsumowanie: OK=%d, uruchomiono ponownie=%d, nieudane=%d, pominięte=%d\n' "$ok" "$retried" "$failed" "$skipped"
printf 'Statusy: %s\nSzczegóły: %s\n' "$STATUS_LOG" "$DETAIL_LOG"
(( failed == 0 ))
