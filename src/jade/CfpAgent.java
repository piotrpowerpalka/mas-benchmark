

import jade.core.AID;
import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.core.behaviours.OneShotBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class CfpAgent extends Agent {

    private int repetitions;
    private int contentSize;
    private int groupSize;

    private final List<String> agentsSet = new ArrayList<>();
    private final List<ACLMessage> offers = new ArrayList<>();
    private final List<ACLMessage> refusals = new ArrayList<>();

    @Override
    protected void setup() {
        Config cfg = Config.fromArgs(getArguments());
        this.repetitions = cfg.repetitionsNum;
        this.contentSize = cfg.contentSize;
        this.groupSize = cfg.groupSize;

        int myIdx = parseAgentIndex(getLocalName());
        for (int cnt = 0; cnt < cfg.numAgents; cnt++) {
            if (cnt != myIdx) agentsSet.add("agent" + cnt);
        }

        addBehaviour(new ReceiveInit());
        addBehaviour(new ReceiveCfpAcceptReject());
        addBehaviour(new ReceiveOffers());
    }

    private class SendCfpBehaviour extends OneShotBehaviour {
        @Override
        public void action() {
            // losowa próbka agentów o rozmiarze groupSize
            List<String> shuffled = new ArrayList<>(agentsSet);
            Collections.shuffle(shuffled, ThreadLocalRandom.current());

            List<String> grp = shuffled.subList(0, Math.min(groupSize, shuffled.size()));
            offers.clear();
            refusals.clear();

            for (String g : grp) {
                ACLMessage msg = new ACLMessage(ACLMessage.CFP);
                msg.setSender(this.myAgent.getAID());
                msg.addReceiver(new AID(g, AID.ISLOCALNAME));
                msg.setReplyWith("rw-" + UUID.randomUUID());
                msg.setConversationId("cid-" + UUID.randomUUID());
                msg.setContent(Tools.randomContent(contentSize));

                Tools.logMessage(msg, "S");
                send(msg);
            }
        }
    }

    private class ReceiveOffers extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.or(
                MessageTemplate.MatchPerformative(ACLMessage.PROPOSE),
                MessageTemplate.MatchPerformative(ACLMessage.REFUSE)
        );

        @Override
        public void action() {
            ACLMessage msg = myAgent.receive(mt);
            if (msg == null) {
                block();
                return;
            }

            Tools.logMessage(msg, "R");

            if (msg.getPerformative() == ACLMessage.PROPOSE) {
                offers.add(msg);
            } else if (msg.getPerformative() == ACLMessage.REFUSE) {
                refusals.add(msg);
            }

            if (offers.size() + refusals.size() == groupSize) {
                // Python wybiera random z offers (zakłada, że offers niepuste). Dla bezpieczeństwa:
                if (!offers.isEmpty()) {
                    ACLMessage winOffer = offers.get(ThreadLocalRandom.current().nextInt(offers.size()));
                    offers.remove(winOffer);

                    ACLMessage accept = winOffer.createReply();
                    accept.setPerformative(ACLMessage.ACCEPT_PROPOSAL);
                    accept.setReplyWith("rw-" + UUID.randomUUID());
                    accept.setContent(Tools.randomContent(contentSize));
                    Tools.logMessage(accept, "S");
                    send(accept);

                    for (ACLMessage off : offers) {
                        ACLMessage rej = off.createReply();
                        rej.setPerformative(ACLMessage.REJECT_PROPOSAL);
                        rej.setReplyWith("rw-" + UUID.randomUUID());
                        rej.setContent(Tools.randomContent(contentSize));
                        Tools.logMessage(rej, "S");
                        send(rej);
                    }
                }

                if (repetitions > 0) {
                    repetitions--;
                    myAgent.addBehaviour(new SendCfpBehaviour());
                }
            }
        }
    }

    private class ReceiveCfpAcceptReject extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.or(
                MessageTemplate.MatchPerformative(ACLMessage.CFP),
                MessageTemplate.or(
                        MessageTemplate.MatchPerformative(ACLMessage.ACCEPT_PROPOSAL),
                        MessageTemplate.MatchPerformative(ACLMessage.REJECT_PROPOSAL)
                )
        );

        @Override
        public void action() {
            ACLMessage msg = myAgent.receive(mt);
            if (msg == null) {
                block();
                return;
            }

            Tools.logMessage(msg, "R");

            if (msg.getPerformative() == ACLMessage.CFP) {
                ACLMessage reply = msg.createReply();

                // 0.9 propose, 0.1 refuse
                if (ThreadLocalRandom.current().nextDouble() <= 0.9) {
                    reply.setPerformative(ACLMessage.PROPOSE);
                } else {
                    reply.setPerformative(ACLMessage.REFUSE);
                }

                reply.setReplyWith("rw-" + UUID.randomUUID());
                reply.setContent(Tools.randomContent(contentSize));
                Tools.logMessage(reply, "S");
                send(reply);
            }

            // accept/reject w tym benchmarku tylko logujemy – brak dalszej logiki (jak w Python)
        }
    }

    private class ReceiveInit extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.MatchContent("Start");

        @Override
        public void action() {
            ACLMessage msg = myAgent.receive(mt);
            if (msg == null) {
                block();
                return;
            }
            Tools.logMessage(msg, "R");
            myAgent.addBehaviour(new SendCfpBehaviour());
            repetitions--;
        }
    }

    private static int parseAgentIndex(String localName) {
        if (localName == null) return -1;
        if (!localName.startsWith("agent")) return -1;
        try {
            return Integer.parseInt(localName.substring("agent".length()));
        } catch (Exception e) {
            return -1;
        }
    }
}
