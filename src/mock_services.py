"""
============================================================
  Business Workflow DSL – Mock Services Layer
  Provides deterministic mock implementations of external services:
    - EmailService
    - DatabaseService
    - NotificationService
    - APIService
  Supports failure simulation for testing RETRY and error recovery.
============================================================
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class EmailMessage:
    recipient: str
    subject: str
    body: str
    timestamp: float = 0.0


@dataclass
class DatabaseRecord:
    entity: str
    destination: str
    data: Dict[str, Any]
    timestamp: float = 0.0


@dataclass
class Notification:
    target: str
    message: str
    timestamp: float = 0.0


@dataclass
class APIRequest:
    endpoint: str
    method: str
    payload: Dict[str, Any]
    timestamp: float = 0.0


class MockServiceError(Exception):
    def __init__(self, service_name: str, message: str):
        super().__init__(f"[{service_name} Error] {message}")
        self.service_name = service_name
        self.message = message


class EmailService:
    def __init__(self):
        self.sent_messages: List[EmailMessage] = []
        self.fail_count: int = 0  # number of remaining intentional failures

    def set_fail_count(self, count: int):
        self.fail_count = count

    def send_email(self, recipient: str, subject: str = "Notification", body: str = "", timestamp: float = 0.0) -> bool:
        if self.fail_count > 0:
            self.fail_count -= 1
            raise MockServiceError("EmailService", "Simulated email delivery network failure")
        msg = EmailMessage(recipient=recipient, subject=subject, body=body, timestamp=timestamp)
        self.sent_messages.append(msg)
        return True


class DatabaseService:
    def __init__(self):
        self.saved_records: List[DatabaseRecord] = []
        self.fail_count: int = 0

    def set_fail_count(self, count: int):
        self.fail_count = count

    def save_record(self, entity: str, destination: str, data: Optional[Dict[str, Any]] = None, timestamp: float = 0.0) -> bool:
        if self.fail_count > 0:
            self.fail_count -= 1
            raise MockServiceError("DatabaseService", "Simulated database connection failure")
        record = DatabaseRecord(entity=entity, destination=destination, data=data or {}, timestamp=timestamp)
        self.saved_records.append(record)
        return True


class NotificationService:
    def __init__(self):
        self.notifications: List[Notification] = []
        self.fail_count: int = 0

    def set_fail_count(self, count: int):
        self.fail_count = count

    def notify(self, target: str, message: str = "Alert triggered", timestamp: float = 0.0) -> bool:
        if self.fail_count > 0:
            self.fail_count -= 1
            raise MockServiceError("NotificationService", "Simulated notification channel outage")
        notif = Notification(target=target, message=message, timestamp=timestamp)
        self.notifications.append(notif)
        return True


class APIService:
    def __init__(self):
        self.requests: List[APIRequest] = []
        self.fail_count: int = 0

    def set_fail_count(self, count: int):
        self.fail_count = count

    def call_api(self, endpoint: str, method: str = "POST", payload: Optional[Dict[str, Any]] = None, timestamp: float = 0.0) -> Dict[str, Any]:
        if self.fail_count > 0:
            self.fail_count -= 1
            raise MockServiceError("APIService", "Simulated API HTTP 503 Service Unavailable")
        req = APIRequest(endpoint=endpoint, method=method, payload=payload or {}, timestamp=timestamp)
        self.requests.append(req)
        return {"status": "SUCCESS", "code": 200, "endpoint": endpoint}
