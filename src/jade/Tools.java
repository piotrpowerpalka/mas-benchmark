


import jade.core.AID;
import jade.lang.acl.ACLMessage;

import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ThreadLocalRandom;

public final class Tools {
    private Tools() {}

    private static final char[] ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".toCharArray();
    private static final DateTimeFormatter TS = DateTimeFormatter.ISO_OFFSET_DATE_TIME;

    public static String nowTs() {
        return OffsetDateTime.now().format(TS);
    }

    public static String randomContent(int size) {
        if (size <= 0) return "";
        var r = ThreadLocalRandom.current();
        var sb = new StringBuilder(size);
        for (int i = 0; i < size; i++) sb.append(ALNUM[r.nextInt(ALNUM.length)]);
        return sb.toString();
    }

    public static String safeName(AID aid) {
        if (aid == null) return "null";
        // getLocalName() bywa wygodniejsze, ale tu zachowujemy pełniejszą postać gdyby zaszła potrzeba.
        return aid.getLocalName();
    }

    /**
     * Log w formacie analogicznym do Python:
     * sender;to;performative;reply_with;conversation_id;{S|R};timestamp
     */
    public static void logMessage(ACLMessage msg, String direction) {
        String sender = safeName(msg.getSender());
        String to = safeName((AID)msg.getAllReceiver().next());
        String perf = ACLMessage.getPerformative(msg.getPerformative());
        String replyWith = msg.getReplyWith();
        String convId = msg.getConversationId();
        System.out.printf("%s;%s;%s;%s;%s;%s;%s%n",
                sender, to, perf, replyWith, convId, direction, nowTs());
    }

    public static void logInitMessage(String state, String agentName) {
        System.out.printf("init;%s;%s;%s%n", state, agentName, nowTs());
    }
}
