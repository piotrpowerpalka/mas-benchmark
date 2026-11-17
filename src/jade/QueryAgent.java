

import jade.core.AID;
import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.core.behaviours.OneShotBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;

public class QueryAgent extends Agent {

    private int repetitions;
    private int contentSize;
    private List<String> agentsSet = new ArrayList<>();

    @Override
    protected void setup() {
        Config cfg = Config.fromArgs(getArguments());
        this.repetitions = cfg.repetitionsNum;
        this.contentSize = cfg.contentSize;

        int myIdx = parseAgentIndex(getLocalName());
        for (int cnt = 0; cnt < cfg.numAgents; cnt++) {
            if (cnt != myIdx) agentsSet.add("agent" + cnt);
        }

        addBehaviour(new ReceiveInit());
        addBehaviour(new ReceiveMessage());
    }

    private class SendQueryBehaviour extends OneShotBehaviour {
        @Override
        public void action() {
            String to = agentsSet.get(ThreadLocalRandom.current().nextInt(agentsSet.size()));

            ACLMessage msg = new ACLMessage(ACLMessage.QUERY_REF); // "query"
            msg.setSender(this.myAgent.getAID());
            msg.addReceiver(new AID(to, AID.ISLOCALNAME));
            msg.setReplyWith("rw-" + UUID.randomUUID());
            msg.setConversationId("cid-" + UUID.randomUUID());
            msg.setContent(Tools.randomContent(contentSize));

            Tools.logMessage(msg, "S");
            send(msg);
        }
    }

    private class ReceiveMessage extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.or(
                MessageTemplate.MatchPerformative(ACLMessage.QUERY_REF),
                MessageTemplate.MatchPerformative(ACLMessage.INFORM)
        );

        @Override
        public void action() {
            ACLMessage msg = myAgent.receive(mt);
            if (msg == null) {
                block();
                return;
            }

            if (msg != null) {
                Tools.logMessage(msg, "R");

                if (msg.getPerformative() == ACLMessage.QUERY_REF) {
                    ACLMessage reply = msg.createReply();
                    reply.setPerformative(ACLMessage.INFORM);
                    reply.setReplyWith("rw-" + UUID.randomUUID());
                    reply.setContent(Tools.randomContent(contentSize));

                    Tools.logMessage(reply, "S");
                    send(reply);

                    if (repetitions > 0) {
                        repetitions--;
                        try {
                            TimeUnit.MILLISECONDS.sleep(10);
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                        }
                        myAgent.addBehaviour(new SendQueryBehaviour());
                    }
                    else if (repetitions == 0) {
//                        System.out.printf("Stoping agent: %s%n", getLocalName());
//                        myAgent.doDelete();
                    }
                }  
            }
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
            myAgent.addBehaviour(new SendQueryBehaviour());
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
