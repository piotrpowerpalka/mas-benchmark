

import jade.core.Profile;
import jade.core.ProfileImpl;
import jade.core.Runtime;
import jade.wrapper.AgentController;
import jade.wrapper.ContainerController;


public class Main {

    public static void main(String[] args) throws Exception {
        System.out.println("Starting...");

        Config cfg = Config.fromCli(args);

        // JADE runtime + main container
        Runtime rt = Runtime.instance();
        rt.setCloseVM(true);

        Profile p = new ProfileImpl();
        // Jeżeli uruchamiasz zdalnie – ustaw host/port odpowiednio.
        // Tu domyślnie: main-container lokalny; 'server' trzymamy dla kompatybilności z CLI.
        p.setParameter(Profile.MAIN_HOST, cfg.server);
        p.setParameter(Profile.GUI, "false");

        ContainerController main = rt.createMainContainer(p);

        // Start agents in range
        for (int cnt = cfg.fromAg; cnt <= cfg.toAg; cnt++) {
            String aname = "agent" + cnt;
            Tools.logInitMessage("initializing", aname);

            Class<?> clazz = switch (cfg.communicationType) {
                case "inform" -> InformAgent.class;
                case "query" -> QueryAgent.class;
                case "cfp" -> CfpAgent.class;
                default -> throw new IllegalArgumentException("Unsupported communication-type: " + cfg.communicationType);
            };

            Object[] agentArgs = cfg.toAgentArgs();
            AgentController ac = main.createNewAgent(aname, clazz.getName(), agentArgs);
            Tools.logInitMessage("running", aname);
            ac.start();
        }

        if (cfg.initAg == 1) {
            String iname = "agent-init";
            Tools.logInitMessage("initializing", iname);
            AgentController init = main.createNewAgent(iname, InitAgent.class.getName(), cfg.toAgentArgs());
            Tools.logInitMessage("running", iname);
            init.start();
        }
    }
}
