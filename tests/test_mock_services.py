import unittest
from mock_services import EmailService, DatabaseService, NotificationService, APIService, MockServiceError
from service_registry import ServiceRegistry


class TestMockServices(unittest.TestCase):

    def test_email_service_success_and_failure(self):
        email_svc = EmailService()
        email_svc.send_email("finance@company.com", "Invoice Alert", "Amount > 50000")
        self.assertEqual(len(email_svc.sent_messages), 1)

        email_svc.set_fail_count(1)
        with self.assertRaises(MockServiceError):
            email_svc.send_email("finance@company.com", "Invoice Alert", "Amount > 50000")

    def test_database_service_record(self):
        db_svc = DatabaseService()
        db_svc.save_record("invoice", "invoices_table", {"amount": 50000})
        self.assertEqual(len(db_svc.saved_records), 1)
        self.assertEqual(db_svc.saved_records[0].entity, "invoice")

    def test_notification_service(self):
        notif_svc = NotificationService()
        notif_svc.notify("manager", "High priority ticket")
        self.assertEqual(len(notif_svc.notifications), 1)

    def test_api_service(self):
        api_svc = APIService()
        res = api_svc.call_api("/v1/payments", "POST", {"amount": 500})
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(api_svc.requests), 1)

    def test_service_registry_dispatch(self):
        reg = ServiceRegistry()
        reg.dispatch_call("notify_finance", {"target": "finance"})
        reg.dispatch_call("save_to_database", {"entity": "order", "destination": "orders_db"})
        summary = reg.get_activity_summary()

        self.assertEqual(summary["notifications_sent"], 1)
        self.assertEqual(summary["records_saved"], 1)


if __name__ == '__main__':
    unittest.main()
