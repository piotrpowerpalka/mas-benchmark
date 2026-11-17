package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;
import jadex.bridge.IInternalAccess;
import jadex.bridge.component.IExecutionFeature;
import jadex.bridge.component.IMessageFeature;
import jadex.bridge.fipa.FipaMessage;
import jadex.micro.annotation.Agent;
import jadex.micro.annotation.OnStart;

import java.util.List;

public class InitAgent {
    @Agent
    protected IInternalAccess agent;

    @OnStart
    public void onStart() {
        LogUtil.logInitMessage("running", agent.getId().getName());

        while (AgentDirectory.countWorkers() < BenchmarkConfig.numAgents) {
            agent.getFeature(IExecutionFeature.class).waitForDelay(100).get();
        }

        List<IComponentIdentifier> all = AgentDirectory.allWorkers();
        for (IComponentIdentifier target : all) {
            FipaMessage msg = new FipaMessage(FipaMessage.Performative.INFORM, "Start", target);
            msg.setReplyWith("rw-init");
            msg.setConversationId("cid-init");
            LogUtil.logMessage(msg, "S");
            agent.getFeature(IMessageFeature.class).sendMessage(msg, target);
        }

        agent.killComponent();
    }
}
