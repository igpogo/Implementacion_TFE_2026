import unittest
import sqlite3
import base64
from unittest.mock import MagicMock, patch

from system_orchestrator import SystemOrchestrator
from message_processor import SanitizationError
from command_grammar import SyntaxValidationError
from db_executor import DatabaseExecutionError, SecurityViolationError


class TestE2EPipeline(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.secret_key = "SECRET_KEY_123"
        self.orchestrator = SystemOrchestrator(self.conn, secret_key=self.secret_key)
        self.user_id = "admin"
        self.user_email = "admin@empresa.com"

    def tearDown(self):
        self.conn.close()

    def _encrypt(self, plain_text: str) -> str:
        key_bytes = self.secret_key.encode('utf-8')
        encrypted_chars = bytes([
            ord(c) ^ key_bytes[i % len(key_bytes)] 
            for i, c in enumerate(plain_text)
        ])
        return base64.b64encode(encrypted_chars).decode('utf-8')

    # -------------------------------------------------------------------------
    # 1. Pruebas E2E CRUD Básicos (Flujos Principales)
    # -------------------------------------------------------------------------
    def test_e2e_successful_crud_flow(self):
        cmd1 = "CREAR_TABLA clientes (id INTEGER PRIMARY KEY, nombre TEXT, saldo REAL)"
        payload1 = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd1)}
        res1 = self.orchestrator.process_request(payload1, self.user_email)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["code"], "OK-200")

        cmd2 = "CREAR EN clientes SET id=10, nombre='Carlos Perez', saldo=500.0"
        payload2 = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd2)}
        res2 = self.orchestrator.process_request(payload2, self.user_email)
        self.assertEqual(res2["status"], "SUCCESS")

        cmd3 = "LEER DE clientes WHERE id=10"
        payload3 = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd3)}
        res3 = self.orchestrator.process_request(payload3, self.user_email)
        self.assertEqual(res3["status"], "SUCCESS")
        self.assertEqual(len(res3["data"]), 1)
        self.assertEqual(res3["data"][0]["nombre"], "Carlos Perez")

    def test_e2e_auth_failure(self):
        payload = {"user_id": "USUARIO_DESCONOCIDO", "encrypted_command": self._encrypt("LEER DE clientes")}
        res = self.orchestrator.process_request(payload, self.user_email)
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["code"], "ERR-101")

    def test_e2e_sanitizer_failure(self):
        cmd = "LEER DE clientes; DROP TABLE clientes--"
        payload = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd)}
        res = self.orchestrator.process_request(payload, self.user_email)
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["code"], "ERR-301")

    def test_e2e_syntax_failure(self):
        cmd = "CREAR clientes SET id=1"
        payload = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd)}
        res = self.orchestrator.process_request(payload, self.user_email)
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["code"], "ERR-403")

    def test_e2e_db_failure(self):
        cmd = "CREAR EN tabla_inexistente SET id=1"
        payload = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd)}
        res = self.orchestrator.process_request(payload, self.user_email)
        self.assertEqual(res["status"], "ERROR")
        self.assertEqual(res["code"], "ERR-501")

    # -------------------------------------------------------------------------
    # 2. Cobertura del Destructor (__del__)
    # -------------------------------------------------------------------------
    def test_destructor_cleanup_exceptions(self):
        mock_file_fail = MagicMock()
        mock_file_fail.close.side_effect = Exception("Fallo en cierre de archivo")
        
        mock_handler_fail = MagicMock()
        mock_handler_fail.close.side_effect = Exception("Fallo en cierre de handler")

        self.orchestrator.logger.file = mock_file_fail
        self.orchestrator.logger.handlers = [mock_handler_fail]

        try:
            self.orchestrator.__del__()
        except Exception as e:
            self.fail(f"__del__ no debería propagar excepciones: {e}")

    # -------------------------------------------------------------------------
    # 3. Cobertura de Parseo de Resultados (_parse_query_results) (Líneas 64-67, 96-97, 115-116)
    # -------------------------------------------------------------------------
    def test_parse_query_results_variations_and_exceptions(self):
        self.assertEqual(self.orchestrator._parse_query_results(None), [])
        self.assertEqual(self.orchestrator._parse_query_results([{"a": 1}]), [{"a": 1}])

        # JSONs válidos
        self.assertEqual(self.orchestrator._parse_query_results('[{"a": 1}]'), [{"a": 1}])
        self.assertEqual(self.orchestrator._parse_query_results('Texto previo [{"a": 2}] texto posterior'), [{"a": 2}])

        # Líneas 64-67: Cadena con corchetes pero JSON interno corrupto
        res_bad_brackets = self.orchestrator._parse_query_results("Texto con [ json invalido sin comillas ] aquí")
        self.assertEqual(res_bad_brackets, "Texto con [ json invalido sin comillas ] aquí")

        # Diccionarios estándar
        self.assertEqual(self.orchestrator._parse_query_results({"resultados": [1]}), [1])
        self.assertEqual(self.orchestrator._parse_query_results({"data": [2]}), [2])
        self.assertEqual(self.orchestrator._parse_query_results({"rows": [3]}), [3])
        self.assertEqual(self.orchestrator._parse_query_results({"email_body": 'Resultado: [{"x": 10}]'}), [{"x": 10}])

        # Líneas 96-97: email_body con corchetes pero JSON malformado
        res_invalid_body = self.orchestrator._parse_query_results({"email_body": "Texto con [ JSON invalido ] aquí"})
        self.assertEqual(res_invalid_body, [])

        # Líneas 115-116: Excepción en el segundo json.loads sobre data_output
        res_invalid_str = self.orchestrator._parse_query_results("Texto sin json")
        self.assertEqual(res_invalid_str, "Texto sin json")

        dict_sin_json = {"email_body": "Sin json valido"}
        self.assertEqual(self.orchestrator._parse_query_results(dict_sin_json), dict_sin_json)

    # -------------------------------------------------------------------------
    # 4. Cobertura de _execute_db_command (Línea 56)
    # -------------------------------------------------------------------------
    def test_execute_db_command_raise_last_exc(self):
        # Línea 56: Forzar a que todos los reintentos de acción fallen con una excepción genérica
        with patch.object(self.orchestrator.db_executor, 'execute_parsed_command', side_effect=ValueError("Error no BD")):
            with self.assertRaises(ValueError):
                self.orchestrator._execute_db_command("CREAR", {"tabla": "t"}, self.user_id)

    # -------------------------------------------------------------------------
    # 5. Cobertura de Transacciones y Reintentos en DB (Líneas 184, 191, 195)
    # -------------------------------------------------------------------------
    def test_process_request_transaction_retry_exception_branches(self):
        # Línea 184: tx_manager no tiene método transaction() -> dispara 'raise exc'
        with patch.object(self.orchestrator, '_execute_db_command', side_effect=Exception("Error genérico DB")):
            with patch.object(self.orchestrator, 'tx_manager', None):
                payload = {"user_id": self.user_id, "encrypted_command": self._encrypt("LEER DE clientes")}
                res = self.orchestrator.process_request(payload, self.user_email)
                self.assertEqual(res["code"], "ERR-501")

        # Línea 191: El reintento dentro de la transacción eleva sqlite3.Error
        with patch.object(self.orchestrator, '_execute_db_command') as mock_exec:
            mock_exec.side_effect = [Exception("Primer fallo"), sqlite3.Error("Error SQLite")]
            payload = {"user_id": self.user_id, "encrypted_command": self._encrypt("LEER DE clientes")}
            res = self.orchestrator.process_request(payload, self.user_email)
            self.assertEqual(res["code"], "ERR-501")

        # Línea 195: El reintento dentro de la transacción eleva Exception genérica
        with patch.object(self.orchestrator, '_execute_db_command') as mock_exec:
            mock_exec.side_effect = [Exception("Primer fallo"), RuntimeError("Fallo no previsto")]
            payload = {"user_id": self.user_id, "encrypted_command": self._encrypt("LEER DE clientes")}
            res = self.orchestrator.process_request(payload, self.user_email)
            self.assertEqual(res["code"], "ERR-501")

    # -------------------------------------------------------------------------
    # 6. Cobertura de Commit en SQLite y Auxiliares (Líneas 206-207, 219-220, 226-230)
    # -------------------------------------------------------------------------
    def test_db_commit_and_logging_notifications_exceptions(self):
        # Líneas 206-207: Mock de conexión donde commit() lanza excepción
        mock_conn = MagicMock()
        mock_conn.commit.side_effect = Exception("Fallo en commit SQLite")

        # Líneas 219-220: Logger falla
        # Líneas 226-230: Notifier falla en llamada principal y en fallback
        with patch.object(self.orchestrator, '_execute_db_command', return_value=[{"id": 1}]), \
             patch.object(self.orchestrator.db_executor, 'conn', mock_conn), \
             patch.object(self.orchestrator.logger, 'log_event', side_effect=Exception("Logger fail")), \
             patch.object(self.orchestrator.notifier, 'send_notification', side_effect=Exception("Notifier fail")):

            cmd = "LEER DE clientes"
            payload = {"user_id": self.user_id, "encrypted_command": self._encrypt(cmd)}
            res = self.orchestrator.process_request(payload, self.user_email)

            self.assertEqual(res["status"], "SUCCESS")
            mock_conn.commit.assert_called_once()

    # -------------------------------------------------------------------------
    # 7. Mapeos de Sintaxis Específicos (Líneas 245, 266, 268, 272, 274)
    # -------------------------------------------------------------------------
    def test_syntax_validation_mappings_complete(self):
        mappings = [
            ("Acción desconocida 'COMANDO'", "ERR-401"),      # Línea 266
            ("Comillas sin cerrar en la cadena", "ERR-402"),  # Línea 268
            ("Asignación inválida en SET", "ERR-404"),        # Línea 272
            ("Filtro no válido", "ERR-404"),                  # Línea 272
            ("Falta paréntesis en columnas", "ERR-405"),       # Línea 274
            ("Error en columnas de tabla", "ERR-405"),        # Línea 274
            ("Mensaje de sintaxis no mapeado", "ERR-403")     # Línea 245
        ]

        for msg, expected_code in mappings:
            with patch.object(self.orchestrator.parser, 'parse', side_effect=SyntaxValidationError(msg)):
                payload = {"user_id": self.user_id, "encrypted_command": self._encrypt("DUMMY")}
                res = self.orchestrator.process_request(payload, self.user_email)
                self.assertEqual(res["code"], expected_code)

    # -------------------------------------------------------------------------
    # 8. Manejo de Errores DB Directos y Fallos en Auxiliares de _handle_failure (Líneas 282-283, 289-290, 294-295, 310)
    # -------------------------------------------------------------------------
    def test_handle_failure_full_coverage(self):
        # Líneas 282-283: SecurityViolationError
        with patch.object(self.orchestrator, '_execute_db_command', side_effect=SecurityViolationError("Acceso denegado")):
            payload = {"user_id": self.user_id, "encrypted_command": self._encrypt("LEER DE clientes")}
            res = self.orchestrator.process_request(payload, self.user_email)
            self.assertEqual(res["code"], "ERR-501")

        # Líneas 289-290, 294-295, 310: Excepciones dentro de logger, notifier y ResponseFormatter en _handle_failure
        with patch.object(self.orchestrator.logger, 'log_event', side_effect=Exception("Logger fail")), \
             patch.object(self.orchestrator.notifier, 'send_notification', side_effect=Exception("Notifier fail")), \
             patch('response_formatter.ResponseFormatter.format_error_response', side_effect=Exception("Formatter fail")):

            res = self.orchestrator._handle_failure("ERR-500", self.user_id, self.user_email, "Detalle")
            self.assertEqual(res["status"], "ERROR")
            self.assertEqual(res["code"], "ERR-500")

    # -------------------------------------------------------------------------
    # 9. Cobertura de Casos Borde de Desencriptación y Sanitización
    # -------------------------------------------------------------------------
    def test_decryption_and_sanitization_edge_cases(self):
        # ERR-201: Usuario autenticado pero sin comando encriptado
        res_sin_cmd = self.orchestrator.process_request({"user_id": self.user_id}, self.user_email)
        self.assertEqual(res_sin_cmd["code"], "ERR-201")

        # ERR-101: Payload sin user_id o no diccionario
        res_no_user = self.orchestrator.process_request({}, self.user_email)
        self.assertEqual(res_no_user["code"], "ERR-101")

        res_no_dict = self.orchestrator.process_request("cadena_invalida", self.user_email)
        self.assertEqual(res_no_dict["code"], "ERR-101")

        # ERR-202: Encrypted command corrupto
        payload_corrupto = {"user_id": self.user_id, "encrypted_command": "NOT_BASE64!!!"}
        res_corrupto = self.orchestrator.process_request(payload_corrupto, self.user_email)
        self.assertEqual(res_corrupto["code"], "ERR-202")

        # ERR-302: Byte nulo en sanitización
        with patch.object(self.orchestrator.sanitizer, 'sanitize', side_effect=SanitizationError("Contiene \\x00")):
            payload = {"user_id": self.user_id, "encrypted_command": self._encrypt("LEER DE t")}
            res = self.orchestrator.process_request(payload, self.user_email)
            self.assertEqual(res["code"], "ERR-302")


if __name__ == "__main__":
    unittest.main()