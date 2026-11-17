package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;
import jadex.bridge.fipa.FipaMessage;

public class QueryAgent extends BaseBenchmarkAgent {
    @Override
    protected void startFirstRound() {
        sendQuery();
    }

    @Override
    protected void handleProtocolMessage(FipaMessage msg) {
        if (FipaMessage.Performative.QUERY_REF.equals(msg.getPerformative())) {
            FipaMessage reply = msg.createReply();
            reply.setPerformative(FipaMessage.Performative.INFORM);
            reply.setReplyWith(replyWith());
            reply.setContent(randomPayload());
            send(reply);
            return;
        }

        if (FipaMessage.Performative.INFORM.equals(msg.getPerformative())) {
            continueOrStop(this::sendQuery);
        }
    }

    private void sendQuery() {
        IComponentIdentifier peer = AgentDirectory.randomPeer(index);
        if (peer == null) {
            stopAgent();
            return;
        }

        FipaMessage msg = new FipaMessage(FipaMessage.Performative.QUERY_REF, randomPayload(), peer);
        msg.setConversationId(conversationId());
        msg.setReplyWith(replyWith());
        send(msg, peer);
    }
}
