package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;
import jadex.bridge.fipa.FipaMessage;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Set;
import java.util.stream.Collectors;

public final class LogUtil {
    private static final DateTimeFormatter FMT = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private LogUtil() {
    }

    public static void logMessage(FipaMessage msg, String direction) {
        String sender = shortId(msg.getSender());
        String receivers = shortIds(msg.getReceivers());
        System.out.printf(
                "%s;%s;%s;%s;%s;%s;%s%n",
                sender,
                receivers,
                msg.getPerformative(),
                safe(msg.getReplyWith()),
                safe(msg.getConversationId()),
                direction,
                LocalDateTime.now().format(FMT)
        );
    }

    public static void logInitMessage(String action, String agentName) {
        System.out.printf("init;%s;%s;%s%n", action, agentName, LocalDateTime.now().format(FMT));
    }

    public static void logInfoMessage(String action, String agentName) {
        System.out.printf("info;%s;%s;%s%n", action, agentName, LocalDateTime.now().format(FMT));
    }

    public static String shortId(IComponentIdentifier id) {
        if (id == null || id.getName() == null) {
            return "-";
        }
        return id.getName();
    }

    public static String shortIds(Set<IComponentIdentifier> ids) {
        if (ids == null || ids.isEmpty()) {
            return "-";
        }
        return ids.stream().map(LogUtil::shortId).collect(Collectors.joining(","));
    }

    private static String safe(String value) {
        return value == null ? "-" : value;
    }
}
