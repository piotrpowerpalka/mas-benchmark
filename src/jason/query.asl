repetitions_left(10).
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
    ?repetitions_left(R);
    !send_periodic_queries(R).

+!send_periodic_queries(0) <- true.

+!send_periodic_queries(R) : R > 0 <-
    ?period_ms(P);
    .wait(P);
    !send_query;
    R1 = R - 1;
    !send_periodic_queries(R1).

+query_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, query, Rw, Cid);
    !new_payload(ReplyPayload);
    !new_rw(ReplyRw);
    !log_send(A, inform, ReplyRw, Cid);
    .send(A, signal, inform_msg(Cid, ReplyRw, ReplyPayload)).

+inform_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, inform, Rw, Cid).

+!send_query <-
    !pick_random_other(To);
    !new_ids(Rw, Cid);
    !new_payload(Payload);
    !log_send(To, query, Rw, Cid);
    .send(To, signal, query_msg(Cid, Rw, Payload)).

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

+!new_rw(Rw) <-
    .myLib.uuid(Id);
    .concat("rw-", Id, Rw).

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
