import re
from typing import Tuple, Dict, Any, List

class SyntaxValidationError(Exception):
    """Excepción detallada cuando un comando contiene errores sintácticos o está mal formado."""
    pass

class CommandGrammarParser:
    """Parser léxico y validador sintáctico para comandos CRUD en lenguaje estructurado DSL."""

    VALID_ACTIONS = {"CREAR_TABLA", "CREAR", "LEER", "MODIFICAR", "ELIMINAR"}

    def _cast_and_validate_value(self, val_str: str) -> Any:
        """Valida literales de texto, números y booleanos, verificando que no existan comillas sin cerrar."""
        val_str = val_str.strip()

        # Detección de comillas sin cerrar
        starts_with_single = val_str.startswith("'")
        ends_with_single = val_str.endswith("'")
        starts_with_double = val_str.startswith('"')
        ends_with_double = val_str.endswith('"')

        if (starts_with_single and not ends_with_single) or (not starts_with_single and ends_with_single):
            raise SyntaxValidationError(f"Comillas sin cerrar en la cadena: {val_str}")
        if (starts_with_double and not ends_with_double) or (not starts_with_double and ends_with_double):
            raise SyntaxValidationError(f"Comillas sin cerrar en la cadena: {val_str}")

        if (starts_with_single and ends_with_single) or (starts_with_double and ends_with_double):
            return val_str[1:-1]

        # Conversiones numéricas
        try:
            if "." in val_str:
                return float(val_str)
            return int(val_str)
        except ValueError:
            pass

        # Booleanos
        if val_str.upper() == "TRUE":
            return True
        if val_str.upper() == "FALSE":
            return False

        return val_str

    def _split_smart_comma(self, text: str) -> List[str]:
        """Divide cadenas por comas respetando cadenas entre comillas."""
        pattern = r",(?=(?:[^\'\"]*[\'\"][^\'\"]*[\'\"])*[^\'\"]*$)"
        return [part.strip() for part in re.split(pattern, text) if part.strip()]

    def parse(self, command_text: str) -> Tuple[str, Dict[str, Any]]:
        """Analiza sintácticamente el comando y devuelve (acción, datos) o lanza SyntaxValidationError."""
        if not command_text or not command_text.strip():
            raise SyntaxValidationError("El comando está vacío.")

        text = command_text.strip()
        first_word = text.split()[0].upper()

        if first_word not in self.VALID_ACTIONS:
            raise SyntaxValidationError(
                f"Acción desconocida '{first_word}'. Las acciones válidas son: {', '.join(sorted(self.VALID_ACTIONS))}"
            )

        # 1. VALIDADOR / PARSER: CREAR_TABLA
        if first_word == "CREAR_TABLA":
            return self._parse_crear_tabla(text)

        # 2. VALIDADOR / PARSER: CREAR
        elif first_word == "CREAR":
            return self._parse_crear(text)

        # 3. VALIDADOR / PARSER: LEER
        elif first_word == "LEER":
            return self._parse_leer(text)

        # 4. VALIDADOR / PARSER: MODIFICAR
        elif first_word == "MODIFICAR":
            return self._parse_modificar(text)

        # 5. VALIDADOR / PARSER: ELIMINAR
        elif first_word == "ELIMINAR":
            return self._parse_eliminar(text)

        raise SyntaxValidationError("No se pudo procesar el comando.")

    def _parse_crear_tabla(self, text: str) -> Tuple[str, Dict[str, Any]]:
        match_table = re.match(r"^CREAR_TABLA\s+([a-zA-Z0-9_]+)(.*)$", text, re.IGNORECASE)
        if not match_table:
            raise SyntaxValidationError("Sintaxis incorrecta en CREAR_TABLA. Uso: CREAR_TABLA <nombre_tabla> (<col1> <TIPO>, ...)")

        table_name = match_table.group(1)
        rest = match_table.group(2).strip()

        if not rest.startswith("("):
            raise SyntaxValidationError("Sintaxis incorrecta en CREAR_TABLA: debe encerrar las columnas entre paréntesis '()'.")
        if not rest.endswith(")"):
            raise SyntaxValidationError("Sintaxis incorrecta en CREAR_TABLA: Paréntesis sin cerrar al final de las columnas.")

        cols_content = rest[1:-1].strip()
        if not cols_content:
            raise SyntaxValidationError("La lista de columnas no puede estar vacía en CREAR_TABLA.")

        cols_raw = self._split_smart_comma(cols_content)
        
        columns = {}
        for col_def in cols_raw:
            parts = col_def.strip().split()
            if len(parts) < 2:
                raise SyntaxValidationError(f"Definición de columna inválida '{col_def}'. Se requiere '<nombre_columna> <TIPO>'.")
            col_name = parts[0]
            col_type = " ".join(parts[1:]).upper()
            columns[col_name] = col_type

        return "CREAR_TABLA", {"tabla": table_name, "columnas": columns}

    def _parse_crear(self, text: str) -> Tuple[str, Dict[str, Any]]:
        if not re.match(r"^CREAR\s+EN\s+", text, re.IGNORECASE):
            raise SyntaxValidationError("Sintaxis incorrecta en CREAR. Se esperaba 'EN <tabla>'.")
        
        if " SET " not in text.upper():
            raise SyntaxValidationError("Sintaxis incorrecta en CREAR. Se requiere la cláusula 'SET <col1>=<val1>, ...'.")

        match = re.match(r"^CREAR\s+EN\s+([a-zA-Z0-9_]+)\s+SET\s+(.+)$", text, re.IGNORECASE)
        if not match:
            raise SyntaxValidationError("Estructura mal formada en comando CREAR.")

        table_name = match.group(1)
        assigns_str = match.group(2).strip()

        assigns = self._split_smart_comma(assigns_str)
        registro = {}
        for assign in assigns:
            if "=" not in assign:
                raise SyntaxValidationError(f"Asignación inválida '{assign}' en SET. Se esperaba formato 'columna=valor'.")
            k, v = assign.split("=", 1)
            registro[k.strip()] = self._cast_and_validate_value(v)

        return "CREAR", {"tabla": table_name, "registro": registro}

    def _parse_leer(self, text: str) -> Tuple[str, Dict[str, Any]]:
        if not re.match(r"^LEER\s+DE\s+", text, re.IGNORECASE):
            raise SyntaxValidationError("Sintaxis incorrecta en LEER. Se esperaba 'DE <tabla>'.")

        has_where = " WHERE " in text.upper() or text.upper().endswith(" WHERE")
        
        if has_where:
            match = re.match(r"^LEER\s+DE\s+([a-zA-Z0-9_]+)\s+WHERE\s*(.*)$", text, re.IGNORECASE)
            if not match or not match.group(2).strip():
                raise SyntaxValidationError("Cláusula WHERE vacía en comando LEER.")
            table_name = match.group(1)
            where_str = match.group(2).strip()
            if "=" not in where_str:
                raise SyntaxValidationError(f"Filtro WHERE inválido '{where_str}'. Se esperaba 'columna=valor'.")
            k, v = where_str.split("=", 1)
            filtros = {k.strip(): self._cast_and_validate_value(v)}
        else:
            match = re.match(r"^LEER\s+DE\s+([a-zA-Z0-9_]+)$", text, re.IGNORECASE)
            if not match:
                raise SyntaxValidationError("Estructura mal formada en comando LEER.")
            table_name = match.group(1)
            filtros = {}

        return "LEER", {"tabla": table_name, "filtros": filtros}

    def _parse_modificar(self, text: str) -> Tuple[str, Dict[str, Any]]:
        if not re.match(r"^MODIFICAR\s+EN\s+", text, re.IGNORECASE):
            raise SyntaxValidationError("Sintaxis incorrecta en MODIFICAR. Se esperaba 'EN <tabla>'.")

        if " SET " not in text.upper():
            raise SyntaxValidationError("Sintaxis incorrecta en MODIFICAR. Se requiere la cláusula 'SET'.")

        if " WHERE " not in text.upper():
            raise SyntaxValidationError("MODIFICAR requiere una cláusula 'WHERE <col>=<valor>' para evitar modificaciones globales.")

        match = re.match(r"^MODIFICAR\s+EN\s+([a-zA-Z0-9_]+)\s+SET\s+(.+)\s+WHERE\s+(.+)$", text, re.IGNORECASE)
        if not match:
            raise SyntaxValidationError("Estructura mal formada en comando MODIFICAR.")

        table_name = match.group(1)
        assigns_str = match.group(2).strip()
        where_str = match.group(3).strip()

        assigns = self._split_smart_comma(assigns_str)
        valores = {}
        for assign in assigns:
            if "=" not in assign:
                raise SyntaxValidationError(f"Asignación inválida '{assign}' en SET.")
            k, v = assign.split("=", 1)
            valores[k.strip()] = self._cast_and_validate_value(v)

        if "=" not in where_str:
            raise SyntaxValidationError(f"Condición WHERE inválida '{where_str}'.")
        cond_k, cond_v = where_str.split("=", 1)
        condicion = {cond_k.strip(): self._cast_and_validate_value(cond_v)}

        return "MODIFICAR", {"tabla": table_name, "valores": valores, "condicion": condicion}

    def _parse_eliminar(self, text: str) -> Tuple[str, Dict[str, Any]]:
        if not re.match(r"^ELIMINAR\s+DE\s+", text, re.IGNORECASE):
            raise SyntaxValidationError("Sintaxis incorrecta en ELIMINAR. Se esperaba 'DE <tabla>'.")

        if " WHERE " not in text.upper():
            raise SyntaxValidationError("ELIMINAR requiere una cláusula 'WHERE <col>=<valor>' por motivos de seguridad.")

        match = re.match(r"^ELIMINAR\s+DE\s+([a-zA-Z0-9_]+)\s+WHERE\s+(.+)$", text, re.IGNORECASE)
        if not match:
            raise SyntaxValidationError("Estructura mal formada en comando ELIMINAR.")

        table_name = match.group(1)
        where_str = match.group(2).strip()

        if "=" not in where_str:
            raise SyntaxValidationError(f"Condición WHERE inválida '{where_str}'.")
        cond_k, cond_v = where_str.split("=", 1)
        condicion = {cond_k.strip(): self._cast_and_validate_value(cond_v)}

        return "ELIMINAR", {"tabla": table_name, "condicion": condicion}