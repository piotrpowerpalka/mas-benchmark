!boot.

+!boot <-
    !log_init(initializing);
    !log_init(running);
    !start.

+!start <-
    .all_names(All);
    .my_name(Me);
    .findall(A, (.member(A,All) & A \== Me), Targets);
    !send_starts(Targets);
    !stop_me.

+!send_starts([]) <- true.

+!send_starts([A|Rest]) <-
    .nano_time(T);
    Rw = rw(T);
    !log_send(A, start, Rw, none);
    .send(A, signal, start);
    !send_starts(Rest).

+!log_send(To, Perf, Rw, Cid) <-
    .my_name(Me);
    .date(Y,Mo,D);
    .time(H,Mi,S);
    .println(Me,";",To,";",Perf,";",Rw,";",Cid,";S;",Y,"-",Mo,"-",D,"T",H,":",Mi,":",S).

+!log_init(State) <-
    .my_name(Me);
    .date(Y,Mo,D);
    .time(H,Mi,S);
    .println("init;",State,";",Me,";",Y,"-",Mo,"-",D,"T",H,":",Mi,":",S).

+!stop_me <-
    .my_name(Me);
    .kill_agent(Me).
