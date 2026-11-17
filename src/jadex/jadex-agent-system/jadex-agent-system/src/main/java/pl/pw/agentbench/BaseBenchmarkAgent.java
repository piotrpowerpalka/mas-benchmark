package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;
import jadex.bridge.IInternalAccess;
import jadex.bridge.component.IExecutionFeature;
import jadex.bridge.component.IMessageFeature;
import jadex.bridge.fipa.FipaMessage;
import jadex.micro.annotation.Agent;
import jadex.micro.annotation.OnMessage;
import jadex.micro.annotation.OnStart;

import java.security.SecureRandom;
import java.util.List;
import java.util.Random;
import java.util.UUID;

public abstract class BaseBenchmarkAgent {
    @Agent
    protected IInternalAccess agent;

    protected Random random;
    protected int index;
    protected int repetitionsRemaining;
    protected final SecureRandom secureRandom = new SecureRandom();

    @OnStart
    public void onStart() {
        this.index = AgentDirectory.registerWorker(agent.getId());
        this.repetitionsRemaining = BenchmarkConfig.repetitionsNum;
        this.random = new Random(BenchmarkConfig.seed + (long) index * 9973L);
        LogUtil.logInitMessage("running", agent.getId().getName());
    }

    @OnMessage
    public void onMessage(FipaMessage msg) {
        LogUtil.logMessage(msg, "R");

        if ("Start".equals(msg.getContent())) {
            handleInitSignal();
            return;
        }

        handleProtocolMessage(msg);
    }

    protected void handleInitSignal() {
        if (repetitionsRemaining > 0) {
            repetitionsRemaining--;
            startFirstRound();
        } else {
            stopAgent();
        }
    }

    protected abstract void startFirstRound();

    protected abstract void handleProtocolMessage(FipaMessage msg);

    protected void send(FipaMessage msg, IComponentIdentifier... receivers) {
        LogUtil.logMessage(msg, "S");
        agent.getFeature(IMessageFeature.class).sendMessage(msg, receivers);
    }

    protected String randomPayload() {
        final String alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        StringBuilder sb = new StringBuilder(BenchmarkConfig.contentSize);
        for (int i = 0; i < BenchmarkConfig.contentSize; i++) {
            sb.append(alphabet.charAt(random.nextInt(alphabet.length())));
        }
        return sb.toString();
    }

    protected String replyWith() {
        return "rw-" + UUID.randomUUID();
    }

    protected String conversationId() {
        return "cid-" + UUID.randomUUID();
    }

    protected void stopAgent() {
        LogUtil.logInfoMessage("Stopping agent", agent.getId().getName());
        AgentDirectory.unregisterWorker(index);
        agent.killComponent();
    }

    protected void continueOrStop(Runnable nextStep) {
        if (repetitionsRemaining > 0) {
            repetitionsRemaining--;
            nextStep.run();
        } else {
            stopAgent();
        }
    }

    protected void shortDelay(long millis) {
        agent.getFeature(IExecutionFeature.class).waitForDelay(millis).get();
    }

    protected List<IComponentIdentifier> peers() {
        return AgentDirectory.getPeers(index);
    }
}
