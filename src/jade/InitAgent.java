


import jade.core.AID;
import jade.core.Agent;
import jade.core.behaviours.OneShotBehaviour;
import jade.lang.acl.ACLMessage;

import java.util.UUID;

public class InitAgent extends Agent {

    public int runnedAgents;

    @Override
    protected void setup() {
        this.runnedAgents = 0;
        System.out.printf("Agent %s starting...%n", getLocalName());
        addBehaviour(new SendInitBehaviour());
        addBehaviour(new ReceiveFinish());
    }

    private class ReceiveFinish extends OneShotBehaviour {
        @Override
        public void action() {
            ACLMessage msg = receive();
            if (msg != null) {
                Tools.logMessage(msg, "R");
                System.out.printf("Agent %s finished.%n", getLocalName());
                InitAgent.this.runnedAgents--;
                if (InitAgent.this.runnedAgents <= 0) {
                    Config cfg = Config.fromArgs(getArguments());

                    for (int cnt = 0; cnt < cfg.numAgents; cnt++) {
                        ACLMessage fmsg = new ACLMessage(ACLMessage.INFORM);
                        fmsg.addReceiver(new AID("agent" + cnt, AID.ISLOCALNAME));
                        fmsg.setReplyWith(UUID.randomUUID().toString());
                        fmsg.setContent("Finish");

                        Tools.logMessage(fmsg, "S");
                        send(fmsg);
                    }
                }
            }
        }
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

                InitAgent.this.runnedAgents++;
            }
        }
    }
}
