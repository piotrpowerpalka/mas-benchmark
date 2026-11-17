repetitions_left(10).
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
        !send_query;
    }.

+query_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, query, Rw, Cid);
    !new_payload(ReplyPayload);
    .nano_time(T);
    ReplyRw = rw(T);
    !log_send(A, inform, ReplyRw, Cid);
    .send(A, signal, inform_msg(Cid, ReplyRw, ReplyPayload));
    ?repetitions_left(R);
    if (R > 0) {
        R1 = R - 1;
        .abolish(repetitions_left(_));
        +repetitions_left(R1);
        !send_query;
    }.

+inform_msg(Cid, Rw, Payload)[source(A)] : repetitions_left(0) <-
    !log_recv(A, inform, Rw, Cid);
    !stop_me.

+inform_msg(Cid, Rw, Payload)[source(A)] : repetitions_left(R) & R > 0 <-
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
    .nano_time(T1);
    .nano_time(T2);
    Rw = rw(T1);
    Cid = cid(T2).

+!new_payload(Payload) <-
    ?content_size(Sz);
    .nano_time(T);
    Payload = payload(Sz, T).

+!log_send(To, Perf, Rw, Cid) <-
    .my_name(Me);
    .date(Y,Mo,D);
    .time(H,Mi,S);
    .println(Me,";",To,";",Perf,";",Rw,";",Cid,";S;",Y,"-",Mo,"-",D,"T",H,":",Mi,":",S).

+!log_recv(From, Perf, Rw, Cid) <-
    .my_name(Me);
    .date(Y,Mo,D);
    .time(H,Mi,S);
    .println(From,";",Me,";",Perf,";",Rw,";",Cid,";R;",Y,"-",Mo,"-",D,"T",H,":",Mi,":",S).

+!log_init(State) <-
    .my_name(Me);
    .date(Y,Mo,D);
    .time(H,Mi,S);
    .println("init;",State,";",Me,";",Y,"-",Mo,"-",D,"T",H,":",Mi,":",S).

+!stop_me <-
    .my_name(Me);
    .println("info;Stoping agent;",Me);
    .kill_agent(Me).
