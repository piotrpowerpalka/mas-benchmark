package pl.pw.agentbench;

import jadex.base.IPlatformConfiguration;
import jadex.base.PlatformConfigurationHandler;
import jadex.base.Starter;

public class Main {
    public static void main(String[] args) {
        BenchmarkConfig.fromArgs(args);

        IPlatformConfiguration config = PlatformConfigurationHandler.getMinimal();
        config.setGui(BenchmarkConfig.gui);

        for (int i = 0; i < BenchmarkConfig.numAgents; i++) {
            switch (BenchmarkConfig.communicationType) {
                case "inform":
                    config.addComponent(InformAgent.class);
                    break;
                case "query":
                    config.addComponent(QueryAgent.class);
                    break;
                case "cfp":
                case "negotiation":
                    config.addComponent(CfpAgent.class);
                    break;
                default:
                    throw new IllegalArgumentException("Unsupported communication type: " + BenchmarkConfig.communicationType);
            }
        }

        if (BenchmarkConfig.startInitAgent) {
            config.addComponent(InitAgent.class);
        }

        System.out.println("Starting JADEX benchmark...");
        Starter.createPlatform(config).get();
    }
}
