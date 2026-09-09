import unittest
import sqlite3
from cryptography.fernet import Fernet

from installer import SystemInstaller
from user_manager import UserManager, Role, UnauthorizedError
from registration_service import RegistrationService, EmailSenderInterface, UnauthorizedEmailError

class MockEmailSender(EmailSenderInterface):
    def __init__(self):
        self.sent_emails = []

    def send_email(self, to_address: str, subject: str, body: str) -> bool:
        self.sent_emails.append({
            "to": to_address,
            "subject": subject,
            "body": body
        })
        return True

class TestRegistrationService(unittest.TestCase):
    def setUp(self):
        self.db_conn = sqlite3.connect(":memory:")
        self.admin_email = "admin@system.com"
        
        # Inicialización del esquema
        installer = SystemInstaller(self.db_conn)
        installer.install_system(self.admin_email)

        self.user_manager = UserManager(self.db_conn)
        self.email_sender = MockEmailSender()
        self.registration_service = RegistrationService(self.user_manager, self.email_sender, self.db_conn)
        
        self.test_email = "allowed_user@test.com"
        self.user_manager.add_to_allowlist(self.admin_email, self.test_email)

    def tearDown(self):
        self.db_conn.close()

    def test_process_registration_assigns_table_automatically(self):
        result = self.registration_service.process_registration(self.test_email)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["assigned_table"], "tabla_allowed_user")

        # Verificar inserción automática en user_table_permissions
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT table_name FROM user_table_permissions WHERE email = ?", (self.test_email,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "tabla_allowed_user")

        # Verificar notificación por correo informando la tabla asignada
        sent_mail = self.email_sender.sent_emails[0]
        self.assertIn("tabla_allowed_user", sent_mail["body"])

    def test_process_registration_not_on_allowlist(self):
        unauthorized_email = "not_allowed@test.com"
        with self.assertRaises(UnauthorizedEmailError):
            self.registration_service.process_registration(unauthorized_email)

if __name__ == "__main__":
    unittest.main()