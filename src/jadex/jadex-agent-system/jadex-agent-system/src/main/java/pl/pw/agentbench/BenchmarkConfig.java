package pl.pw.agentbench;

import java.util.HashMap;
import java.util.Map;

public final class BenchmarkConfig {
    public static int numAgents = 10;
    public static int groupSize = 3;
    public static String communicationType = "inform";
    public static int contentSize = 1024;
    public static int repetitionsNum = 10;
    public static boolean startInitAgent = true;
    public static long seed = 213742189290L;
    public static boolean gui = false;

    private BenchmarkConfig() {
    }

    public static void fromArgs(String[] args) {
        Map<String, String> parsed = parseArgs(args);

        numAgents = intArg(parsed, "numagents", numAgents);
        groupSize = intArg(parsed, "groupsize", groupSize);
        communicationType = parsed.getOrDefault("communication-type", communicationType).toLowerCase();
        contentSize = intArg(parsed, "content-size", contentSize);
        repetitionsNum = intArg(parsed, "repetitions-num", repetitionsNum);
        startInitAgent = intArg(parsed, "initag", startInitAgent ? 1 : 0) == 1;
        seed = longArg(parsed, "seed", seed);
        gui = intArg(parsed, "gui", gui ? 1 : 0) == 1;
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> values = new HashMap<>();
        for (String arg : args) {
            if (!arg.startsWith("--")) {
                continue;
            }
            int idx = arg.indexOf('=');
            if (idx <= 2) {
                continue;
            }
            String key = arg.substring(2, idx);
            String value = arg.substring(idx + 1);
            values.put(key, value);
        }
        return values;
    }

    private static int intArg(Map<String, String> parsed, String key, int defaultValue) {
        try {
            return Integer.parseInt(parsed.getOrDefault(key, Integer.toString(defaultValue)));
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    private static long longArg(Map<String, String> parsed, String key, long defaultValue) {
        try {
            return Long.parseLong(parsed.getOrDefault(key, Long.toString(defaultValue)));
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}
