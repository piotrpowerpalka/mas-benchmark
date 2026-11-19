repetitions_left(100).
content_size(1024).
seed(213742189290).

!boot.

+!boot <-
    !log_init(initializing);
    ?seed(S);
    .set_random_seed(S);
    !log_init(running).

+start[source(A)] <-
    !log_recv(A, start, none, none);
    ?repetitions_left(R);
    if (R > 0) {
        R1 = R - 1;
        .abolish(repetitions_left(_));
        +repetitions_left(R1);
        !send_inform;
    }.

+inform_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, inform, Rw, Cid);
    ?repetitions_left(R);
    if (R > 0) {
        R1 = R - 1;
        .abolish(repetitions_left(_));
        +repetitions_left(R1);
        !send_inform;
    } else {
        !stop_me;
    }.

+!send_inform <-
    !pick_random_other(To);
    !new_ids(Rw, Cid);
    !new_payload(Payload);
    !log_send(To, inform, Rw, Cid);
    .send(To, signal, inform_msg(Cid, Rw, Payload)).

+!pick_random_other(To) <-
    .all_names(All);
    .my_name(Me);
    .findall(A, (.member(A,All) & A \== Me & A \== init), Others);
    .random(Others, To).

+!new_ids(Rw, Cid) <-
    .myLib.uuid(R);
    .nano_time(T2);
    .concat("rw-", R, Rw);
    Cid = cid(T2).

+!new_payload(Payload) <-
    ?content_size(Sz);
    .nano_time(T);
    Payload = payload(Sz, T).

+!log_send(To, Perf, Rw, Cid) <-
    .my_name(Me);
    .myLib.timestamp(Timestamp);
    .println(Me,";",To,";",Perf,";",Rw,";",Cid,";S;",Timestamp).

+!log_recv(From, Perf, Rw, Cid) <-
    .my_name(Me);
    .myLib.timestamp(Timestamp);
    .println(From,";",Me,";",Perf,";",Rw,";",Cid,";R;",Timestamp).

+!log_init(State) <-
    .my_name(Me);
    .myLib.timestamp(Timestamp);
    .println("init;",State,";",Me,";",Timestamp).

+!stop_me <-
    .my_name(Me);
    .println("info;Stoping agent;",Me);
    .kill_agent(Me).
