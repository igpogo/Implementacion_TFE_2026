import sqlite3
from contextlib import contextmanager
from db_executor import DatabaseExecutionError

class TransactionManager:
    """Gestor de transacciones con control de Commit y Rollback automático."""

    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection

    @contextmanager
    def transaction(self):
        """Context Manager para envolver ejecuciones dentro de una transacción segura."""
        try:
            yield
            self.conn.commit()
        except sqlite3.Error as db_err:
            self.conn.rollback()
            raise DatabaseExecutionError(f"Error en la transacción DB: {str(db_err)}")
        except Exception as ex:
            self.conn.rollback()
            raise ex