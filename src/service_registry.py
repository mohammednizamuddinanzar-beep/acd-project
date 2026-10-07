"""
============================================================
  Business Workflow DSL – Service Registry
  Central dispatch registry connecting workflow calls to mock services.
============================================================
"""

from typing import Dict, Any, Optional
from mock_services import EmailService, DatabaseService, NotificationService, APIService, MockServiceError


class ServiceRegistry:
    def __init__(self):
        self.email_service = EmailService()
        self.db_service = DatabaseService()
        self.notification_service = NotificationService()
        self.api_service = APIService()

    def set_failure_simulation(self, service_name: str, count: int):
        s_name = service_name.lower()
        if "email" in s_name:
            self.email_service.set_fail_count(count)
        elif "db" in s_name or "database" in s_name:
            self.db_service.set_fail_count(count)
        elif "notif" in s_name:
            self.notification_service.set_fail_count(count)
        elif "api" in s_name:
            self.api_service.set_fail_count(count)

    def dispatch_call(self, service_or_function: str, args: Optional[Dict[str, Any]] = None, timestamp: float = 0.0) -> Any:
        args = args or {}
        name = service_or_function.lower()

        if "email" in name or name == "send_email":
            recipient = args.get("recipient", args.get("target", "user@example.com"))
            subject = args.get("subject", "Workflow Notification")
            body = args.get("body", "Notification body content")
            return self.email_service.send_email(recipient, subject, body, timestamp=timestamp)

        elif "save" in name or "db" in name or name == "save_to_database":
            entity = args.get("entity", "record")
            dest = args.get("destination", args.get("dest", "database"))
            return self.db_service.save_record(entity, dest, data=args, timestamp=timestamp)

        elif "notify" in name or name == "notify_finance" or name == "notify_manager":
            target = args.get("target", service_or_function.replace("notify_", ""))
            message = args.get("message", f"Notification to {target}")
            return self.notification_service.notify(target, message=message, timestamp=timestamp)

        elif "api" in name or name == "api_request":
            endpoint = args.get("endpoint", service_or_function)
            method = args.get("method", "POST")
            return self.api_service.call_api(endpoint, method, payload=args, timestamp=timestamp)

        # Generic default mock handler
        return {"service": service_or_function, "status": "COMPLETED", "timestamp": timestamp}

    def get_activity_summary(self) -> Dict[str, Any]:
        return {
            "emails_sent": len(self.email_service.sent_messages),
            "records_saved": len(self.db_service.saved_records),
            "notifications_sent": len(self.notification_service.notifications),
            "api_calls_made": len(self.api_service.requests),
            "details": {
                "emails": [vars(m) for m in self.email_service.sent_messages],
                "database": [vars(r) for r in self.db_service.saved_records],
                "notifications": [vars(n) for n in self.notification_service.notifications],
                "api": [vars(a) for a in self.api_service.requests],
            }
        }
