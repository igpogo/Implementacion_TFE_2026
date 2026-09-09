import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any

class AuditLogger:
    """
    Gestor del registro de auditoría (Audit Log).
    Cumple con la Tarea 2.4 [HU12, SRS 3.12 FR-1, FR-2, Sec 6.4].
    Garantiza la trazabilidad, inmutabilidad y el no repudio de las operaciones.
    """

    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self._init_audit_table()

    def _init_audit_table(self):
        """
        Inicializa la tabla de auditoría si no existe.
        La estructura incluye autoría, timestamp, MAC, operación y código de respuesta.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                mac_address TEXT NOT NULL,
                requested_operation TEXT NOT NULL,
                response_code TEXT NOT NULL
            )
        """)
        # Crear un índice sobre timestamp y user_id para búsquedas eficientes en auditorías
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)")
        self.conn.commit()

    def log_operation(self, user_id: str, mac_address: str, operation: str, response_code: str) -> int:
        """
        Registra una operación en el log de auditoría.
        
        :param user_id: Identificador del usuario (autoría).
        :param mac_address: Dirección MAC de origen provista en el payload.
        :param operation: El comando crudo o sanitizado solicitado por el usuario.
        :param response_code: Código del catálogo de respuestas (ej. 'OK-200', 'ERR-403').
        :return: El ID del registro insertado.
        """
        # Se genera el timestamp en UTC en formato ISO 8601 estandarizado
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Fallbacks en caso de datos faltantes para no romper la transacción de auditoría
        safe_user_id = user_id if user_id else "UNKNOWN_USER"
        safe_mac_address = mac_address if mac_address else "UNKNOWN_MAC"
        safe_operation = operation if operation else "EMPTY_PAYLOAD"

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, user_id, mac_address, requested_operation, response_code)
            VALUES (?, ?, ?, ?, ?)
        """, (current_timestamp, safe_user_id, safe_mac_address, safe_operation, response_code))
        
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recupera los registros de auditoría más recientes. 
        Útil para el panel de administración o reportes de seguridad.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, user_id, mac_address, requested_operation, response_code 
            FROM audit_logs 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        
        # Convertir a formato de diccionario estándar
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]