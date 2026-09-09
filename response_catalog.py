from typing import Dict, Any

CATALOGO_RESPUESTAS: Dict[str, Dict[str, str]] = {
    "OK-200": {
        "fase": "Ejecución",
        "tipo": "Éxito",
        "log_template": "Comando parseado y procesado exitosamente. Acción: {action} en tabla {tabla}.",
        "user_message": "Operación Exitosa: El comando fue procesado correctamente por el sistema."
    },
    "ERR-101": {
        "fase": "Autenticación",
        "tipo": "Fallo",
        "log_template": "Usuario no encontrado, no autorizado o ID de usuario nulo.",
        "user_message": "Error de Autenticación: Las credenciales del remitente no están registradas o no son válidas."
    },
    "ERR-201": {
        "fase": "Desencriptación",
        "tipo": "Fallo",
        "log_template": "Payload encriptado ausente o vacío en la solicitud.",
        "user_message": "Error de Formato: No se encontró el contenido encriptado en el mensaje."
    },
    "ERR-202": {
        "fase": "Desencriptación",
        "tipo": "Fallo",
        "log_template": "Error en algoritmo de desencriptación / Clave incorrecta / Payload corrupto: {detail}",
        "user_message": "Error de Desencriptación: No fue posible desencriptar el mensaje enviado. Verifique el formato de cifrado."
    },
    "ERR-301": {
        "fase": "Sanitización",
        "tipo": "Fallo",
        "log_template": "Detección de patrones prohibidos / Intentos de inyección: {detail}",
        "user_message": "Error de Seguridad: El mensaje contiene caracteres o patrones de texto no permitidos."
    },
    "ERR-302": {
        "fase": "Sanitización",
        "tipo": "Fallo",
        "log_template": "Caracteres nulos \\x00 o caracteres de control no imprimibles detectados.",
        "user_message": "Error de Formato: El contenido contiene caracteres no válidos o corruptos."
    },
    "ERR-401": {
        "fase": "Sintaxis",
        "tipo": "Fallo",
        "log_template": "Acción no reconocida o no soportada en el DSL.",
        "user_message": "Error Sintáctico: La acción o comando solicitado no existe o no es reconocido."
    },
    "ERR-402": {
        "fase": "Sintaxis",
        "tipo": "Fallo",
        "log_template": "Comillas simples o dobles sin cerrar en valores de tipo texto.",
        "user_message": "Error Sintáctico: El comando contiene comillas o cadenas de texto sin cerrar correctamente."
    },
    "ERR-403": {
        "fase": "Sintaxis",
        "tipo": "Fallo",
        "log_template": "Falta de cláusulas requeridas (EN, DE, SET, WHERE). Detalle: {detail}",
        "user_message": "Error Sintáctico: Faltan palabras clave requeridas en la estructura del comando (ej: cláusula obligatoria ausente)."
    },
    "ERR-404": {
        "fase": "Sintaxis",
        "tipo": "Fallo",
        "log_template": "Formato de asignación o filtro inválido: {detail}",
        "user_message": "Error Sintáctico: Una o más asignaciones de variables no cumplen con el formato requerido."
    },
    "ERR-405": {
        "fase": "Sintaxis",
        "tipo": "Fallo",
        "log_template": "Error de paréntesis en CREAR_TABLA (ausentes o desbalanceados).",
        "user_message": "Error Sintáctico: La definición de la tabla no encierra correctamente las columnas entre paréntesis."
    },
    "ERR-500": {
        "fase": "Sistema",
        "tipo": "Fallo",
        "log_template": "Excepción no controlada durante el procesamiento interno: {detail}",
        "user_message": "Error del Sistema: Ocurrió un fallo interno no esperado durante el procesamiento de la solicitud."
    },
    "ERR-501": {
        "fase": "Base de datos",
        "tipo": "Fallo",
        "log_template": "Excepción al ejecutar la petición del usuario sobre la base de datos: {detail}",
        "user_message": "Error en la Base de Datos: Ocurrió un fallo no esperado durante el procesamiento de la solicitud."
    }
}