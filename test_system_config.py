import unittest
import sqlite3
from system_config import SystemConfigManager

class TestSystemConfigManager(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.config_manager = SystemConfigManager(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_default_compile_responses_is_false(self):
        # Por defecto, la compilación de respuestas debe estar desactivada
        self.assertFalse(self.config_manager.get_compile_responses_enabled())

    def test_admin_can_toggle_compile_responses(self):
        # El administrador activa la compilación
        self.config_manager.set_compile_responses_enabled(True)
        self.assertTrue(self.config_manager.get_compile_responses_enabled())

        # El administrador desactiva la compilación
        self.config_manager.set_compile_responses_enabled(False)
        self.assertFalse(self.config_manager.get_compile_responses_enabled())

if __name__ == "__main__":
    unittest.main()