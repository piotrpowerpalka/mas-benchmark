repetitions_left(100).
content_size(1024).
seed(213742189290).
period_ms(100).

!boot.

+!boot <-
    !log_init(initializing);
    ?seed(S);
    .set_random_seed(S);
    !log_init(running).

+start(Rw, Cid)[source(A)] <-
    !log_recv(A, start, Rw, Cid);
    !send_periodic_informs.

+inform_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, inform, Rw, Cid).

+!send_periodic_informs <-
    ?repetitions_left(R);
    if (R > 0) {
        ?period_ms(P);
        .wait(P);
        !send_inform(R);
        R1 = R - 1;
        .abolish(repetitions_left(_));
        +repetitions_left(R1);
        !send_periodic_informs;
    }.

+!send_inform(Sequence) <-
    !pick_random_other(To);
    !new_ids(Rw, Cid);
    ?content_size(Sz);
    ?seed(S);
    .my_name(Me);
    .myLib.random_payload(Sz, S, Me, Sequence, Payload);
    !log_send(To, inform, Rw, Cid);
    .send(To, signal, inform_msg(Cid, Rw, Payload)).

+!pick_random_other(To) <-
    .all_names(All);
    .my_name(Me);
    .findall(A, (.member(A,All) & A \== Me & A \== init), Others);
    .random(Others, To).

+!new_ids(Rw, Cid) <-
    .myLib.uuid(RwId);
    .concat("rw-", RwId, Rw);
    .myLib.uuid(CidId);
    .concat("cid-", CidId, Cid).

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
