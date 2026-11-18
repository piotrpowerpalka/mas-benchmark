import jade.core.AID;
import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.core.behaviours.OneShotBehaviour;
import jade.core.behaviours.TickerBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;

public class InformAgent extends Agent {

    public int repetitions;
    private int contentSize;
    private List<String> agentsSet = new ArrayList<>();
    private final Random random = new Random();
    
    @Override
    protected void setup() {
        Config cfg = Config.fromArgs(getArguments());
        this.repetitions = cfg.repetitionsNum;
        this.contentSize = cfg.contentSize;
        this.random.setSeed(cfg.seed);

        int myIdx = parseAgentIndex(getLocalName());
        for (int cnt = 0; cnt < cfg.numAgents; cnt++) {
            if (cnt != myIdx) agentsSet.add("agent" + cnt);
        }

        addBehaviour(new ReceiveInit());
        addBehaviour(new ReceiveInform());
    }

    private class SendInformBehaviour extends OneShotBehaviour {
        @Override
        public void action() {
            String to = agentsSet.get(InformAgent.this.random.nextInt(agentsSet.size()));
            ACLMessage msg = new ACLMessage(ACLMessage.INFORM);
            msg.setSender(this.myAgent.getAID());
            msg.addReceiver(new AID(to, AID.ISLOCALNAME));
            msg.setReplyWith("rw-" + UUID.randomUUID());
            msg.setConversationId("cid-" + UUID.randomUUID());
            msg.setContent(Tools.randomContent(contentSize));
            send(msg);
            Tools.logMessage(msg, "S");
        }
    }

    private class ReceiveInform extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.MatchPerformative(ACLMessage.INFORM);

        @Override
        public void action() {
            ACLMessage msg = myAgent.receive(mt);
            if (msg != null) {
                Tools.logMessage(msg, "R");
            } else {
                block();
            }
        }
    }

    private class ReceiveInit extends CyclicBehaviour {
        private final MessageTemplate mt = MessageTemplate.MatchContent("Start");

        @Override
        public void action() {
            ACLMessage msg = myAgent.receive(mt);
            if (msg != null) {
                Tools.logMessage(msg, "R");
                myAgent.addBehaviour(new myTickerBehaviour(myAgent, Config.fromArgs(getArguments()).period));  
            } else {
                block();
            }
        }
    }

    private class myTickerBehaviour extends TickerBehaviour {
        public myTickerBehaviour(Agent agent, long period) {
            super(agent, period);
        }

        @Override
        protected void onTick() {
            InformAgent.this.repetitions--;
            myAgent.addBehaviour(new SendInformBehaviour());

            if (InformAgent.this.repetitions <= 0) {
                stop();
            }
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
