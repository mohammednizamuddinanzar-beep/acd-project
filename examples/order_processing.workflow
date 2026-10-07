WORKFLOW OrderProcessing {
    ON order.created

    VALIDATE order
    EXTRACT amount FROM order
    EXTRACT customer FROM order
    EXTRACT order_id FROM order

    IF amount > 10000 {
        NOTIFY manager
    }

    CALL process_order
    SAVE order TO database
    NOTIFY customer
}
