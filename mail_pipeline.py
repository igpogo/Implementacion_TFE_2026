import sqlite3
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from cryptography.fernet import Fernet

from user_manager import UserManager
from payload_resolver import PayloadResolver, PayloadFormatError

logger = logging.getLogger(__name__)

@dataclass
class GmailMessage:
    id: str
    sender: str
    raw_body: Dict[str, Any]

class Step5ProcessorInterface(ABC):
    @abstractmethod
    def process_ordered_message(self, decrypted_msg: Dict[str, Any]) -> Dict[str, Any]:
        pass

class DefaultStep5Processor(Step5ProcessorInterface):
    def __init__(self, resolver: PayloadResolver = None):
        self.resolver = resolver or PayloadResolver()

    def process_ordered_message(self, decrypted_msg: Dict[str, Any]) -> Dict[str, Any]:
        sender = decrypted_msg["sender"]
        msg_id = decrypted_msg["msg_id"]
        untrusted_payload = decrypted_msg["untrusted_payload"]

        try:
            action, data = self.resolver.resolve(untrusted_payload)
            return {
                "to": sender,
                "subject": f"Re: Petición {msg_id} - Procesada",
                "plain_body": f"OK: Acción '{action}' procesada correctamente.",
                "encrypted_body": "RESPUESTA_PROCESADA"
            }
        except PayloadFormatError as e:
            return {
                "to": sender,
                "subject": f"Re: Petición {msg_id} - Error Formato",
                "plain_body": f"ERROR: {e}",
                "encrypted_body": None
            }

class MailPipelineEngine:
    """Pipeline que soporta mensajes cifrados y en texto plano/sin cifrar."""

    def __init__(self, db_connection: sqlite3.Connection, step5_processor: Step5ProcessorInterface = None):
        self.conn = db_connection
        self.user_manager = UserManager(db_connection)
        self.step5_processor = step5_processor or DefaultStep5Processor()

    @staticmethod
    def parse_timestamp_key(ts_str: str) -> Tuple[datetime, int]:
        try:
            parts = ts_str.split('-')
            date_obj = datetime.strptime(f"{parts[0]}-{parts[1]}-{parts[2]}", "%Y-%m-%d")
            seconds = int(parts[3])
            return (date_obj, seconds)
        except Exception as e:
            logger.error(f"Error parseando timestamp '{ts_str}': {e}")
            return (datetime.min, 0)

    def process_inbox_batch(self, downloaded_messages: List[GmailMessage]) -> List[Dict[str, Any]]:
        all_responses: List[Dict[str, Any]] = []

        allowed_messages: List[GmailMessage] = []
        for msg in downloaded_messages:
            if not self.user_manager.is_allowed(msg.sender):
                all_responses.append({
                    "to": msg.sender,
                    "subject": f"Re: Petición {msg.id} - Rechazada",
                    "plain_body": "ERROR: Usuario NO PERMITIDO o inactivo.",
                    "encrypted_body": None
                })
            else:
                allowed_messages.append(msg)

        decrypted_batch: List[Dict[str, Any]] = []
        for msg in allowed_messages:
            sender = msg.sender
            raw_payload = msg.raw_body.get("payload")
            is_encryption_active = self.user_manager.is_encryption_enabled(sender)

            payload_data = None

            if is_encryption_active:
                user_key = self.user_manager.get_user_key(sender)
                if not user_key:
                    all_responses.append({
                        "to": sender,
                        "subject": f"Re: Petición {msg.id} - Error",
                        "plain_body": "ERROR: Clave de usuario no encontrada.",
                        "encrypted_body": None
                    })
                    continue

                try:
                    fernet = Fernet(user_key.encode('utf-8'))
                    decrypted_bytes = fernet.decrypt(raw_payload.encode('utf-8'))
                    payload_data = json.loads(decrypted_bytes.decode('utf-8'))
                except Exception as e:
                    all_responses.append({
                        "to": sender,
                        "subject": f"Re: Petición {msg.id} - Error Criptográfico",
                        "plain_body": "ERROR: No se pudo desencriptar el mensaje.",
                        "encrypted_body": None
                    })
                    continue
            else:
                # El usuario tiene desactivada la encriptación: procesar directo
                if isinstance(raw_payload, str):
                    try:
                        payload_data = json.loads(raw_payload)
                    except json.JSONDecodeError:
                        payload_data = raw_payload  # Texto plano directo (Gramática)
                else:
                    payload_data = raw_payload

            decrypted_batch.append({
                "msg_id": msg.id,
                "sender": sender,
                "timestamp": msg.raw_body.get("timestamp", "1970-01-01-00000"),
                "untrusted_payload": payload_data
            })

        grouped_by_user: Dict[str, List[Dict[str, Any]]] = {}
        for item in decrypted_batch:
            grouped_by_user.setdefault(item["sender"], []).append(item)

        ordered_queue: List[Dict[str, Any]] = []
        for sender, user_msgs in grouped_by_user.items():
            if len(user_msgs) > 1:
                user_msgs.sort(key=lambda m: self.parse_timestamp_key(m["timestamp"]))
            ordered_queue.extend(user_msgs)

        for item in ordered_queue:
            response = self.step5_processor.process_ordered_message(item)
            all_responses.append(response)

        return all_responses