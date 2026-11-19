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
    !new_ids(Rw, Cid);
    !log_send(A, start, Rw, Cid);
    .send(A, signal, start(Rw, Cid));
    !send_starts(Rest).

+!new_ids(Rw, Cid) <-
    .myLib.uuid(RwId);
    .concat("rw-", RwId, Rw);
    .myLib.uuid(CidId);
    .concat("cid-", CidId, Cid).

+!log_send(To, Perf, Rw, Cid) <-
    .my_name(Me);
    .myLib.timestamp(Timestamp);
    .println(Me,";",To,";",Perf,";",Rw,";",Cid,";S;",Timestamp).

+!log_init(State) <-
    .my_name(Me);
    .myLib.timestamp(Timestamp);
    .println("init;",State,";",Me,";",Timestamp).

+!stop_me <-
    .my_name(Me);
    .kill_agent(Me).
