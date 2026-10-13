#!/usr/bin/env bash
set -euo pipefail

# Fail early with a readable message if a mounted directory is not writable by this container's user.
for dir in "$MEDIA_DIR" "$LOG_DIR" /models; do
  if [ -n "$dir" ] && [ ! -w "$dir" ]; then
    echo "ERROR: $dir is not writable by uid $(id -u). Fix the host directory permissions (see README)." >&2
    exit 1
  fi
done

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

# Detect SSL certificates, auto-generate fallback if missing, and configure Uvicorn
if [ "$#" -ge 2 ] && [ "$1" = "uvicorn" ] && [ "${SSL_ENABLED:-true}" != "false" ]; then
  SSL_KEY="${SSL_KEYFILE:-/ssl/server.key}"
  SSL_CERT="${SSL_CERTFILE:-/ssl/server.crt}"

  # If certificates are missing or unreadable, auto-generate self-signed fallback in /tmp/ssl
  if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo "NOTICE: SSL certificate ($SSL_CERT) or key ($SSL_KEY) not found."
    mkdir -p /tmp/ssl
    FALLBACK_CERT="/tmp/ssl/server.crt"
    FALLBACK_KEY="/tmp/ssl/server.key"
    if [ ! -f "$FALLBACK_CERT" ] || [ ! -f "$FALLBACK_KEY" ]; then
      echo "NOTICE: Generating fallback self-signed SSL certificates with SANs in /tmp/ssl..."
      openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$FALLBACK_KEY" \
        -out "$FALLBACK_CERT" \
        -days 365 \
        -subj "/C=IN/ST=Tamil Nadu/L=Coimbatore/O=Sri Shakthi Institute of Engineering & Technology/OU=Faculty Attendance/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:*.localhost,DNS:host.docker.internal,DNS:app,IP:127.0.0.1,IP:::1" \
        2>/dev/null || true
      chmod 600 "$FALLBACK_KEY" 2>/dev/null || true
      chmod 644 "$FALLBACK_CERT" 2>/dev/null || true
    fi
    SSL_CERT="$FALLBACK_CERT"
    SSL_KEY="$FALLBACK_KEY"
  fi

  # Process command arguments, rewriting missing certificate paths to valid SSL_CERT/SSL_KEY
  NEW_CMD=()
  has_ssl=false
  prev_opt=""

  for arg in "$@"; do
    case "$arg" in
      --ssl-certfile=*)
        cert_val="${arg#*=}"
        if [ ! -f "$cert_val" ]; then
          NEW_CMD+=("--ssl-certfile=$SSL_CERT")
        else
          NEW_CMD+=("$arg")
        fi
        has_ssl=true
        ;;
      --ssl-keyfile=*)
        key_val="${arg#*=}"
        if [ ! -f "$key_val" ]; then
          NEW_CMD+=("--ssl-keyfile=$SSL_KEY")
        else
          NEW_CMD+=("$arg")
        fi
        has_ssl=true
        ;;
      --ssl-certfile)
        prev_opt="cert"
        NEW_CMD+=("$arg")
        has_ssl=true
        ;;
      --ssl-keyfile)
        prev_opt="key"
        NEW_CMD+=("$arg")
        has_ssl=true
        ;;
      *)
        if [ "$prev_opt" = "cert" ]; then
          if [ ! -f "$arg" ]; then
            NEW_CMD+=("$SSL_CERT")
          else
            NEW_CMD+=("$arg")
          fi
          prev_opt=""
        elif [ "$prev_opt" = "key" ]; then
          if [ ! -f "$arg" ]; then
            NEW_CMD+=("$SSL_KEY")
          else
            NEW_CMD+=("$arg")
          fi
          prev_opt=""
        else
          NEW_CMD+=("$arg")
        fi
        ;;
    esac
  done

  if [ "$has_ssl" = "false" ] && [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
    echo "SSL certificate detected ($SSL_CERT). Launching Uvicorn with HTTPS..."
    NEW_CMD+=("--ssl-keyfile" "$SSL_KEY" "--ssl-certfile" "$SSL_CERT")
  fi

  set -- "${NEW_CMD[@]}"
fi

exec "$@"
