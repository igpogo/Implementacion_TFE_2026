import sqlite3
import json
from typing import Dict, Any, List, Optional

class DatabaseExecutionError(Exception):
    """Excepción lanzada cuando ocurre un error de ejecución SQL."""
    pass

class SecurityViolationError(Exception):
    """Excepción lanzada cuando un usuario intenta acceder o modificar recursos ajenos sin permisos de Admin."""
    pass

class DataFormatter:
    """Utilidad para renderizar los resultados en formatos aptos para correos electrónicos (Task 3.7)."""
    
    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> str:
        return json.dumps(data, indent=4, ensure_ascii=False)
    
    @staticmethod
    def to_ascii_table(data: List[Dict[str, Any]]) -> str:
        if not data:
            return "No se encontraron registros."
        
        # Obtener nombres de columnas
        headers = list(data[0].keys())
        # Calcular ancho máximo por columna
        col_widths = {h: len(str(h)) for h in headers}
        for row in data:
            for h in headers:
                col_widths[h] = max(col_widths[h], len(str(row.get(h, ''))))
                
        # Construir separador
        separator = "+" + "+".join("-" * (col_widths[h] + 2) for h in headers) + "+"
        
        # Construir cabecera
        header_row = "|" + "|".join(f" {str(h).ljust(col_widths[h])} " for h in headers) + "|"
        
        lines = [separator, header_row, separator]
        
        # Construir filas
        for row in data:
            line = "|" + "|".join(f" {str(row.get(h, '')).ljust(col_widths[h])} " for h in headers) + "|"
            lines.append(line)
            
        lines.append(separator)
        return "\n".join(lines)


class DatabaseExecutor:
    """
    Motor de ejecución SQL seguro que implementa:
    - Task 3.3: Creación de Campos y Valores
    - Task 3.4: Lectura de Datos de Usuario
    - Task 3.5: Modificación de Registros
    - Task 3.6: Borrado y Permisos de Administrador
    - Task 3.7: Filtros y Formato de Salida
    """

    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.conn.row_factory = sqlite3.Row
        self._init_metadata_registry()

    def _init_metadata_registry(self):
        """Inicializa una tabla del sistema para rastrear quién es el dueño de cada tabla (Task 3.6)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _sys_table_owners (
                table_name TEXT PRIMARY KEY,
                owner_id TEXT
            )
        """)
        self.conn.commit()

    def _verify_table_ownership(self, cursor: sqlite3.Cursor, tabla: str, user_id: str, is_admin: bool):
        """Verifica si el usuario es dueño de la tabla o si tiene rol de administrador."""
        cursor.execute("SELECT owner_id FROM _sys_table_owners WHERE table_name = ?", (tabla,))
        row = cursor.fetchone()
        if not row:
            raise DatabaseExecutionError(f"La tabla '{tabla}' no existe o no está registrada.")
        
        if not is_admin and row["owner_id"] != user_id:
            raise SecurityViolationError(f"Permiso denegado. No eres el propietario de la tabla '{tabla}'.")

    def execute_parsed_command(self, action: str, data: Dict[str, Any], user_id: str, is_admin: bool = False, output_format: str = "table") -> Dict[str, Any]:
        """Enruta la acción validada a su método correspondiente inyectando el contexto de seguridad."""
        tabla = data.get("tabla")
        cursor = self.conn.cursor()

        try:
            # -------------------------------------------------------------------------
            # Task 3.3: Endpoint CRUD: Creación de Campos y Valores [HU2, SRS 3.5]
            # -------------------------------------------------------------------------
            if action == "CREAR_TABLA":
                columnas = dict(data["columnas"])
                # Inyectamos columna de sistema para Row-Level Security
                columnas["_owner_id"] = "TEXT" 
                cols_def = ", ".join([f'"{k}" {v}' for k, v in columnas.items()])
                
                sql = f'CREATE TABLE "{tabla}" ({cols_def});'
                cursor.execute(sql)
                
                # Registrar propiedad
                cursor.execute("INSERT INTO _sys_table_owners (table_name, owner_id) VALUES (?, ?)", (tabla, user_id))
                self.conn.commit()
                
                # Omitir metadato interno en la notificación del usuario
                columnas.pop("_owner_id", None)
                return {
                    "action": action, 
                    "tabla": tabla, 
                    "email_body": f"Tabla '{tabla}' creada con éxito.\nCampos generados: {', '.join(columnas.keys())}"
                }

            elif action == "CREAR":
                self._verify_table_ownership(cursor, tabla, user_id, is_admin)
                registro = dict(data["registro"])
                # Forzamos la inserción del propietario del registro
                registro["_owner_id"] = user_id 
                
                cols = ", ".join([f'"{k}"' for k in registro.keys()])
                placeholders = ", ".join(["?"] * len(registro))
                sql = f'INSERT INTO "{tabla}" ({cols}) VALUES ({placeholders});'
                
                cursor.execute(sql, list(registro.values()))
                self.conn.commit()
                
                # Eliminamos '_owner_id' para la notificación visual del usuario
                del registro["_owner_id"] 
                return {
                    "action": action, 
                    "tabla": tabla, 
                    "email_body": f"Registro creado con éxito en '{tabla}'.\nValores insertados:\n{DataFormatter.to_json([registro])}"
                }

            # -------------------------------------------------------------------------
            # Task 3.4 & 3.7: Lectura de Datos, Filtros y Formato de Salida [HU1, HU5]
            # -------------------------------------------------------------------------
            elif action == "LEER":
                self._verify_table_ownership(cursor, tabla, user_id, is_admin)
                filtros = data.get("filtros", {})
                params = []
                where_clauses = []

                # Aislamiento de datos: si no es admin, solo lee sus propias filas
                if not is_admin:
                    where_clauses.append(' "_owner_id" = ? ')
                    params.append(user_id)

                for k, v in filtros.items():
                    where_clauses.append(f' "{k}" = ? ')
                    params.append(v)

                where_sql = " AND ".join(where_clauses)
                sql = f'SELECT * FROM "{tabla}"' + (f" WHERE {where_sql}" if where_sql else "")
                
                cursor.execute(sql, params)
                rows = [dict(row) for row in cursor.fetchall()]
                
                # Limpiar columna de sistema antes de retornar y renderizar
                for r in rows:
                    r.pop('_owner_id', None)

                # Formatear salida según preferencia
                formatted_data = DataFormatter.to_ascii_table(rows) if output_format == "table" else DataFormatter.to_json(rows)

                return {
                    "action": action, 
                    "tabla": tabla, 
                    "datos": rows,  # <-- Se devuelve siempre la lista de filas (vacía o poblada)
                    "filas_afectadas": len(rows),
                    "email_body": f"Resultados de su consulta en '{tabla}':\n\n{formatted_data}"
                }

            # -------------------------------------------------------------------------
            # Task 3.5: Endpoint CRUD: Modificación de Registros [HU3, SRS 3.6]
            # -------------------------------------------------------------------------
            elif action == "MODIFICAR":
                self._verify_table_ownership(cursor, tabla, user_id, is_admin)
                valores = data["valores"]
                condicion = data["condicion"]
                
                set_clause = ", ".join([f'"{k}" = ?' for k in valores.keys()])
                where_clauses = [f'"{k}" = ?' for k in condicion.keys()]
                params = list(valores.values()) + list(condicion.values())

                if not is_admin:
                    where_clauses.append(' "_owner_id" = ? ')
                    params.append(user_id)

                where_sql = " AND ".join(where_clauses)
                sql = f'UPDATE "{tabla}" SET {set_clause} WHERE {where_sql};'
                
                cursor.execute(sql, params)
                self.conn.commit()
                
                return {
                    "action": action, 
                    "tabla": tabla, 
                    "email_body": f"Se han modificado {cursor.rowcount} registro(s) en la tabla '{tabla}'."
                }

            # -------------------------------------------------------------------------
            # Task 3.6: Endpoint CRUD: Borrado de Valores, Campos o Tablas [HU4, SRS 3.7]
            # -------------------------------------------------------------------------
            elif action == "ELIMINAR":
                self._verify_table_ownership(cursor, tabla, user_id, is_admin)
                condicion = data.get("condicion", {})
                where_clauses = []
                params = []

                for k, v in condicion.items():
                    where_clauses.append(f'"{k}" = ?')
                    params.append(v)

                # Prevención de borrado masivo por accidente y aislamiento
                if not is_admin:
                    where_clauses.append(' "_owner_id" = ? ')
                    params.append(user_id)

                if not where_clauses:
                    raise DatabaseExecutionError("No se permite ejecutar ELIMINAR sin condiciones de seguridad.")

                where_sql = " AND ".join(where_clauses)
                sql = f'DELETE FROM "{tabla}" WHERE {where_sql};'
                
                cursor.execute(sql, params)
                self.conn.commit()
                
                return {
                    "action": action, 
                    "tabla": tabla, 
                    "email_body": f"Se han eliminado {cursor.rowcount} registro(s) de la tabla '{tabla}'."
                }

            elif action == "BORRAR_TABLA":
                self._verify_table_ownership(cursor, tabla, user_id, is_admin)
                cursor.execute(f'DROP TABLE "{tabla}";')
                cursor.execute("DELETE FROM _sys_table_owners WHERE table_name = ?", (tabla,))
                self.conn.commit()
                
                return {
                    "action": action, 
                    "tabla": tabla, 
                    "email_body": f"La tabla '{tabla}' y todos sus datos han sido destruidos permanentemente."
                }

            else:
                raise DatabaseExecutionError(f"Acción no soportada en el motor de BD: {action}")

        except sqlite3.Error as e:
            raise DatabaseExecutionError(f"Error de base de datos durante operación {action}: {str(e)}") from e