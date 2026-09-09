import unittest
from command_grammar import CommandGrammarParser, SyntaxValidationError

class TestSyntaxValidatorAndMalformedParser(unittest.TestCase):
    def setUp(self):
        self.parser = CommandGrammarParser()

    # --- CASOS DE COMANDOS VACÍOS O DESCONOCIDOS ---
    def test_empty_or_whitespace_command(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("   ")
        self.assertIn("El comando está vacío", str(ctx.exception))

    def test_unknown_action_keyword(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("DESPACHAR EN pedidos SET id=1")
        self.assertIn("Acción desconocida 'DESPACHAR'", str(ctx.exception))

    # --- ERRORES EN CREAR_TABLA ---
    def test_crear_tabla_missing_parentheses(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR_TABLA usuarios id INTEGER, nombre TEXT")
        self.assertIn("debe encerrar las columnas entre paréntesis", str(ctx.exception))

    def test_crear_tabla_unclosed_parenthesis(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR_TABLA usuarios (id INTEGER, nombre TEXT")
        self.assertIn("Paréntesis sin cerrar", str(ctx.exception))

    def test_crear_tabla_empty_columns(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR_TABLA usuarios ()")
        self.assertIn("La lista de columnas no puede estar vacía", str(ctx.exception))

    def test_crear_tabla_invalid_column_definition(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR_TABLA usuarios (id, nombre TEXT)")
        self.assertIn("Definición de columna inválida 'id'", str(ctx.exception))

    # --- ERRORES EN CREAR ---
    def test_crear_missing_en(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR ventas SET total=100")
        self.assertIn("Sintaxis incorrecta en CREAR. Se esperaba 'EN <tabla>'", str(ctx.exception))

    def test_crear_missing_set(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR EN ventas total=100")
        self.assertIn("Se requiere la cláusula 'SET'", str(ctx.exception))

    def test_crear_malformed_assignment(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR EN ventas SET total")
        self.assertIn("Asignación inválida 'total'", str(ctx.exception))

    # --- ERRORES EN LEER ---
    def test_leer_missing_de(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("LEER ventas")
        self.assertIn("Sintaxis incorrecta en LEER. Se esperaba 'DE <tabla>'", str(ctx.exception))

    def test_leer_empty_where_clause(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("LEER DE ventas WHERE")
        self.assertIn("Cláusula WHERE vacía", str(ctx.exception))

    # --- ERRORES EN MODIFICAR ---
    def test_modificar_missing_where(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("MODIFICAR EN clientes SET estado='activo'")
        self.assertIn("MODIFICAR requiere una cláusula 'WHERE'", str(ctx.exception))

    def test_modificar_missing_set(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("MODIFICAR EN clientes estado='activo' WHERE id=1")
        self.assertIn("Se requiere la cláusula 'SET'", str(ctx.exception))

    # --- ERRORES EN ELIMINAR ---
    def test_eliminar_missing_where(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("ELIMINAR DE clientes")
        self.assertIn("ELIMINAR requiere una cláusula 'WHERE'", str(ctx.exception))

    # --- ERRORES DE CADENAS SIN CERRAR ---
    def test_unclosed_string_quote(self):
        with self.assertRaises(SyntaxValidationError) as ctx:
            self.parser.parse("CREAR EN clientes SET nombre='Juan Perez")
        self.assertIn("Comillas sin cerrar en la cadena", str(ctx.exception))

    # --- COMANDOS VÁLIDOS ---
    def test_valid_commands_parse_successfully(self):
        action, data = self.parser.parse("CREAR EN productos SET nombre='Silla Ergonomica', precio=120.50, stock=10")
        self.assertEqual(action, "CREAR")
        self.assertEqual(data["tabla"], "productos")
        self.assertEqual(data["registro"], {"nombre": "Silla Ergonomica", "precio": 120.50, "stock": 10})

if __name__ == "__main__":
    unittest.main()