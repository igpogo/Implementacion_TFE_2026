import unittest
import sqlite3
from user_manager import (
    UserManager, 
    Role, 
    UserStatus, 
    UserEncryption, 
    UnauthorizedError, 
    UserNotFoundError
)

class TestUserManager(unittest.TestCase):
    def setUp(self):
        # Base de datos SQLite en memoria para tests aislados
        self.db_conn = sqlite3.connect(":memory:")
        self.manager = UserManager(self.db_conn)
        self.admin_email = "admin@system.com"
        self.user_email = "user@test.com"
        
        # Bootstrap inicial de un Administrador en el sistema
        self.manager.bootstrap_admin(self.admin_email)

    def tearDown(self):
        self.db_conn.close()

    def test_bootstrap_admin_default_encryption(self):
        admin = self.manager.get_user(self.admin_email)
        self.assertEqual(admin["encryption"], UserEncryption.ACTIVE.value)

    def test_add_to_allowlist_by_admin_success(self):
        result = self.manager.add_to_allowlist(self.admin_email, "newuser@test.com")
        self.assertTrue(result)
        self.assertTrue(self.manager.is_on_allowlist("newuser@test.com"))

    def test_add_to_allowlist_unauthorized_fails(self):
        self.manager.add_to_allowlist(self.admin_email, self.user_email)
        self.manager.register_user(self.user_email, Role.USER)
        
        with self.assertRaises(UnauthorizedError):
            self.manager.add_to_allowlist(self.user_email, "hacker@test.com")

    def test_register_user_default_encryption_active(self):
        self.manager.add_to_allowlist(self.admin_email, self.user_email)
        user = self.manager.register_user(self.user_email, Role.USER)
        
        self.assertEqual(user["email"], self.user_email)
        self.assertEqual(user["role"], Role.USER.value)
        self.assertEqual(user["status"], UserStatus.ACTIVE.value)
        self.assertEqual(user["encryption"], UserEncryption.ACTIVE.value)

    def test_register_user_with_custom_encryption(self):
        self.manager.add_to_allowlist(self.admin_email, self.user_email)
        user = self.manager.register_user(
            self.user_email, 
            Role.USER, 
            encryption=UserEncryption.INACTIVE
        )
        
        self.assertEqual(user["encryption"], UserEncryption.INACTIVE.value)

    def test_register_user_not_on_allowlist_fails(self):
        with self.assertRaises(UnauthorizedError):
            self.manager.register_user("unknown@test.com", Role.USER)

    def test_remove_from_allowlist_success(self):
        self.manager.add_to_allowlist(self.admin_email, self.user_email)
        self.assertTrue(self.manager.is_on_allowlist(self.user_email))
        
        self.manager.remove_from_allowlist(self.admin_email, self.user_email)
        self.assertFalse(self.manager.is_on_allowlist(self.user_email))

    def test_update_user_role_success(self):
        self.manager.add_to_allowlist(self.admin_email, self.user_email)
        self.manager.register_user(self.user_email, Role.USER)
        
        updated_user = self.manager.update_user_role(self.admin_email, self.user_email, Role.ADMIN)
        self.assertEqual(updated_user["role"], Role.ADMIN.value)

    def test_update_user_encryption_success(self):
        self.manager.add_to_allowlist(self.admin_email, self.user_email)
        self.manager.register_user(self.user_email, Role.USER)
        
        updated_user = self.manager.update_user_encryption(self.user_email, UserEncryption.INACTIVE)
        self.assertEqual(updated_user["encryption"], UserEncryption.INACTIVE.value)

    def test_get_user_not_found(self):
        with self.assertRaises(UserNotFoundError):
            self.manager.get_user("nonexistent@test.com")

if __name__ == "__main__":
    unittest.main()