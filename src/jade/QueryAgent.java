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


public class QueryAgent extends Agent {

    private int repetitions;
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
        addBehaviour(new ReceiveMessage());
    }

    private class SendQueryBehaviour extends OneShotBehaviour {
        @Override
        public void action() {
            String to = agentsSet.get(QueryAgent.this.random.nextInt(agentsSet.size()));
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
            if (msg != null) {
                Tools.logMessage(msg, "R");

                if (msg.getPerformative() == ACLMessage.QUERY_REF) {
                    ACLMessage reply = msg.createReply();
                    reply.setSender(this.myAgent.getAID());
                    reply.setPerformative(ACLMessage.INFORM);
                    reply.setReplyWith("rw-" + UUID.randomUUID());
                    reply.setContent(Tools.randomContent(contentSize));

                    Tools.logMessage(reply, "S");
                    send(reply);
                }  
            }
            else {
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
            QueryAgent.this.repetitions--;
            myAgent.addBehaviour(new SendQueryBehaviour());

            if (QueryAgent.this.repetitions <= 0) {
                stop();
            }
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
