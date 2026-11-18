package jason.stdlib.myLib;

import java.util.UUID;
import jason.asSemantics.DefaultInternalAction;
import jason.asSemantics.TransitionSystem;
import jason.asSemantics.Unifier;
import jason.asSyntax.ASSyntax;
import jason.asSyntax.Term;

public class uuid extends DefaultInternalAction {
    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        String id = UUID.randomUUID().toString();
        return un.unifies(args[0], ASSyntax.createString(id));
    }
}