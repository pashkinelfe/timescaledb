# reorder should be fully blocker by an insert into the chunk being reordered
setup
{
 CREATE TABLE ts_reorder_test(time int, temp float, location int);
 SELECT create_hypertable('ts_reorder_test', 'time', chunk_time_interval => 10);
 INSERT INTO ts_reorder_test VALUES (1, 23.4, 1),
       (11, 21.3, 2),
       (21, 19.5, 3);

 CREATE TABLE waiter(i INTEGER);
 -- like reluster_chunk execpt that it'll attempt to grab an release a ACCESS EXCLUSIVE
 -- lock on wait_on before swapping the tables. This allows us to control interleaving more.
 CREATE OR REPLACE FUNCTION reorder_chunk_i(
     chunk REGCLASS,
     index REGCLASS=NULL,
     verbose BOOLEAN=FALSE,
     wait_on REGCLASS=NULL
 ) RETURNS VOID AS '$libdir/timescaledb-1.2.0-dev', 'ts_reorder_chunk' LANGUAGE C VOLATILE;
}

teardown {
      DROP TABLE ts_reorder_test;
      DROP TABLE waiter;
}

session "I"
setup		{ BEGIN; SET LOCAL lock_timeout = '50ms'; SET LOCAL deadlock_timeout = '10ms';}
step "I1"	{ INSERT INTO ts_reorder_test VALUES (1, 19.5, 3); }
step "Ic"	{ COMMIT; }

session "R"
setup		{ BEGIN; SET LOCAL lock_timeout = '50ms'; SET LOCAL deadlock_timeout = '10ms'; }
step "R1"	{ SELECT reorder_chunk_i((SELECT show_chunks('ts_reorder_test') LIMIT 1), 'ts_reorder_test_time_idx', wait_on => 'waiter'); }
step "Rc"	{ COMMIT; }

session "B"
setup		{ BEGIN; LOCK TABLE waiter; }
step "Bc"   { COMMIT; }


permutation "Bc" "I1" "Ic" "R1" "Rc"
permutation "Bc" "I1" "R1" "Ic" "Rc"
permutation "Bc" "I1" "R1" "Rc" "Ic"

permutation "Bc" "R1" "Rc" "I1" "Ic"
permutation "Bc" "R1" "I1" "Rc" "Ic"
permutation "Bc" "R1" "I1" "Ic" "Rc"

permutation "R1" "I1" "Ic" "Bc" "Rc"
permutation "R1" "I1" "Bc" "Rc" "Ic"
permutation "I1" "R1" "Bc" "Rc" "Ic"
