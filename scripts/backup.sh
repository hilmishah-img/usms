#!/bin/bash
#
# USMS API Backup Script
# ======================
#
# This script creates automated backups of the USMS API data, including:
# - Docker volume data (cache, databases, CSV files)
# - Environment configuration (.env file)
# - Docker compose configuration
#
# Usage:
#   ./scripts/backup.sh [OPTIONS]
#
# Options:
#   -d, --destination DIR    Backup destination directory (default: ./backups)
#   -r, --retention DAYS     Number of days to retain backups (default: 30)
#   -c, --compress          Use maximum compression (slower but smaller)
#   -v, --verbose           Verbose output
#   -h, --help              Show this help message
#
# Examples:
#   # Basic backup
#   ./scripts/backup.sh
#
#   # Backup to custom location with 60-day retention
#   ./scripts/backup.sh -d /mnt/backup -r 60
#
#   # Backup with maximum compression and verbose output
#   ./scripts/backup.sh -c -v
#
# Cron Setup:
#   # Daily backup at 2 AM
#   0 2 * * * /opt/usms-api/scripts/backup.sh -d /mnt/backup -r 30
#

set -euo pipefail  # Exit on error, undefined variable, or pipe failure

# =============================================================================
# Configuration
# =============================================================================

# Default values
BACKUP_DIR="./backups"
RETENTION_DAYS=30
COMPRESS_LEVEL=6  # gzip compression level (1-9, higher = more compression)
VERBOSE=false
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Docker settings
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
VOLUME_NAME="usms-api-data"
CONTAINER_NAME="usms-api"

# Backup file names
VOLUME_BACKUP="usms-data-${TIMESTAMP}.tar.gz"
ENV_BACKUP=".env.${TIMESTAMP}"
COMPOSE_BACKUP="docker-compose.prod-${TIMESTAMP}.yml"
MANIFEST="backup-manifest-${TIMESTAMP}.txt"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

# =============================================================================
# Functions
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${GREEN}[VERBOSE]${NC} $*"
    fi
}

show_help() {
    grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //' | sed 's/^#//'
    exit 0
}

check_dependencies() {
    log_verbose "Checking dependencies..."

    local deps=("docker" "tar" "gzip")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency not found: $dep"
            exit 1
        fi
        log_verbose "  ✓ $dep found"
    done
}

check_docker_volume() {
    log_verbose "Checking Docker volume: $VOLUME_NAME"

    if ! docker volume inspect "$VOLUME_NAME" &> /dev/null; then
        log_error "Docker volume not found: $VOLUME_NAME"
        log_error "Make sure the USMS API has been deployed at least once"
        exit 1
    fi

    log_verbose "  ✓ Volume exists"
}

create_backup_dir() {
    log_verbose "Creating backup directory: $BACKUP_DIR"

    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_verbose "  ✓ Directory created"
    else
        log_verbose "  ✓ Directory exists"
    fi
}

backup_volume() {
    log "Backing up Docker volume: $VOLUME_NAME"

    local backup_path="$BACKUP_DIR/$VOLUME_BACKUP"

    # Use docker run to access volume and create tar archive
    docker run --rm \
        -v "$VOLUME_NAME":/data:ro \
        -v "$BACKUP_DIR":/backup \
        alpine \
        tar czf "/backup/$VOLUME_BACKUP" -C /data .

    local size=$(du -h "$backup_path" | cut -f1)
    log "  ✓ Volume backup complete: $VOLUME_BACKUP ($size)"

    echo "$backup_path" >> "$BACKUP_DIR/$MANIFEST"
}

backup_env() {
    log "Backing up environment configuration"

    if [ -f "$PROJECT_ROOT/.env" ]; then
        cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/$ENV_BACKUP"
        log "  ✓ Environment backup complete: $ENV_BACKUP"
        echo "$BACKUP_DIR/$ENV_BACKUP" >> "$BACKUP_DIR/$MANIFEST"
    else
        log_warn "No .env file found, skipping"
    fi
}

backup_compose() {
    log "Backing up Docker Compose configuration"

    if [ -f "$PROJECT_ROOT/$DOCKER_COMPOSE_FILE" ]; then
        cp "$PROJECT_ROOT/$DOCKER_COMPOSE_FILE" "$BACKUP_DIR/$COMPOSE_BACKUP"
        log "  ✓ Compose backup complete: $COMPOSE_BACKUP"
        echo "$BACKUP_DIR/$COMPOSE_BACKUP" >> "$BACKUP_DIR/$MANIFEST"
    else
        log_warn "No docker-compose.prod.yml file found, skipping"
    fi
}

create_manifest() {
    log "Creating backup manifest"

    cat > "$BACKUP_DIR/$MANIFEST" << EOF
USMS API Backup Manifest
========================

Backup Date: $(date +'%Y-%m-%d %H:%M:%S')
Timestamp: $TIMESTAMP

Files in this backup:
EOF

    # Add volume backup
    if [ -f "$BACKUP_DIR/$VOLUME_BACKUP" ]; then
        echo "  - $VOLUME_BACKUP ($(du -h "$BACKUP_DIR/$VOLUME_BACKUP" | cut -f1))" >> "$BACKUP_DIR/$MANIFEST"
    fi

    # Add env backup
    if [ -f "$BACKUP_DIR/$ENV_BACKUP" ]; then
        echo "  - $ENV_BACKUP ($(du -h "$BACKUP_DIR/$ENV_BACKUP" | cut -f1))" >> "$BACKUP_DIR/$MANIFEST"
    fi

    # Add compose backup
    if [ -f "$BACKUP_DIR/$COMPOSE_BACKUP" ]; then
        echo "  - $COMPOSE_BACKUP ($(du -h "$BACKUP_DIR/$COMPOSE_BACKUP" | cut -f1))" >> "$BACKUP_DIR/$MANIFEST"
    fi

    cat >> "$BACKUP_DIR/$MANIFEST" << EOF

Restoration Instructions:
=========================

1. Stop the API service:
   docker compose -f docker-compose.prod.yml down

2. Restore the data volume:
   docker run --rm \\
     -v $VOLUME_NAME:/data \\
     -v $(pwd)/backups:/backup \\
     alpine sh -c "rm -rf /data/* && tar xzf /backup/$VOLUME_BACKUP -C /data"

3. Restore environment configuration:
   cp backups/$ENV_BACKUP .env

4. Restore Docker Compose (if needed):
   cp backups/$COMPOSE_BACKUP docker-compose.prod.yml

5. Start the API service:
   docker compose -f docker-compose.prod.yml --profile api up -d

6. Verify the service:
   docker compose -f docker-compose.prod.yml ps
   curl http://localhost:8000/health
EOF

    log "  ✓ Manifest created: $MANIFEST"
}

cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days"

    local deleted_count=0

    # Find and delete old volume backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        log_verbose "  Deleted: $(basename "$file")"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "usms-data-*.tar.gz" -mtime +"$RETENTION_DAYS" -print0)

    # Find and delete old env backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        log_verbose "  Deleted: $(basename "$file")"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name ".env.*" -mtime +"$RETENTION_DAYS" -print0)

    # Find and delete old compose backups
    while IFS= read -r -d '' file; do
        rm -f "$file"
        log_verbose "  Deleted: $(basename "$file")"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "docker-compose.prod-*.yml" -mtime +"$RETENTION_DAYS" -print0)

    # Find and delete old manifests
    while IFS= read -r -d '' file; do
        rm -f "$file"
        log_verbose "  Deleted: $(basename "$file")"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "backup-manifest-*.txt" -mtime +"$RETENTION_DAYS" -print0)

    if [ $deleted_count -gt 0 ]; then
        log "  ✓ Deleted $deleted_count old backup file(s)"
    else
        log "  ✓ No old backups to delete"
    fi
}

show_summary() {
    log ""
    log "================================================================"
    log "Backup Summary"
    log "================================================================"
    log "Backup location: $BACKUP_DIR"
    log "Backup timestamp: $TIMESTAMP"
    log ""
    log "Files created:"

    if [ -f "$BACKUP_DIR/$VOLUME_BACKUP" ]; then
        log "  ✓ $VOLUME_BACKUP ($(du -h "$BACKUP_DIR/$VOLUME_BACKUP" | cut -f1))"
    fi

    if [ -f "$BACKUP_DIR/$ENV_BACKUP" ]; then
        log "  ✓ $ENV_BACKUP"
    fi

    if [ -f "$BACKUP_DIR/$COMPOSE_BACKUP" ]; then
        log "  ✓ $COMPOSE_BACKUP"
    fi

    log "  ✓ $MANIFEST"
    log ""

    # Calculate total backup size
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Total backup directory size: $total_size"
    log ""
    log "To restore this backup, see: $BACKUP_DIR/$MANIFEST"
    log "================================================================"
}

# =============================================================================
# Main Script
# =============================================================================

main() {
    log "USMS API Backup Script Started"
    log "================================================================"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--destination)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -r|--retention)
                RETENTION_DAYS="$2"
                shift 2
                ;;
            -c|--compress)
                COMPRESS_LEVEL=9
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done

    # Change to project root
    cd "$PROJECT_ROOT"
    log_verbose "Project root: $PROJECT_ROOT"

    # Run backup steps
    check_dependencies
    check_docker_volume
    create_backup_dir
    backup_volume
    backup_env
    backup_compose
    create_manifest
    cleanup_old_backups
    show_summary

    log "Backup completed successfully!"
}

# Run main function
main "$@"
