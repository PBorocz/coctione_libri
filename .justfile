# Directory for shared image exports
shared_images := "/Users/Shared/images"

# Root project directory
project_root := justfile_directory()

default:
	@just --list

################################################################################
# Development environment support
################################################################################
# Build development container
podman-dev-build:
	#!/usr/bin/env fish
	set TIMESTAMP (date +"%Y-%m-%dT%H:%M")
	podman rm --force coctione_libri || true
	podman build \
	  --build-arg BUILD_TIMESTAMP="$TIMESTAMP" \
	  --tag       coctione_libri:latest .

# Run development container
podman-dev-run:
	cat .env.common .env.development > .env
	podman rm --force coctione_libri_dev || true
	podman run \
	  --detach \
	  --publish 6022:6022 \
	  --name coctione_libri_dev	\
	  --env-file .env \
	  --env PATH_DATA="/app/data" \
	  --volume "{{project_root}}/data:/app/data:Z" \
	  coctione_libri:latest
	podman logs --follow=true coctione_libri_dev

# Stop development container
podman-dev-stop:
	podman stop coctione_libri_dev

# Run development raw flask server
dev-run-raw:
	#!/usr/bin/env fish
	set -x FLASK_RUN_PORT        "6022"
	set -x STORAGE_DOCS_DIR_NAME "documents"
	set -x STORAGE_META_DB_NAME  "meta.sqlite3"
	cat .env.common .env.development > .env
	sass --update app/static/css/sass/styles.scss app/static/css/coctione_libri.css
	uv run flask run --debug --host localhost --port $FLASK_RUN_PORT

################################################################################
# Production environment support
################################################################################

# Full release workflow: build-image, export to shared and update environment file
deploy-to-prod:
	#!/usr/bin/env fish
	# echo "🔧 FIXME: Need to install pre-commit!"
	# echo "🔧 Running pre-commit..."
	# pre-commit autoupdate
	# pre-commit run

	echo "🔧 Refreshing CSS..."
	sass --update app/static/css/sass/styles.scss app/static/css/coctione_libri.css

	echo "🔧 Building container image..."
	set TIMESTAMP (date +%Y-%m-%dT%H-%M-%s)
	podman build --tag coctione_libri:$TIMESTAMP .

	echo "🔧 Exporting to shared storage..."
	mkdir -p /Users/Shared/images
	podman save --output {{shared_images}}/coctione_libri-$TIMESTAMP.tar coctione_libri:$TIMESTAMP

	echo "🔧 Updating permissions on exported image..."
	chmod 644 {{shared_images}}/coctione_libri-$TIMESTAMP.tar

	echo "🔧 Refreshing environment configuration..."
	set ENV_PATH "/Users/service/services/shared/environments/coctione_libri.env"
	cat .env.common .env.production > /tmp/coctione_libri.env
	sudo cp /tmp/coctione_libri.env $ENV_PATH
	sudo chown service:staff        $ENV_PATH
	sudo chmod 400                  $ENV_PATH

	# echo "🔧 Cleaning up old images..."
	just cleanup-prod-images

	echo ""
	echo "✅ Release complete: coctione_libri-$TIMESTAMP.tar"
	echo ""
	echo "To deploy, switch to service account:"
	echo "  sudo -u service -i"
	echo "  cd ~/services && ./manage deploy coctione_libri"

# Push current code to github.
push:
	jj bookmark set --revision  @- trunk
	jj git push     --revisions @-

# Cleanup old image tars (keep last 3)
cleanup-prod-images:
	#!/usr/bin/env fish
	cd {{shared_images}}
	set old_tars (ls -t coctione_libri-*.tar 2>/dev/null | tail -n +4)
	if test -n "$old_tars"
	echo "🔧 Removing old images: $old_tars..."
	rm -f $old_tars
	echo "✅ Cleanup complete"
	else
	echo "No old images to clean up"
	end

import '../.justfile'
