package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;
import jadex.bridge.fipa.FipaMessage;

public class InformAgent extends BaseBenchmarkAgent {
    @Override
    protected void startFirstRound() {
        sendInform();
    }

    @Override
    protected void handleProtocolMessage(FipaMessage msg) {
        if (FipaMessage.Performative.INFORM.equals(msg.getPerformative())) {
            continueOrStop(this::sendInform);
        }
    }

    private void sendInform() {
        IComponentIdentifier peer = AgentDirectory.randomPeer(index);
        if (peer == null) {
            stopAgent();
            return;
        }

        FipaMessage msg = new FipaMessage(FipaMessage.Performative.INFORM, randomPayload(), peer);
        msg.setConversationId(conversationId());
        msg.setReplyWith(replyWith());
        send(msg, peer);
    }
}
