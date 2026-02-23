


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

public class InformAgent extends Agent {

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

        // Init: match treści "Start" (jak w SPADE templateInit.body="Start")
        addBehaviour(new ReceiveInit());
        // Inform: match performative INFORM
        addBehaviour(new ReceiveInform());
    }

    private class SendInformBehaviour extends OneShotBehaviour {
        @Override
        public void action() {
            String to = agentsSet.get(ThreadLocalRandom.current().nextInt(agentsSet.size()));
            ACLMessage msg = new ACLMessage(ACLMessage.INFORM);
            msg.setSender(this.myAgent.getAID());
            msg.addReceiver(new AID(to, AID.ISLOCALNAME));
            msg.setReplyWith("rw-" + UUID.randomUUID());
            msg.setConversationId("cid-" + UUID.randomUUID());
            msg.setContent(Tools.randomContent(contentSize));

            Tools.logMessage(msg, "S");
            send(msg);
        }
    }

    private class ReceiveInform extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.MatchPerformative(ACLMessage.INFORM);

        @Override
        public void action() {
            // Odpowiednik: await self.receive(15)
            ACLMessage msg = myAgent.blockingReceive(mt, 15000);
            if (msg == null) {
                block();
                return;
            }

            if (msg != null) {
                Tools.logMessage(msg, "R");
                if (repetitions > 0) {
                    repetitions--;
                    myAgent.addBehaviour(new SendInformBehaviour());
                }
                
                else if (repetitions == 0) {
                    System.out.printf("Stoping agent: %s%n", getLocalName());
                    myAgent.doDelete();
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
            myAgent.addBehaviour(new SendInformBehaviour());
            repetitions--;
        }
    }

    private static int parseAgentIndex(String localName) {
        // "agent7" -> 7
        if (localName == null) return -1;
        if (!localName.startsWith("agent")) return -1;
        try {
            return Integer.parseInt(localName.substring("agent".length()));
        } catch (Exception e) {
            return -1;
        }
    }
}
