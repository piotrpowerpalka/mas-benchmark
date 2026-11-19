repetitions_left(10).
content_size(1024).
groupsize(3).
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
        !start_round;
    }.

+cfp_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, cfp, Rw, Cid);
    .random([propose,propose,propose,propose,propose,propose,propose,propose,propose,refuse], Decision);
    !new_payload(ReplyPayload);
    .nano_time(T);
    ReplyRw = rw(T);
    if (Decision == propose) {
        !log_send(A, propose, ReplyRw, Cid);
        .send(A, signal, propose_msg(Cid, ReplyRw, ReplyPayload));
    } else {
        !log_send(A, refuse, ReplyRw, Cid);
        .send(A, signal, refuse_msg(Cid, ReplyRw, ReplyPayload));
    }.

+propose_msg(Cid, Rw, Payload)[source(A)] : current_round(Cid) <-
    !log_recv(A, propose, Rw, Cid);
    +offer(Cid, A, Payload);
    !maybe_close_round(Cid).

+refuse_msg(Cid, Rw, Payload)[source(A)] : current_round(Cid) <-
    !log_recv(A, refuse, Rw, Cid);
    +refusal(Cid, A, Payload);
    !maybe_close_round(Cid).

+accept_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, accept_proposal, Rw, Cid).

+reject_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, reject_proposal, Rw, Cid).

+!start_round <-
    ?groupsize(G);
    !pick_random_group(G, Group);
    !new_ids(Rw, Cid);
    !new_payload(Payload);
    .abolish(current_round(_));
    +current_round(Cid);
    .abolish(offer(Cid, _, _));
    .abolish(refusal(Cid, _, _));
    !broadcast_cfp(Group, Cid, Rw, Payload).

+!broadcast_cfp([], _, _, _) <- true.

+!broadcast_cfp([A|Rest], Cid, Rw, Payload) <-
    !log_send(A, cfp, Rw, Cid);
    .send(A, signal, cfp_msg(Cid, Rw, Payload));
    !broadcast_cfp(Rest, Cid, Rw, Payload).

+!maybe_close_round(Cid) <-
    ?groupsize(G);
    .count(offer(Cid, _, _), NO);
    .count(refusal(Cid, _, _), NR);
    Total = NO + NR;
    if (Total == G) {
        if (NO > 0) {
            .findall(A, offer(Cid, A, _), Offerers);
            .random(Offerers, Winner);
            !accept_winner(Cid, Winner);
            !reject_others(Cid, Winner);
        };
        !cleanup_round(Cid);
        ?repetitions_left(R);
        if (R > 0) {
            R1 = R - 1;
            .abolish(repetitions_left(_));
            +repetitions_left(R1);
            !start_round;
        } else {
            !stop_me;
        }
    }.

+!accept_winner(Cid, Winner) <-
    !new_payload(Payload);
    .nano_time(T);
    Rw = rw(T);
    !log_send(Winner, accept_proposal, Rw, Cid);
    .send(Winner, signal, accept_msg(Cid, Rw, Payload)).

+!reject_others(Cid, Winner) <-
    .findall(A, offer(Cid, A, _), Offerers);
    !reject_list(Cid, Winner, Offerers).

+!reject_list(_, _, []) <- true.

+!reject_list(Cid, Winner, [A|Rest]) <-
    if (A \== Winner) {
        !new_payload(Payload);
        .nano_time(T);
        Rw = rw(T);
        !log_send(A, reject_proposal, Rw, Cid);
        .send(A, signal, reject_msg(Cid, Rw, Payload));
    };
    !reject_list(Cid, Winner, Rest).

+!cleanup_round(Cid) <-
    .abolish(current_round(Cid));
    .abolish(offer(Cid, _, _));
    .abolish(refusal(Cid, _, _)).

+!pick_random_group(K, Group) <-
    .all_names(All);
    .my_name(Me);
    .findall(A, (.member(A,All) & A \== Me & A \== init), Others);
    .shuffle(Others, Shuffled);
    !take_first(K, Shuffled, Group).

+!take_first(0, _, []) <- true.

+!take_first(K, [H|T], [H|Rest]) : K > 0 <-
    K1 = K - 1;
    !take_first(K1, T, Rest).

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
