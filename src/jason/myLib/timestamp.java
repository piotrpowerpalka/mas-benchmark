package jason.stdlib.myLib;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import jason.asSemantics.DefaultInternalAction;
import jason.asSemantics.TransitionSystem;
import jason.asSemantics.Unifier;
import jason.asSyntax.ASSyntax;
import jason.asSyntax.Term;

public class timestamp extends DefaultInternalAction {
    private static final DateTimeFormatter FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS");

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("timestamp expects one argument");
        }
        String value = LocalDateTime.now().format(FORMAT);
        return un.unifies(args[0], ASSyntax.createString(value));
    }
}
