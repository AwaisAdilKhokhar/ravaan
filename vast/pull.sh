#!/bin/bash
# Runs LOCALLY. Pulls one run directory with true byte-offset resume and md5 verification.
#
#   ./vast/pull.sh <host> <port> <run-dir-name> [dest]
#
# Two failures shaped this, both in session 30 on the same 6.3 GB run:
#
#   1. `scp -r` of the whole directory is ONE transfer. A reset at 2 GB lost everything,
#      and because the fetcher ran under `set -e` it died without writing the watchdog's
#      sentinel -- so the instance billed idle for an hour with nobody watching.
#   2. Per-file `scp` with retries still restarts each FILE from zero. On a link that
#      drops every few hundred MB, an 840 MB checkpoint never completes: observed
#      1.5 MB, then 378 MB, then another reset.
#
# So transfers resume at a byte offset instead: `tail -c +N` on the remote appends only
# the part that is missing, and a drop costs only what was in flight. Git Bash has no
# rsync, which is the obvious tool and is not available here.
#
# The banner Vast prints on login goes to stderr, so it cannot land in the data -- but
# the md5 check at the end is what actually proves that, rather than assuming it.
set -uo pipefail
H="root@${1:?host}"; P="${2:?port}"; RUN="${3:?run dir}"; DEST="${4:-/d/ravaan-runs}"
# -n is load-bearing: without it the in-loop ssh consumes the file listing from stdin
# and the loop silently processes exactly one entry, then reports success.
S="ssh -n -p $P -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3"
SLIST="ssh -p $P -o BatchMode=yes -o ConnectTimeout=20"
REMOTE="/workspace/runs/$RUN"
mkdir -p "$DEST/$RUN"

listing=$($SLIST "$H" "cd $REMOTE && for f in *; do printf '%s\t%s\n' \"\$f\" \"\$(stat -c%s \"\$f\")\"; done" 2>/dev/null)
[ -z "$listing" ] && { echo "could not list $REMOTE"; exit 1; }

fail=0
while IFS=$'\t' read -r name size; do
    [ -z "$name" ] && continue
    # rolling.pt is the mid-run resume artefact: useless once the run finished, and 840 MB.
    case "$name" in *_rolling.pt) echo "skip     $name (resume artefact)"; continue;; esac
    # ONLY is an optional glob, for when the link is dropping and you want the small
    # files or one specific checkpoint before committing to ~5.9 GB. Unset = everything,
    # which is the default because seven scored rungs are worth more than the transfer
    # time: re-scoring, elbo.py at K=9 and an A3/A4 re-sweep all want a choice of rung.
    #   ONLY='*.json'      ./vast/pull.sh h p run     # curve + evaluation + config first
    #   ONLY='*_fp25.pt'   ./vast/pull.sh h p run     # one checkpoint
    if [ -n "${ONLY:-}" ]; then
        # shellcheck disable=SC2254
        case "$name" in $ONLY) ;; *) continue;; esac
    fi
    dst="$DEST/$RUN/$name"
    [ -f "$dst" ] || : > "$dst"

    for attempt in $(seq 1 40); do
        have=$(stat -c%s "$dst" 2>/dev/null || echo 0)
        if [ "$have" -eq "$size" ]; then break; fi
        if [ "$have" -gt "$size" ]; then
            echo "  $name overshot ($have > $size) — restarting from zero"
            : > "$dst"; have=0
        fi
        [ "$attempt" -gt 1 ] && echo "  resume $name at $have/$size (attempt $attempt)"
        # append only the missing tail; a drop mid-stream just shortens this append
        $S "$H" "tail -c +$((have + 1)) '$REMOTE/$name'" >> "$dst" 2>/dev/null
        sleep 1
    done

    have=$(stat -c%s "$dst" 2>/dev/null || echo 0)
    if [ "$have" -ne "$size" ]; then
        echo "FAILED   $name — $have/$size after 40 attempts"; fail=1; continue
    fi
    want=$($S "$H" "md5sum '$REMOTE/$name'" 2>/dev/null | cut -d' ' -f1)
    got=$(md5sum "$dst" | cut -d' ' -f1)
    if [ "$want" = "$got" ]; then
        echo "OK       $name ($size bytes, md5 $got)"
    else
        echo "CORRUPT  $name — remote $want local $got"; fail=1
    fi
done <<< "$listing"

echo
if [ "$fail" -eq 0 ]; then
    echo "$RUN complete and md5-verified in $DEST/$RUN"
else
    echo "$RUN INCOMPLETE — rerun this script; it resumes where it stopped"
    exit 1
fi
