import imaplib
import email
import json
from email.message import Message
from typing import List, Dict, Any, Tuple
from system_orchestrator import SystemOrchestrator

class MailIngestionError(Exception):
    pass

class MailReaderService:
    """
    Módulo encargado de conectarse al servidor de correo mediante IMAP,
    descargar los mensajes no leídos y extraer los payloads para el Orquestador.
    """

    def __init__(self, imap_server: str, email_account: str, password: str, port: int = 993):
        self.imap_server = imap_server
        self.email_account = email_account
        self.password = password
        self.port = port
        self.mail_conn = None

    def connect(self):
        """Establece conexión segura con el servidor IMAP."""
        try:
            self.mail_conn = imaplib.IMAP4_SSL(self.imap_server, self.port)
            self.mail_conn.login(self.email_account, self.password)
        except imaplib.IMAP4.error as e:
            raise MailIngestionError(f"Error de autenticación IMAP: {e}")
        except Exception as e:
            raise MailIngestionError(f"Error al conectar con el servidor de correo: {e}")

    def disconnect(self):
        """Cierra la conexión con el servidor."""
        if self.mail_conn:
            try:
                self.mail_conn.close()
                self.mail_conn.logout()
            except:
                pass

    def fetch_unread_messages(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Busca correos no leídos, extrae el remitente y el payload JSON del cuerpo.
        Retorna una lista de tuplas: (email_remitente, payload_json)
        """
        if not self.mail_conn:
            raise MailIngestionError("No hay conexión activa con el servidor IMAP.")

        self.mail_conn.select("inbox")
        
        # Buscar correos no leídos
        status, messages = self.mail_conn.search(None, 'UNSEEN')
        if status != "OK":
            return []

        email_ids = messages[0].split()
        parsed_requests = []

        for e_id in email_ids:
            status, msg_data = self.mail_conn.fetch(e_id, '(RFC822)')
            if status == "OK":
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        sender = email.utils.parseaddr(msg.get("From"))[1]
                        body = self._extract_body(msg)
                        
                        try:
                            # Se asume que la app del cliente envía un JSON puro en el cuerpo del correo
                            payload = json.loads(body)
                            parsed_requests.append((sender, payload))
                        except json.JSONDecodeError:
                            print(f"[!] Ignorando correo de {sender}: El cuerpo no es un JSON válido.")
                            # Aquí se podría invocar al NotificationService para avisarle al usuario del error de formato

        return parsed_requests

    def _extract_body(self, msg: Message) -> str:
        """Extrae el texto plano del cuerpo del mensaje, manejando correos multipart."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition'))

                # Solo nos interesa el texto plano
                if content_type == 'text/plain' and 'attachment' not in disposition:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8')
                    except UnicodeDecodeError:
                        body = part.get_payload(decode=True).decode('latin-1')
                    break
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8')
            except UnicodeDecodeError:
                body = msg.get_payload(decode=True).decode('latin-1')
                
        return body.strip()