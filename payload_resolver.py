from typing import Tuple, Dict, Any, Union
from command_grammar import CommandGrammarParser, GrammarParseError

class PayloadFormatError(Exception):
    """Excepción lanzada cuando la estructura o el formato del payload es inválido."""
    pass

class PayloadResolver:
    """Interpreta el contenido del mensaje (diccionario o texto plano).
    Si 'format_type' no está presente o se recibe texto plano, asume Gramática de Comandos.
    """

    def __init__(self, grammar_parser: CommandGrammarParser = None):
        self.grammar_parser = grammar_parser or CommandGrammarParser()

    def resolve(self, untrusted_payload: Union[Dict[str, Any], str]) -> Tuple[str, Dict[str, Any]]:
        # CASO 1: El payload es una cadena directa en texto plano
        if isinstance(untrusted_payload, str):
            try:
                return self.grammar_parser.parse(untrusted_payload)
            except GrammarParseError as e:
                raise PayloadFormatError(f"Error al interpretar texto plano mediante gramática: {e}")

        # CASO 2: El payload es un diccionario JSON
        if isinstance(untrusted_payload, dict):
            format_type = untrusted_payload.get("format_type")

            # Si el format_type es explicitamente 'json'
            if format_type == "json":
                action = untrusted_payload.get("action")
                data = untrusted_payload.get("data")
                if not action or data is None:
                    raise PayloadFormatError("Payload JSON incompleto: requiere 'action' y 'data'.")
                return action, data

            # Si format_type es 'grammar' O SI NO ESTÁ PRESENTE (Asunción por defecto)
            else:
                command = untrusted_payload.get("command")
                if command:
                    try:
                        return self.grammar_parser.parse(command)
                    except GrammarParseError as e:
                        raise PayloadFormatError(f"Error de sintaxis en comando de gramática: {e}")
                else:
                    raise PayloadFormatError(
                        "Payload sin 'format_type' asumido como gramática, pero no contiene el campo 'command'."
                    )

        raise PayloadFormatError("El payload debe ser una cadena de texto o un objeto JSON/Diccionario.")