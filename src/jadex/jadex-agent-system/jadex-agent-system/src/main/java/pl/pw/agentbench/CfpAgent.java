package pl.pw.agentbench;

import jadex.bridge.IComponentIdentifier;
import jadex.bridge.fipa.FipaMessage;

import java.util.ArrayList;
import java.util.List;

public class CfpAgent extends BaseBenchmarkAgent {
    private final List<FipaMessage> offers = new ArrayList<>();
    private final List<FipaMessage> refusals = new ArrayList<>();
    private String currentConversationId;
    private int expectedResponses;

    @Override
    protected void startFirstRound() {
        sendCfpRound();
    }

    @Override
    protected void handleProtocolMessage(FipaMessage msg) {
        String perf = msg.getPerformative();

        if (FipaMessage.Performative.CFP.equals(perf)) {
            FipaMessage reply = msg.createReply();
            boolean propose = random.nextDouble() <= 0.9d;
            reply.setPerformative(propose ? FipaMessage.Performative.PROPOSE : FipaMessage.Performative.REFUSE);
            reply.setReplyWith(replyWith());
            reply.setContent(randomPayload());
            send(reply);
            return;
        }

        if (!sameConversation(msg)) {
            return;
        }

        if (FipaMessage.Performative.PROPOSE.equals(perf)) {
            offers.add(msg);
        } else if (FipaMessage.Performative.REFUSE.equals(perf)) {
            refusals.add(msg);
        } else {
            return;
        }

        if (offers.size() + refusals.size() == expectedResponses) {
            evaluateRound();
        }
    }

    private boolean sameConversation(FipaMessage msg) {
        return currentConversationId != null && currentConversationId.equals(msg.getConversationId());
    }

    private void sendCfpRound() {
        offers.clear();
        refusals.clear();

        List<IComponentIdentifier> group = AgentDirectory.randomGroup(index, BenchmarkConfig.groupSize);
        if (group.isEmpty()) {
            stopAgent();
            return;
        }

        expectedResponses = group.size();
        currentConversationId = conversationId();

        for (IComponentIdentifier peer : group) {
            FipaMessage msg = new FipaMessage(FipaMessage.Performative.CFP, randomPayload(), peer);
            msg.setConversationId(currentConversationId);
            msg.setReplyWith(replyWith());
            send(msg, peer);
        }
    }

    private void evaluateRound() {
        if (!offers.isEmpty()) {
            FipaMessage winner = offers.remove(random.nextInt(offers.size()));

            FipaMessage accept = winner.createReply();
            accept.setPerformative(FipaMessage.Performative.ACCEPT_PROPOSAL);
            accept.setReplyWith(replyWith());
            accept.setContent(randomPayload());
            send(accept);

            for (FipaMessage other : offers) {
                FipaMessage reject = other.createReply();
                reject.setPerformative(FipaMessage.Performative.REJECT_PROPOSAL);
                reject.setReplyWith(replyWith());
                reject.setContent(randomPayload());
                send(reject);
            }
        }

        continueOrStop(this::sendCfpRound);
    }
}
