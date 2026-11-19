repetitions_left(10).
content_size(1024).
groupsize(3).
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
    !send_periodic_cfps(R).

+!send_periodic_cfps(0) <- true.

+!send_periodic_cfps(R) : R > 0 <-
    ?period_ms(P);
    .wait(P);
    !start_round;
    R1 = R - 1;
    !send_periodic_cfps(R1).

+cfp_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, cfp, Rw, Cid);
    .random([propose,propose,propose,propose,propose,propose,propose,propose,propose,refuse], Decision);
    !new_payload(ReplyPayload);
    !new_rw(ReplyRw);
    if (Decision == propose) {
        !log_send(A, propose, ReplyRw, Cid);
        .send(A, signal, propose_msg(Cid, ReplyRw, ReplyPayload));
    } else {
        !log_send(A, refuse, ReplyRw, Cid);
        .send(A, signal, refuse_msg(Cid, ReplyRw, ReplyPayload));
    }.

+propose_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, propose, Rw, Cid);
    .count(round_recipient(Cid,A), Expected);
    if (Expected > 0) {
        .count(round_reply(Cid,A), Already);
        if (Already == 0) {
            +round_reply(Cid,A);
            +offer(Cid, A, Payload);
            !maybe_close_round(Cid)
        }
    }.

+refuse_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, refuse, Rw, Cid);
    .count(round_recipient(Cid,A), Expected);
    if (Expected > 0) {
        .count(round_reply(Cid,A), Already);
        if (Already == 0) {
            +round_reply(Cid,A);
            +refusal(Cid, A, Payload);
            !maybe_close_round(Cid)
        }
    }.

+accept_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, accept_proposal, Rw, Cid).

+reject_msg(Cid, Rw, Payload)[source(A)] <-
    !log_recv(A, reject_proposal, Rw, Cid).

+!start_round <-
    ?groupsize(G);
    !pick_random_group(G, Group);
    !new_ids(Rw, Cid);
    !new_payload(Payload);
    !register_round_recipients(Cid, Group);
    .count(round_recipient(Cid,_), Expected);
    if (Expected > 0) {
        !broadcast_cfp(Group, Cid, Rw, Payload)
    }.

+!register_round_recipients(_, []) <- true.

+!register_round_recipients(Cid, [A|Rest]) <-
    +round_recipient(Cid,A);
    !register_round_recipients(Cid, Rest).

+!broadcast_cfp([], _, _, _) <- true.

+!broadcast_cfp([A|Rest], Cid, Rw, Payload) <-
    !log_send(A, cfp, Rw, Cid);
    .send(A, signal, cfp_msg(Cid, Rw, Payload));
    !broadcast_cfp(Rest, Cid, Rw, Payload).

+!maybe_close_round(Cid) <-
    .count(round_recipient(Cid,_), Expected);
    .count(round_reply(Cid,_), Received);
    if (Expected > 0) {
        if (Received == Expected) {
            .count(offer(Cid, _, _), NO);
            if (NO > 0) {
                .findall(A, offer(Cid, A, _), Offerers);
                .random(Offerers, Winner);
                !accept_winner(Cid, Winner);
                !reject_others(Cid, Winner);
            };
            !cleanup_round(Cid)
        }
    }.

+!accept_winner(Cid, Winner) <-
    !new_payload(Payload);
    !new_rw(Rw);
    !log_send(Winner, accept_proposal, Rw, Cid);
    .send(Winner, signal, accept_msg(Cid, Rw, Payload)).

+!reject_others(Cid, Winner) <-
    .findall(A, offer(Cid, A, _), Offerers);
    !reject_list(Cid, Winner, Offerers).

+!reject_list(_, _, []) <- true.

+!reject_list(Cid, Winner, [A|Rest]) <-
    if (A \== Winner) {
        !new_payload(Payload);
        !new_rw(Rw);
        !log_send(A, reject_proposal, Rw, Cid);
        .send(A, signal, reject_msg(Cid, Rw, Payload));
    };
    !reject_list(Cid, Winner, Rest).

+!cleanup_round(Cid) <-
    .abolish(round_recipient(Cid, _));
    .abolish(round_reply(Cid, _));
    .abolish(offer(Cid, _, _));
    .abolish(refusal(Cid, _, _)).

+!pick_random_group(K, Group) <-
    .all_names(All);
    .my_name(Me);
    .findall(A, (.member(A,All) & A \== Me & A \== init), Others);
    .shuffle(Others, Shuffled);
    !take_first(K, Shuffled, Group).

+!take_first(0, _, []) <- true.

+!take_first(_, [], []) <- true.

+!take_first(K, [H|T], [H|Rest]) : K > 0 <-
    K1 = K - 1;
    !take_first(K1, T, Rest).

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
