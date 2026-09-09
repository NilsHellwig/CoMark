#!/bin/sh
set -e

# Local compose self-migrates on start. In Cloud Run the deploy workflow runs
# migrations against Neon, so the container sets RUN_MIGRATIONS=0.
if [ "${RUN_MIGRATIONS:-1}" != "0" ]; then
	echo "› Applying database migrations"
	alembic upgrade head
fi

exec "$@"
