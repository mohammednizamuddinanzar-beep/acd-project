WORKFLOW InvoiceProcessing {
    ON email.received

    EXTRACT amount FROM email
    EXTRACT vendor FROM email
    EXTRACT invoice_id FROM email

    IF amount > 50000 {
        NOTIFY finance
        NOTIFY manager
    }

    CALL notify_erp
    SAVE invoice TO database
    NOTIFY vendor
}
