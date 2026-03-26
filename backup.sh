#!/bin/bash
#
# Script de backup para el Sistema de Seguimiento de Entregas
# Autor: Matias Barreto (www.matiasbarreto.com)
# Version: 1.0.0
#
# Uso: ./backup.sh
# Programar en crontab para backups automaticos diarios:
#   0 2 * * * /path/to/backup.sh
#

set -e

# Configuracion
BACKUP_DIR="${BACKUP_DIR:-./backups}"
PROJECT_DIR="$(dirname "$0")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funcion de logging
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ADVERTENCIA:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

log "Iniciando backup del Sistema de Seguimiento de Entregas v1.0.0"
log "Directorio de backup: $BACKUP_DIR"

# Verificar que existe el directorio de datos
if [ ! -d "$PROJECT_DIR/nocodb-data" ]; then
    error "No se encontro el directorio nocodb-data en $PROJECT_DIR"
fi

# Nombre del archivo de backup
BACKUP_FILE="entregas-backup-${TIMESTAMP}.tar.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

log "Creando backup: $BACKUP_FILE"

# Crear tarball excluyendo archivos innecesarios
tar -czf "$BACKUP_PATH" \
    --exclude='*.log' \
    --exclude='*.tmp' \
    --exclude='.cache' \
    --exclude='nc/uploads/tmp' \
    -C "$PROJECT_DIR" \
    nocodb-data/

# Verificar que se creo correctamente
if [ -f "$BACKUP_PATH" ]; then
    SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    log "Backup creado exitosamente: $BACKUP_FILE ($SIZE)"
else
    error "No se pudo crear el archivo de backup"
fi

# Crear archivo de informacion del backup
cat > "$BACKUP_DIR/backup-${TIMESTAMP}.info" << EOF
Backup creado: $(date '+%Y-%m-%d %H:%M:%S')
Archivo: $BACKUP_FILE
Tamano: $SIZE
Version del sistema: v1.0.0
Desarrollado por: Matias Barreto (www.matiasbarreto.com)
EOF

log "Informacion del backup guardada"

# Limpiar backups antiguos (mas de RETENTION_DIAS dias)
log "Limpiando backups antiguos (mas de $RETENTION_DAYS dias)..."
DELETED=$(find "$BACKUP_DIR" -name "entregas-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
find "$BACKUP_DIR" -name "backup-*.info" -mtime +$RETENTION_DAYS -delete

if [ "$DELETED" -gt 0 ]; then
    log "Eliminados $DELETED backups antiguos"
else
    log "No hay backups antiguos para eliminar"
fi

# Listar backups existentes
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "entregas-backup-*.tar.gz" | wc -l)
log "Total de backups disponibles: $BACKUP_COUNT"
log "Ubicacion: $BACKUP_DIR"

# Mostrar ultimos 5 backups
echo ""
echo "Ultimos backups:"
ls -lht "$BACKUP_DIR"/entregas-backup-*.tar.gz 2>/dev/null | head -5 | awk '{print $9, "("$5")"}'

log "Backup completado exitosamente"
exit 0
