import sys
import unittest

# Importación de los módulos de pruebas unitarias individuales
from test_system_config import TestSystemConfigManager
from test_batch_notifier import TestBatchResponseManager
from test_audit_logger import TestAuditLogger
from test_db_executor import TestDataFormatter, TestDatabaseExecutor
from test_command_grammar import TestCommandGrammarParser
from test_mail_ingestion_service import TestMailIngestionService
from test_main_daemon import TestMainDaemon
from test_system_orchestrator import TestE2EPipeline
from test_message_processor import TestAuthenticator, TestDecryptor, TestSanitizer


def run_unit_tests():
    """Compila y ejecuta la suite integral de pruebas unitarias."""
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    # Añadir baterías de pruebas utilizando TestLoader
    test_suite.addTest(loader.loadTestsFromTestCase(TestSystemConfigManager))
    test_suite.addTest(loader.loadTestsFromTestCase(TestBatchResponseManager))
    test_suite.addTest(loader.loadTestsFromTestCase(TestCommandGrammarParser))
    test_suite.addTest(loader.loadTestsFromTestCase(TestAuditLogger))
    test_suite.addTest(loader.loadTestsFromTestCase(TestDataFormatter))
    test_suite.addTest(loader.loadTestsFromTestCase(TestDatabaseExecutor))
    test_suite.addTest(loader.loadTestsFromTestCase(TestE2EPipeline))
    test_suite.addTest(loader.loadTestsFromTestCase(TestMailIngestionService))
    test_suite.addTest(loader.loadTestsFromTestCase(TestMainDaemon))
    test_suite.addTest(loader.loadTestsFromTestCase(TestAuthenticator))
    test_suite.addTest(loader.loadTestsFromTestCase(TestDecryptor))
    test_suite.addTest(loader.loadTestsFromTestCase(TestSanitizer))
    
    print("Iniciando ejecución de Suite Integral de Pruebas Unitarias...\n")
    
    # Ejecutor con nivel de detalle 2 para mayor visibilidad en consola
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Retornar código de salida válido para pipelines de CI/CD
    sys.exit(not result.wasSuccessful())


if __name__ == '__main__':
    run_unit_tests()