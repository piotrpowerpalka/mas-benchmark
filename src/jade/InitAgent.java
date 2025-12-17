


import jade.core.AID;
import jade.core.Agent;
import jade.core.behaviours.OneShotBehaviour;
import jade.lang.acl.ACLMessage;

import java.util.UUID;

public class InitAgent extends Agent {

    @Override
    protected void setup() {
        System.out.printf("Agent %s starting...%n", getLocalName());
        addBehaviour(new SendInitBehaviour());
    }

    private class SendInitBehaviour extends OneShotBehaviour {
        @Override
        public void action() {
            Config cfg = Config.fromArgs(getArguments());

            for (int cnt = 0; cnt < cfg.numAgents; cnt++) {
                ACLMessage msg = new ACLMessage(ACLMessage.INFORM);
                msg.addReceiver(new AID("agent" + cnt, AID.ISLOCALNAME));
                msg.setReplyWith(UUID.randomUUID().toString());
                msg.setContent("Start");

                Tools.logMessage(msg, "S");
                send(msg);
            }

            System.out.printf("Stoping agent: %s%n", getLocalName());
            doDelete();
        }
    }
}
