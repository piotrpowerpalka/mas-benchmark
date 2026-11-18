

import java.util.HashMap;
import java.util.Map;

final class Config {
    String server = "serverhello";
    String password = "123456789"; // nieużywane w JADE, zostawione dla kompatybilności CLI
    int numAgents = 10;
    int fromAg = 0;
    int toAg = 9;
    int groupSize = 3;
    String communicationType = "inform";
    int contentSize = 1024;
    int repetitionsNum = 10;
    int initAg = 1;
    String containerName = "main-container";
    long seed = 213742189290L; 
    long period = 100L; // okres w ms dla TickerBehaviour

    static Config fromCli(String[] args) {
        // Minimalistyczny parser w stylu argparse (klucze dokładnie jak w Pythonie)
        Map<String, String> m = new HashMap<>();
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            if (a.startsWith("-") && i + 1 < args.length) {
                m.put(a, args[++i]);
            }
        }

        Config c = new Config();
        c.server = m.getOrDefault("-s", m.getOrDefault("--server", c.server));
        c.password = m.getOrDefault("-p", m.getOrDefault("--password", c.password));
        c.numAgents = Integer.parseInt(m.getOrDefault("-n", m.getOrDefault("--numagents", Integer.toString(c.numAgents))));
        c.fromAg = Integer.parseInt(m.getOrDefault("-f", m.getOrDefault("--fromag", Integer.toString(c.fromAg))));
        c.toAg = Integer.parseInt(m.getOrDefault("-t", m.getOrDefault("--toag", Integer.toString(c.toAg))));
        c.groupSize = Integer.parseInt(m.getOrDefault("-g", m.getOrDefault("--groupsize", Integer.toString(c.groupSize))));
        c.communicationType = m.getOrDefault("-c", m.getOrDefault("--communication-type", c.communicationType));
        c.contentSize = Integer.parseInt(m.getOrDefault("-x", m.getOrDefault("--content-size", Integer.toString(c.contentSize))));
        c.repetitionsNum = Integer.parseInt(m.getOrDefault("-r", m.getOrDefault("--repetitions-num", Integer.toString(c.repetitionsNum))));
        c.initAg = Integer.parseInt(m.getOrDefault("-i", m.getOrDefault("--initag", Integer.toString(c.initAg))));
        c.containerName = m.getOrDefault("--container-name", c.containerName);
        c.seed = Long.parseLong(m.getOrDefault("--seed", Long.toString(c.seed)));
        c.period = Long.parseLong(m.getOrDefault("-p", Long.toString(c.period)));
        return c;
    }

    static Config fromArgs(Object[] args) {
        Config c = new Config();
        if (args == null || args.length == 0) return c;

        // Oczekujemy Map<String,Object>
        @SuppressWarnings("unchecked")
        Map<String, Object> m = (Map<String, Object>) args[0];

        c.server = (String) m.getOrDefault("server", c.server);
        c.containerName = (String) m.getOrDefault("container-name", c.containerName);
        c.password = (String) m.getOrDefault("password", c.password);
        c.numAgents = ((Number) m.getOrDefault("numagents", c.numAgents)).intValue();
        c.fromAg = ((Number) m.getOrDefault("fromag", c.fromAg)).intValue();
        c.toAg = ((Number) m.getOrDefault("toag", c.toAg)).intValue();
        c.groupSize = ((Number) m.getOrDefault("groupsize", c.groupSize)).intValue();
        c.communicationType = (String) m.getOrDefault("communication-type", c.communicationType);
        c.contentSize = ((Number) m.getOrDefault("content-size", c.contentSize)).intValue();
        c.repetitionsNum = ((Number) m.getOrDefault("repetitions-num", c.repetitionsNum)).intValue();
        c.initAg = ((Number) m.getOrDefault("initag", c.initAg)).intValue();
        c.period = ((Number) m.getOrDefault("period", c.period)).longValue();
        c.seed = ((Number) m.getOrDefault("seed", c.seed)).longValue();
        return c;
    }

    Object[] toAgentArgs() {
        Map<String, Object> m = new HashMap<>();
        m.put("server", server);
        m.put("password", password);
        m.put("numagents", numAgents);
        m.put("fromag", fromAg);
        m.put("toag", toAg);
        m.put("groupsize", groupSize);
        m.put("communication-type", communicationType);
        m.put("content-size", contentSize);
        m.put("repetitions-num", repetitionsNum);
        m.put("initag", initAg);
        m.put("container-name", containerName);
        m.put("seed", seed);
        m.put("period", period);
        return new Object[]{m};
    }
}
