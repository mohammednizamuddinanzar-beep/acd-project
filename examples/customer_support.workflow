WORKFLOW CustomerSupport {

    ON ticket.created

    EXTRACT priority FROM ticket

    IF priority == "HIGH" {

        NOTIFY manager

    }

    SAVE ticket TO database
}
