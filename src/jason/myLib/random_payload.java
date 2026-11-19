package jason.stdlib.myLib;

import java.util.Random;

import jason.asSemantics.DefaultInternalAction;
import jason.asSemantics.TransitionSystem;
import jason.asSemantics.Unifier;
import jason.asSyntax.ASSyntax;
import jason.asSyntax.NumberTerm;
import jason.asSyntax.Term;

public class random_payload extends DefaultInternalAction {
    private static final char[] ALPHABET =
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".toCharArray();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        if (args.length != 5) {
            throw new IllegalArgumentException(
                    "random_payload expects size, seed, agent name, sequence, and output");
        }

        int size = (int) ((NumberTerm) args[0]).solve();
        long seed = (long) ((NumberTerm) args[1]).solve();
        String agentName = args[2].toString();
        long sequence = (long) ((NumberTerm) args[3]).solve();
        if (size < 0) {
            throw new IllegalArgumentException("Payload size must not be negative");
        }

        Random random = new Random(seed ^ ((long) agentName.hashCode() << 32) ^ sequence);
        StringBuilder payload = new StringBuilder(size);
        for (int i = 0; i < size; i++) {
            payload.append(ALPHABET[random.nextInt(ALPHABET.length)]);
        }
        return un.unifies(args[4], ASSyntax.createString(payload.toString()));
    }
}
