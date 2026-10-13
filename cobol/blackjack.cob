>>SOURCE FORMAT FREE
IDENTIFICATION DIVISION.
PROGRAM-ID. BLACKJACK.
AUTHOR. OPENCODE.
ENVIRONMENT DIVISION.
CONFIGURATION SECTION.
SOURCE-COMPUTER. GnuCOBOL-3.
OBJECT-COMPUTER. GnuCOBOL-3.
INPUT-OUTPUT SECTION.
FILE-CONTROL.
    SELECT STAT-FILE ASSIGN TO "BLACKJACK.DAT"
        ORGANIZATION IS LINE SEQUENTIAL
        FILE STATUS IS WS-FILE-STAT.

DATA DIVISION.
FILE SECTION.
*> The statistics file is plain text so a damaged file can be detected
*> and ignored instead of loading rubbish into the counters.
*>   1-6 wins   7-12 pushes   13-18 losses   19-24 rounds
*>   25 sign, 26-34 net      35 sign, 36-44 best
FD  STAT-FILE.
01  STAT-RECORD.
    05 SR-AREA   PIC X(200).

WORKING-STORAGE SECTION.

01  WS-FILE-STAT       PIC XX VALUE SPACES.
01  WS-EOF             PIC X  VALUE "N".
01  ST-DIRTY           PIC X  VALUE "N".
01  WS-ALL-BLANK       PIC X(96) VALUE SPACES.

*> fields used to build and validate the statistics record
01  WS-STAT-OK         PIC 9 VALUE ZERO.
01  WS-N9              PIC 9(9) VALUE ZERO.
01  WS-TREC.
    05 WS-T-WINS       PIC X(6) VALUE SPACES.
    05 WS-T-PUSH       PIC X(6) VALUE SPACES.
    05 WS-T-LOSS       PIC X(6) VALUE SPACES.
    05 WS-T-ROUND      PIC X(6) VALUE SPACES.
    05 WS-T-NSIGN      PIC X VALUE "+".
    05 WS-T-NET        PIC X(9) VALUE SPACES.
    05 WS-T-BSIGN      PIC X VALUE "+".
    05 WS-T-BEST       PIC X(9) VALUE SPACES.

*> ---------------------------------------------------------------
*> command input
*> ---------------------------------------------------------------
01  WS-CMD-LINE        PIC X(96) VALUE SPACES.
01  WS-BLANK-RUN       PIC 9(4) VALUE ZERO.
01  WS-VERB            PIC X(12) VALUE SPACES.
01  WS-VERB-C          PIC X(12) VALUE SPACES.
01  WS-ARG             PIC X(30) VALUE SPACES.

*> display-form scratch fields used to build the protocol records.
*> numerics are always moved into one of these before being emitted.
01  WS-S-PHASE        PIC X(12) VALUE SPACES.
01  WS-S-IDX          PIC 9(1)  VALUE ZERO.
01  WS-S-N1           PIC 9(4)  VALUE ZERO.
01  WS-S-N2           PIC 9(10) VALUE ZERO.
01  WS-S-N3           PIC 9(10) VALUE ZERO.
01  WS-S-N4           PIC 9(10) VALUE ZERO.
01  WS-S-S1           PIC S9(10) VALUE ZERO.
01  WS-S-S2           PIC S9(10) VALUE ZERO.
01  WS-S-C1           PIC X VALUE SPACE.
01  WS-S-C2           PIC X VALUE SPACE.
01  WS-S-C3           PIC X VALUE SPACE.
01  WS-S-C4           PIC X VALUE SPACE.
01  WS-S-C5           PIC X VALUE SPACE.
01  WS-S-C6           PIC X VALUE SPACE.
01  WS-S-ZZ            PIC ZZZ9 VALUE ZERO.
01  WS-CARD-ROW       PIC X(48) VALUE SPACES.
01  WS-CARD-TOK       PIC X(3)  VALUE SPACES.
01  WS-CARD-SLOT      PIC X(4)  VALUE SPACES.
01  WS-CARD-CUR       PIC 99    VALUE ZERO.

*> ---------------------------------------------------------------
*> card model: card code 1..52 = ((rank - 1) * 4) + suit
*>   rank  1=A .. 13=K        suit 1=H 2=D 3=C 4=S
*> ---------------------------------------------------------------
01  WS-RANK-CHARS      PIC X(13) VALUE "A23456789TJQK".
01  WS-SUIT-CHARS      PIC X(4)  VALUE "HDCS".
01  WS-CARD            PIC 9(2) COMP-3 VALUE ZERO.
01  WS-RANK            PIC 9(2) COMP-3 VALUE ZERO.
01  WS-SUIT            PIC 99  COMP-3 VALUE ZERO.

*> precomputed per-card lookup tables (1..52)
01  WS-CARD-TABLES.
    05 WS-CARD-RANK   PIC 9(2) OCCURS 52 TIMES.
    05 WS-CARD-VAL    PIC 9(2) OCCURS 52 TIMES.
    05 WS-CARD-DELTA  PIC S9 OCCURS 52 TIMES.

*> ---------------------------------------------------------------
*> shoe - six decks, reshuffle at 75% penetration
*> ---------------------------------------------------------------
01  WS-DECK-NUMBER     PIC 99 COMP-3 VALUE 6.
01  WS-SHOE            PIC 9(3) COMP-3 OCCURS 312 TIMES.
01  WS-SHOE-POS        PIC 9(3) COMP-3 VALUE ZERO.
01  WS-SHOE-LEN        PIC 9(3) COMP-3 VALUE 312.
01  WS-SHOE-TOP        PIC 9(3) COMP-3 VALUE 234.
01  WS-I               PIC 9(4) COMP-3 VALUE ZERO.
01  WS-J               PIC 9(2) COMP-3 VALUE ZERO.
01  WS-SWAP            PIC 9(3) COMP-3 VALUE ZERO.
01  WS-PICK            PIC 9(3) COMP-3 VALUE ZERO.
01  WS-SEED            PIC 9(10) COMP-3 VALUE 12345.
01  WS-SEED-RAW        PIC 9(6)  COMP-3 VALUE ZERO.
01  WS-DATE-TXT        PIC X(21) VALUE SPACES.

*> ---------------------------------------------------------------
*> the table - hand 1 is always the dealer, hand 2 is the player
*>   HR-STATUS  E=EMPTY A=ACTIVE S=STAND B=BUST J=BLACKJACK
*> ---------------------------------------------------------------
01  WS-HANDS.
    05 WS-HAND-ROW OCCURS 2 TIMES.
        10 HR-ROLE     PIC X    VALUE "P".
        10 HR-BET      PIC 9(9) VALUE ZERO.
        10 HR-NCARDS   PIC 99   VALUE ZERO.
        10 HR-CARD     PIC 9(2) COMP-3 OCCURS 11 TIMES.
        10 HR-STATUS   PIC X    VALUE "E".
        10 HR-SOFT     PIC X    VALUE "N".
        10 HR-TOTAL    PIC 99   VALUE ZERO.
        10 HR-RESULT   PIC X    VALUE "-".
        10 HR-PAID     PIC 9(9) VALUE ZERO.

01  WS-HAND-N          PIC 9 COMP-3 VALUE ZERO.
01  WS-HAND-NOW        PIC 9 COMP-3 VALUE ZERO.
01  WS-ACT-HAND        PIC 9 COMP-3 VALUE ZERO.
01  WS-DLR-HAND        PIC 9 COMP-3 VALUE 1.
01  WS-DEAL-TARGET     PIC 9 COMP-3 VALUE ZERO.
01  WS-DOUBLE-OK       PIC X VALUE "N".
01  WS-INS-TAKEN       PIC X VALUE "N".
01  WS-SUM             PIC 9(4) COMP-3 VALUE ZERO.
01  WS-ACES            PIC 99 COMP-3 VALUE ZERO.

*> ---------------------------------------------------------------
*> money - every amount is held in CENTS
*> ---------------------------------------------------------------
01  WS-BANKROLL        PIC 9(9)  VALUE 50000.
01  WS-BET             PIC 9(9)  VALUE 500.
01  WS-STAKE           PIC 9(9)  VALUE ZERO.
01  WS-NET             PIC S9(9) VALUE ZERO.
01  WS-INS-BET         PIC 9(9)  VALUE ZERO.
01  WS-INS-PAID        PIC 9(9)  VALUE ZERO.
01  ST-WINS            PIC 9(6)  VALUE ZERO.
01  ST-PUSH            PIC 9(6)  VALUE ZERO.
01  ST-LOSS            PIC 9(6)  VALUE ZERO.
01  ST-ROUND           PIC 9(6)  VALUE ZERO.
01  ST-NET             PIC S9(9) VALUE ZERO.
01  ST-BEST            PIC S9(9) VALUE ZERO.

*> hi-lo card counting
01  WS-COUNT           PIC S9(4) COMP-3 VALUE ZERO.
01  WS-TRUE-COUNT      PIC S9(4) COMP-3 VALUE ZERO.
01  WS-DECKS-LEFT      PIC 9(2) COMP-3 VALUE 6.
01  WS-FACE-DOWN       PIC X VALUE "N".
*> the dealer's hole card is only added to the count once it is revealed
01  WS-HOLE-COUNTED    PIC X VALUE "N".

*> interface state
01  WS-PHASE           PIC X(12) VALUE "IDLE".
01  WS-NOTE            PIC X(120) VALUE SPACES.
01  WS-RESULT-LINE     PIC X VALUE "-".

PROCEDURE DIVISION.

MAIN.
    MOVE SPACES TO WS-NOTE
    DISPLAY "READY"
    PERFORM PROC-LOAD-STATS
    PERFORM PROC-BUILD-TABLES
    PERFORM PROC-SEED-RANDOM
    PERFORM PROC-SHOE-FILL
    MOVE 0 TO WS-COUNT
    MOVE 0 TO WS-SHOE-POS
    MOVE "IDLE" TO WS-PHASE
    MOVE "Place your bet and press DEAL." TO WS-NOTE
    MOVE "N" TO WS-EOF
    PERFORM UNTIL WS-EOF = "Y"
        PERFORM PROC-READ-COMMAND
        IF WS-EOF NOT = "Y"
            PERFORM PROC-EMIT-STATE
        END-IF
    END-PERFORM
    PERFORM PROC-SAVE-STATS
    GOBACK.

PROC-READ-COMMAND.
*> GnuCOBOL gives no way to tell an empty input line from end of input, so
*> blank lines are ignored and a run of them is treated as end of input. A
*> client never sends a blank command, and end of input still stops the
*> program straight away.
    MOVE SPACES TO WS-CMD-LINE
    ACCEPT WS-CMD-LINE
    IF WS-CMD-LINE = WS-ALL-BLANK
        ADD 1 TO WS-BLANK-RUN
        IF WS-BLANK-RUN >= 32
            MOVE "Y" TO WS-EOF
        END-IF
    ELSE
        MOVE ZERO TO WS-BLANK-RUN
        PERFORM PROC-HANDLE-COMMAND
    END-IF.

*> ===============================================================
*> command dispatch
*> ===============================================================
PROC-HANDLE-COMMAND.
    MOVE SPACES TO WS-NOTE
    MOVE SPACES TO WS-VERB
    MOVE SPACES TO WS-ARG
    UNSTRING WS-CMD-LINE DELIMITED BY ALL SPACE
        INTO WS-VERB WS-ARG
    END-UNSTRING
    MOVE FUNCTION TRIM(WS-VERB) TO WS-VERB-C
    EVALUATE WS-VERB-C
        WHEN "DEAL"     PERFORM PROC-CMD-DEAL
        WHEN "BET"      PERFORM PROC-CMD-BET
        WHEN "HIT"      PERFORM PROC-CMD-HIT
        WHEN "STAND"    PERFORM PROC-CMD-STAND
        WHEN "DOUBLE"   PERFORM PROC-CMD-DOUBLE
        WHEN "INSURE"   PERFORM PROC-CMD-INSURE
        WHEN "NOINSURE" PERFORM PROC-CMD-NOINSURE
        WHEN "INFO"     CONTINUE
        WHEN "QUIT"     MOVE "Y" TO WS-EOF
        WHEN OTHER      MOVE "Unknown command." TO WS-NOTE
    END-EVALUATE.

PROC-CMD-BET.
    IF WS-PHASE NOT = "IDLE" AND WS-PHASE NOT = "SETTLE"
        MOVE "You cannot change the bet mid-round." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF FUNCTION NUMVAL(WS-ARG) < 0
        MOVE "Bet must be positive." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF FUNCTION NUMVAL(WS-ARG) = 0
        MOVE "Bet must be greater than zero." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF FUNCTION NUMVAL(WS-ARG) > 50
        MOVE "Table limit is $50.00." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    COMPUTE WS-BET ROUNDED = FUNCTION NUMVAL(WS-ARG) * 100
    MOVE "Bet updated." TO WS-NOTE.

PROC-CMD-DEAL.
    PERFORM PROC-DEAL-ROUND.

PROC-CMD-HIT.
    IF WS-PHASE NOT = "PLAYER"
        MOVE "Not your move." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    PERFORM PROC-FIND-ACTIVE
    IF WS-ACT-HAND = 0
        MOVE "No active hand." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    MOVE WS-ACT-HAND TO WS-DEAL-TARGET
    PERFORM PROC-DRAW
    EVALUATE TRUE
        WHEN HR-TOTAL(WS-ACT-HAND) > 21
            MOVE "B" TO HR-STATUS(WS-ACT-HAND)
            MOVE "Bust." TO WS-NOTE
        WHEN HR-TOTAL(WS-ACT-HAND) = 21
            MOVE "S" TO HR-STATUS(WS-ACT-HAND)
            MOVE "Twenty-one." TO WS-NOTE
        WHEN OTHER
            MOVE "You hit." TO WS-NOTE
    END-EVALUATE
    PERFORM PROC-AFTER-PLAYER-MOVE.

PROC-CMD-STAND.
    IF WS-PHASE NOT = "PLAYER"
        MOVE "Not your move." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    PERFORM PROC-FIND-ACTIVE
    IF WS-ACT-HAND = 0
        MOVE "No active hand." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    MOVE "S" TO HR-STATUS(WS-ACT-HAND)
    MOVE "You stand." TO WS-NOTE
    PERFORM PROC-AFTER-PLAYER-MOVE.

PROC-CMD-DOUBLE.
    IF WS-PHASE NOT = "PLAYER"
        MOVE "Not your move." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF WS-DOUBLE-OK NOT = "Y"
        MOVE "You cannot double right now." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    MOVE WS-ACT-HAND TO WS-HAND-NOW
    IF WS-BANKROLL < HR-BET(WS-HAND-NOW)
        MOVE "Not enough chips to double." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    SUBTRACT HR-BET(WS-HAND-NOW) FROM WS-BANKROLL
    ADD HR-BET(WS-HAND-NOW) TO WS-STAKE
    COMPUTE HR-BET(WS-HAND-NOW) = HR-BET(WS-HAND-NOW) * 2
    MOVE WS-HAND-NOW TO WS-DEAL-TARGET
    PERFORM PROC-DRAW
    MOVE "S" TO HR-STATUS(WS-HAND-NOW)
    MOVE "N" TO WS-DOUBLE-OK
    EVALUATE TRUE
        WHEN HR-TOTAL(WS-HAND-NOW) > 21
            MOVE "B" TO HR-STATUS(WS-HAND-NOW)
            MOVE "Doubled down and busted." TO WS-NOTE
        WHEN OTHER
            MOVE "Doubled down." TO WS-NOTE
    END-EVALUATE
    PERFORM PROC-AFTER-PLAYER-MOVE.

PROC-CMD-INSURE.
    IF WS-PHASE NOT = "INSURANCE"
        MOVE "No insurance offered." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    COMPUTE WS-INS-BET ROUNDED = WS-BET / 2
    IF WS-BANKROLL < WS-INS-BET
        COMPUTE WS-INS-BET ROUNDED = WS-BANKROLL
    END-IF
    SUBTRACT WS-INS-BET FROM WS-BANKROLL
    ADD WS-INS-BET TO WS-STAKE
    MOVE "Y" TO WS-INS-TAKEN
    MOVE "Insurance taken." TO WS-NOTE
    PERFORM PROC-PEEK-DEALER.

PROC-CMD-NOINSURE.
    IF WS-PHASE NOT = "INSURANCE"
        MOVE "No insurance offered." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    MOVE 0 TO WS-INS-BET
    MOVE "Insurance declined." TO WS-NOTE
    PERFORM PROC-PEEK-DEALER.

*> ===============================================================
*> round lifecycle
*> ===============================================================
PROC-DEAL-ROUND.
    IF WS-PHASE NOT = "IDLE" AND WS-PHASE NOT = "SETTLE"
        MOVE "Finish the round in progress first." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF WS-BET = 0
        MOVE "Place a bet first." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF WS-BANKROLL < WS-BET
        MOVE "Not enough chips to cover that bet." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    PERFORM PROC-RESET-TABLE
    SUBTRACT WS-BET FROM WS-BANKROLL
    MOVE WS-BET TO WS-STAKE
    MOVE 2 TO WS-HAND-N
    MOVE "D" TO HR-ROLE(1)
    MOVE "P" TO HR-ROLE(2)
    MOVE "A" TO HR-STATUS(1)
    MOVE "A" TO HR-STATUS(2)
    MOVE WS-BET TO HR-BET(2)
    MOVE 2 TO WS-DEAL-TARGET
    PERFORM PROC-DRAW
    MOVE 1 TO WS-DEAL-TARGET
    PERFORM PROC-DRAW
    MOVE 2 TO WS-DEAL-TARGET
    PERFORM PROC-DRAW
    MOVE 1 TO WS-DEAL-TARGET
    PERFORM PROC-DRAW

    EVALUATE TRUE
        WHEN HR-TOTAL(2) = 21
            MOVE "J" TO HR-STATUS(2)
    END-EVALUATE
    EVALUATE TRUE
        WHEN HR-TOTAL(1) = 21
            MOVE "J" TO HR-STATUS(1)
    END-EVALUATE

*> insurance is offered whenever the dealer shows an ace, even when the
*> player already holds blackjack, so even money stays available.
    IF WS-CARD-RANK(HR-CARD(1, 1)) = 1
        MOVE "INSURANCE" TO WS-PHASE
        MOVE "Dealer shows an ace. Insurance up?" TO WS-NOTE
        EXIT PARAGRAPH
    END-IF

    IF HR-STATUS(1) = "J" OR HR-STATUS(2) = "J"
        MOVE "Blackjack!" TO WS-NOTE
        PERFORM PROC-SETTLE
        EXIT PARAGRAPH
    END-IF

    IF WS-CARD-RANK(HR-CARD(1, 1)) >= 10
        PERFORM PROC-PEEK-DEALER
        EXIT PARAGRAPH
    END-IF

    MOVE "PLAYER" TO WS-PHASE
    MOVE "Your move." TO WS-NOTE
    PERFORM PROC-FIND-ACTIVE
    PERFORM PROC-UPDATE-FLAGS.

PROC-RESET-TABLE.
    MOVE 0 TO WS-HAND-N
    MOVE 0 TO WS-ACT-HAND
    MOVE 0 TO WS-STAKE
    MOVE 0 TO WS-INS-BET
    MOVE 0 TO WS-INS-PAID
    MOVE "N" TO WS-INS-TAKEN
    MOVE "N" TO WS-DOUBLE-OK
    MOVE "N" TO WS-HOLE-COUNTED
    MOVE "D" TO HR-ROLE(1)
    MOVE "P" TO HR-ROLE(2)
    PERFORM VARYING WS-J FROM 1 BY 1 UNTIL WS-J > 2
        MOVE "E" TO HR-STATUS(WS-J)
        MOVE "-" TO HR-RESULT(WS-J)
        MOVE "N" TO HR-SOFT(WS-J)
        MOVE 0 TO HR-NCARDS(WS-J)
        MOVE 0 TO HR-TOTAL(WS-J)
        MOVE 0 TO HR-BET(WS-J)
        MOVE 0 TO HR-PAID(WS-J)
    END-PERFORM.

PROC-AFTER-PLAYER-MOVE.
    PERFORM PROC-FIND-ACTIVE
    EVALUATE TRUE
        WHEN WS-ACT-HAND > 0
            MOVE "PLAYER" TO WS-PHASE
            PERFORM PROC-UPDATE-FLAGS
        WHEN OTHER
            PERFORM PROC-DEALER-PLAY
    END-EVALUATE.

PROC-FIND-ACTIVE.
    MOVE 0 TO WS-ACT-HAND
    PERFORM VARYING WS-J FROM 2 BY 1 UNTIL WS-J > WS-HAND-N
        IF HR-STATUS(WS-J) = "A"
            MOVE WS-J TO WS-ACT-HAND
        END-IF
    END-PERFORM.

PROC-UPDATE-FLAGS.
    MOVE "N" TO WS-DOUBLE-OK
    IF WS-ACT-HAND > 0
        IF HR-NCARDS(WS-ACT-HAND) = 2
            IF WS-BANKROLL >= HR-BET(WS-ACT-HAND)
                MOVE "Y" TO WS-DOUBLE-OK
            END-IF
        END-IF
    END-IF.

PROC-PEEK-DEALER.
    IF HR-TOTAL(1) = 21
        MOVE "J" TO HR-STATUS(1)
        MOVE "Dealer has blackjack." TO WS-NOTE
        PERFORM PROC-SETTLE
    ELSE
        IF HR-STATUS(2) = "J"
            MOVE "Blackjack!" TO WS-NOTE
            PERFORM PROC-SETTLE
        ELSE
            MOVE "PLAYER" TO WS-PHASE
            MOVE "Dealer checks - no blackjack. Your move." TO WS-NOTE
            PERFORM PROC-FIND-ACTIVE
            PERFORM PROC-UPDATE-FLAGS
        END-IF
    END-IF.

PROC-DEALER-PLAY.
    MOVE "DEALER" TO WS-PHASE
    MOVE "A" TO HR-STATUS(1)
    PERFORM PROC-COUNT-HOLE
    PERFORM UNTIL HR-TOTAL(1) >= 17
        MOVE 1 TO WS-DEAL-TARGET
        PERFORM PROC-DRAW
    END-PERFORM
    EVALUATE TRUE
        WHEN HR-TOTAL(1) > 21
            MOVE "B" TO HR-STATUS(1)
        WHEN OTHER
            MOVE "S" TO HR-STATUS(1)
    END-EVALUATE
    PERFORM PROC-SETTLE.

PROC-SETTLE.
    PERFORM PROC-COUNT-HOLE
    MOVE "SETTLE" TO WS-PHASE
    MOVE "N" TO WS-DOUBLE-OK
    MOVE 0 TO WS-INS-PAID
    MOVE 0 TO WS-STAKE

    IF WS-INS-TAKEN = "Y" AND HR-TOTAL(1) = 21
        COMPUTE WS-INS-PAID = WS-INS-BET * 3
    END-IF
    COMPUTE WS-BANKROLL ROUNDED = WS-BANKROLL + WS-INS-PAID
    COMPUTE WS-NET = WS-INS-PAID - WS-INS-BET
    MOVE "N" TO WS-INS-TAKEN

    PERFORM VARYING WS-J FROM 2 BY 1 UNTIL WS-J > WS-HAND-N
        MOVE 0 TO HR-PAID(WS-J)
        MOVE "-" TO HR-RESULT(WS-J)
        ADD HR-BET(WS-J) TO WS-STAKE
        EVALUATE TRUE
            WHEN HR-STATUS(WS-J) = "B"
                MOVE "L" TO HR-RESULT(WS-J)
            WHEN HR-TOTAL(1) > 21
                MOVE "W" TO HR-RESULT(WS-J)
                COMPUTE HR-PAID(WS-J) = HR-BET(WS-J) * 2
            WHEN HR-STATUS(WS-J) = "J"
                IF HR-STATUS(1) = "J"
                    MOVE "P" TO HR-RESULT(WS-J)
                    MOVE HR-BET(WS-J) TO HR-PAID(WS-J)
                ELSE
                    MOVE "W" TO HR-RESULT(WS-J)
                    COMPUTE HR-PAID(WS-J) =
                        HR-BET(WS-J) + (HR-BET(WS-J) * 3 / 2)
                END-IF
            WHEN HR-TOTAL(WS-J) > HR-TOTAL(1)
                MOVE "W" TO HR-RESULT(WS-J)
                COMPUTE HR-PAID(WS-J) = HR-BET(WS-J) * 2
            WHEN HR-TOTAL(WS-J) = HR-TOTAL(1)
                MOVE "P" TO HR-RESULT(WS-J)
                MOVE HR-BET(WS-J) TO HR-PAID(WS-J)
            WHEN OTHER
                MOVE "L" TO HR-RESULT(WS-J)
        END-EVALUATE
        COMPUTE WS-NET = WS-NET + HR-PAID(WS-J) - HR-BET(WS-J)
        COMPUTE WS-BANKROLL ROUNDED = WS-BANKROLL + HR-PAID(WS-J)
    END-PERFORM

    EVALUATE TRUE
        WHEN HR-TOTAL(1) > 21
            MOVE "Dealer busts." TO WS-NOTE
        WHEN OTHER
            MOVE HR-TOTAL(1) TO WS-S-ZZ
            MOVE SPACES TO WS-NOTE
            STRING "Dealer stands on " DELIMITED BY SIZE
                   FUNCTION TRIM(WS-S-ZZ) DELIMITED BY SIZE
                   INTO WS-NOTE
    END-EVALUATE

    EVALUATE TRUE
        WHEN WS-NET > 0
            ADD 1 TO ST-WINS
            MOVE "W" TO WS-RESULT-LINE
        WHEN WS-NET = 0
            ADD 1 TO ST-PUSH
            MOVE "P" TO WS-RESULT-LINE
        WHEN OTHER
            ADD 1 TO ST-LOSS
            MOVE "L" TO WS-RESULT-LINE
    END-EVALUATE
    ADD 1 TO ST-ROUND
    COMPUTE ST-NET ROUNDED = ST-NET + WS-NET
    IF WS-BANKROLL > ST-BEST
        MOVE WS-BANKROLL TO ST-BEST
    END-IF
    MOVE "Y" TO ST-DIRTY.

*> ===============================================================
*> shoe management
*> ===============================================================
PROC-SEED-RANDOM.
    MOVE FUNCTION CURRENT-DATE TO WS-DATE-TXT
    MOVE WS-DATE-TXT(7:6) TO WS-SEED-RAW
    COMPUTE WS-SEED = FUNCTION MOD(WS-SEED-RAW, 2147483646) + 1.

PROC-NEXT-RANDOM.
    COMPUTE WS-SEED = FUNCTION MOD(WS-SEED * 16807, 2147483647).

PROC-BUILD-TABLES.
    PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 52
        COMPUTE WS-RANK = FUNCTION INTEGER((WS-I - 1) / 4) + 1
        MOVE WS-RANK TO WS-CARD-RANK(WS-I)
        EVALUATE TRUE
            WHEN WS-RANK = 1
                MOVE 11 TO WS-CARD-VAL(WS-I)
                MOVE -1 TO WS-CARD-DELTA(WS-I)
            WHEN WS-RANK >= 11 AND WS-RANK <= 13
                MOVE 10 TO WS-CARD-VAL(WS-I)
                MOVE -1 TO WS-CARD-DELTA(WS-I)
            WHEN WS-RANK <= 6
                MOVE WS-RANK TO WS-CARD-VAL(WS-I)
                MOVE 1 TO WS-CARD-DELTA(WS-I)
            WHEN OTHER
                MOVE WS-RANK TO WS-CARD-VAL(WS-I)
                MOVE 0 TO WS-CARD-DELTA(WS-I)
        END-EVALUATE
    END-PERFORM.

PROC-SHOE-FILL.
    MOVE 0 TO WS-SHOE-POS
    COMPUTE WS-SHOE-LEN = WS-DECK-NUMBER * 52
    PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > WS-SHOE-LEN
        COMPUTE WS-J = FUNCTION INTEGER((WS-I - 1) / WS-DECK-NUMBER) + 1
        MOVE WS-J TO WS-SHOE(WS-I)
    END-PERFORM
    COMPUTE WS-SHOE-TOP = WS-SHOE-LEN * 75 / 100
    PERFORM VARYING WS-I FROM WS-SHOE-LEN BY -1 UNTIL WS-I < 2
        PERFORM PROC-NEXT-RANDOM
        COMPUTE WS-PICK = FUNCTION MOD(WS-SEED, WS-I) + 1
        MOVE WS-SHOE(WS-I) TO WS-SWAP
        MOVE WS-SHOE(WS-PICK) TO WS-SHOE(WS-I)
        MOVE WS-SWAP TO WS-SHOE(WS-PICK)
    END-PERFORM
    MOVE 0 TO WS-SHOE-POS
    MOVE 0 TO WS-COUNT.

PROC-NEXT-CARD.
    IF WS-SHOE-POS >= WS-SHOE-TOP
        MOVE "Shoe exhausted - reshuffling." TO WS-NOTE
        PERFORM PROC-SHOE-FILL
    END-IF
    ADD 1 TO WS-SHOE-POS
    MOVE WS-SHOE(WS-SHOE-POS) TO WS-CARD.

PROC-DRAW.
*> A hand stores eleven cards. Nothing can reach that many in real play,
*> but the check keeps a stray draw from writing past the table.
    IF WS-DEAL-TARGET < 1 OR WS-DEAL-TARGET > WS-HAND-N
        MOVE "Internal error: bad deal target." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    IF HR-NCARDS(WS-DEAL-TARGET) >= 11
        MOVE "S" TO HR-STATUS(WS-DEAL-TARGET)
        MOVE "No room for another card." TO WS-NOTE
        EXIT PARAGRAPH
    END-IF
    PERFORM PROC-NEXT-CARD
    ADD 1 TO HR-NCARDS(WS-DEAL-TARGET)
    MOVE WS-CARD TO HR-CARD(WS-DEAL-TARGET, HR-NCARDS(WS-DEAL-TARGET))
    IF WS-DEAL-TARGET NOT = WS-DLR-HAND
        ADD WS-CARD-DELTA(WS-CARD) TO WS-COUNT
    ELSE
        IF HR-NCARDS(WS-DEAL-TARGET) NOT = 2
            ADD WS-CARD-DELTA(WS-CARD) TO WS-COUNT
        END-IF
    END-IF
    PERFORM PROC-RECALC-TOTAL.

PROC-RECALC-TOTAL.
    MOVE 0 TO WS-SUM
    MOVE 0 TO WS-ACES
    MOVE "N" TO HR-SOFT(WS-DEAL-TARGET)
    PERFORM VARYING WS-J FROM 1 BY 1 UNTIL WS-J > HR-NCARDS(WS-DEAL-TARGET)
        ADD WS-CARD-VAL(HR-CARD(WS-DEAL-TARGET, WS-J)) TO WS-SUM
        IF WS-CARD-RANK(HR-CARD(WS-DEAL-TARGET, WS-J)) = 1
            ADD 1 TO WS-ACES
        END-IF
    END-PERFORM
    IF WS-ACES > 0 AND WS-SUM <= 21
        MOVE "Y" TO HR-SOFT(WS-DEAL-TARGET)
    END-IF
    PERFORM UNTIL WS-SUM <= 21 OR WS-ACES = 0
        SUBTRACT 10 FROM WS-SUM
        SUBTRACT 1 FROM WS-ACES
        MOVE "N" TO HR-SOFT(WS-DEAL-TARGET)
    END-PERFORM
    MOVE WS-SUM TO HR-TOTAL(WS-DEAL-TARGET).

*> The dealer's second card is dealt face down and is deliberately left
*> out of the running count until it is revealed. This paragraph adds it
*> exactly once, the first time the hole card is turned over.
PROC-COUNT-HOLE.
    IF WS-HOLE-COUNTED = "N" AND HR-NCARDS(WS-DLR-HAND) >= 2
        ADD WS-CARD-DELTA(HR-CARD(WS-DLR-HAND, 2)) TO WS-COUNT
        MOVE "Y" TO WS-HOLE-COUNTED
    END-IF.

*> ===============================================================
*> statistics file
*> ===============================================================
PROC-LOAD-STATS.
    MOVE ZERO TO WS-STAT-OK
    OPEN INPUT STAT-FILE
    IF WS-FILE-STAT = "00"
        READ STAT-FILE
            AT END
                MOVE "N" TO WS-FILE-STAT
            NOT AT END
                PERFORM PROC-STAT-RECORD-CHECK
                IF WS-STAT-OK = 1
                    COMPUTE ST-WINS = FUNCTION NUMVAL(SR-AREA(1:6))
                    COMPUTE ST-PUSH = FUNCTION NUMVAL(SR-AREA(7:6))
                    COMPUTE ST-LOSS = FUNCTION NUMVAL(SR-AREA(13:6))
                    COMPUTE ST-ROUND = FUNCTION NUMVAL(SR-AREA(19:6))
                    IF SR-AREA(25:1) = "-"
                        COMPUTE ST-NET = 0 - FUNCTION NUMVAL(SR-AREA(26:9))
                    ELSE
                        COMPUTE ST-NET = FUNCTION NUMVAL(SR-AREA(26:9))
                    END-IF
                    IF SR-AREA(35:1) = "-"
                        COMPUTE ST-BEST = 0 - FUNCTION NUMVAL(SR-AREA(36:9))
                    ELSE
                        COMPUTE ST-BEST = FUNCTION NUMVAL(SR-AREA(36:9))
                    END-IF
                    MOVE "Y" TO ST-DIRTY
                END-IF
        END-READ
    END-IF
    CLOSE STAT-FILE.

*> WS-STAT-OK is 1 when every byte of the statistics record holds what it
*> should. A file that fails this check is discarded and the counters keep
*> their zero values instead of being polluted by uninitialised storage.
PROC-STAT-RECORD-CHECK.
    MOVE 1 TO WS-STAT-OK
    PERFORM VARYING WS-J FROM 1 BY 1 UNTIL WS-J > 44
        IF WS-J = 25 OR WS-J = 35
            IF SR-AREA(WS-J:1) NOT = "+"
                IF SR-AREA(WS-J:1) NOT = "-"
                    MOVE 0 TO WS-STAT-OK
                END-IF
            END-IF
        ELSE
            IF SR-AREA(WS-J:1) < "0"
                MOVE 0 TO WS-STAT-OK
            END-IF
            IF SR-AREA(WS-J:1) > "9"
                MOVE 0 TO WS-STAT-OK
            END-IF
        END-IF
    END-PERFORM
*> nothing may follow the 44 characters of the record
    PERFORM VARYING WS-J FROM 45 BY 1 UNTIL WS-J > 200
        IF SR-AREA(WS-J:1) NOT = SPACE
            MOVE 0 TO WS-STAT-OK
        END-IF
    END-PERFORM.

PROC-SAVE-STATS.
    IF ST-DIRTY NOT = "Y"
        EXIT PARAGRAPH
    END-IF
    MOVE SPACES TO WS-TREC
    MOVE ST-WINS  TO WS-T-WINS
    MOVE ST-PUSH  TO WS-T-PUSH
    MOVE ST-LOSS  TO WS-T-LOSS
    MOVE ST-ROUND TO WS-T-ROUND
    IF ST-NET < ZERO
        MOVE "-" TO WS-T-NSIGN
        COMPUTE WS-N9 = 0 - ST-NET
    ELSE
        MOVE "+" TO WS-T-NSIGN
        MOVE ST-NET TO WS-N9
    END-IF
    MOVE WS-N9 TO WS-T-NET
    IF ST-BEST < ZERO
        MOVE "-" TO WS-T-BSIGN
        COMPUTE WS-N9 = 0 - ST-BEST
    ELSE
        MOVE "+" TO WS-T-BSIGN
        MOVE ST-BEST TO WS-N9
    END-IF
    MOVE WS-N9 TO WS-T-BEST
    MOVE WS-TREC TO SR-AREA
    OPEN OUTPUT STAT-FILE
    IF WS-FILE-STAT NOT = "00"
        CLOSE STAT-FILE
        EXIT PARAGRAPH
    END-IF
    WRITE STAT-RECORD
    CLOSE STAT-FILE
    MOVE "N" TO ST-DIRTY.

PROC-CARD-TO-TEXT.
    MOVE SPACES TO WS-CARD-TOK
    IF WS-FACE-DOWN = "Y"
        MOVE "~" TO WS-CARD-TOK(1:1)
    END-IF
    MOVE WS-CARD-RANK(WS-CARD) TO WS-RANK
    COMPUTE WS-SUIT = FUNCTION MOD(WS-CARD - 1, 4) + 1
    MOVE WS-RANK-CHARS(WS-RANK:1) TO WS-CARD-TOK(2:1)
    MOVE WS-SUIT-CHARS(WS-SUIT:1) TO WS-CARD-TOK(3:1).

PROC-COUNT-UPDATE.
    COMPUTE WS-DECKS-LEFT ROUNDED =
        1 + ((WS-SHOE-TOP - WS-SHOE-POS) / 52)
    IF WS-DECKS-LEFT < 1
        MOVE 1 TO WS-DECKS-LEFT
    END-IF
    COMPUTE WS-TRUE-COUNT ROUNDED = WS-COUNT / WS-DECKS-LEFT.

*> ===============================================================
*> state emission - one record per line, terminated by END
*> ===============================================================
PROC-EMIT-STATE.
    MOVE WS-PHASE TO WS-S-PHASE
    DISPLAY "STATE" " " WS-S-PHASE

    MOVE WS-BANKROLL TO WS-S-N2
    MOVE WS-BET      TO WS-S-N3
    MOVE WS-NET      TO WS-S-S1
    MOVE ST-NET      TO WS-S-S2
    MOVE WS-RESULT-LINE TO WS-S-C1
    DISPLAY "MONEY" " " WS-S-N2 " " WS-S-N3 " " WS-S-S1 " "
        WS-S-S2 " " WS-S-C1

    PERFORM PROC-COUNT-UPDATE
    MOVE WS-COUNT      TO WS-S-S1
    MOVE WS-TRUE-COUNT TO WS-S-S2
    MOVE WS-DECKS-LEFT TO WS-S-N1
    DISPLAY "RC" " " WS-S-S1 " " WS-S-S2 " " WS-S-N1

    MOVE WS-HAND-N   TO WS-S-N1
    MOVE WS-ACT-HAND TO WS-S-N2
    DISPLAY "HANDS" " " WS-S-N1 " " WS-S-N2

    PERFORM VARYING WS-J FROM 1 BY 1 UNTIL WS-J > WS-HAND-N
        MOVE WS-J            TO WS-S-IDX
        MOVE HR-ROLE(WS-J)   TO WS-S-C1
        MOVE HR-STATUS(WS-J) TO WS-S-C2
        MOVE HR-TOTAL(WS-J)  TO WS-S-N1
        MOVE HR-SOFT(WS-J)   TO WS-S-C3
        MOVE HR-RESULT(WS-J) TO WS-S-C4
        MOVE HR-BET(WS-J)    TO WS-S-N2
        MOVE HR-PAID(WS-J)   TO WS-S-S1
        MOVE HR-NCARDS(WS-J) TO WS-S-N3
        MOVE SPACES TO WS-CARD-ROW
        MOVE 1 TO WS-CARD-CUR
        PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > HR-NCARDS(WS-J)
            MOVE "N" TO WS-FACE-DOWN
            IF WS-J = WS-DLR-HAND AND WS-I = 2
                IF WS-PHASE = "PLAYER" OR WS-PHASE = "INSURANCE"
                    MOVE "Y" TO WS-FACE-DOWN
                END-IF
            END-IF
            MOVE HR-CARD(WS-J, WS-I) TO WS-CARD
            PERFORM PROC-CARD-TO-TEXT
            MOVE SPACES TO WS-CARD-SLOT
            MOVE WS-CARD-TOK TO WS-CARD-SLOT(1:3)
            MOVE WS-CARD-SLOT TO WS-CARD-ROW(WS-CARD-CUR:4)
            ADD 4 TO WS-CARD-CUR
        END-PERFORM
        DISPLAY "HAND" " " WS-S-IDX " " WS-S-C1 " " WS-S-C2 " "
            WS-S-N1 " " WS-S-C3 " " WS-S-C4 " " WS-S-N2 " " WS-S-S1 " "
            WS-S-N3 " " WS-CARD-ROW
    END-PERFORM

    MOVE WS-DOUBLE-OK TO WS-S-C1
    MOVE WS-INS-TAKEN TO WS-S-C2
    DISPLAY "FLAGS" " " WS-S-C1 " " WS-S-C2

    MOVE ST-WINS  TO WS-S-N1
    MOVE ST-PUSH  TO WS-S-N2
    MOVE ST-LOSS  TO WS-S-N3
    MOVE ST-ROUND TO WS-S-N4
    MOVE ST-NET   TO WS-S-S1
    MOVE ST-BEST  TO WS-S-S2
    DISPLAY "STATS" " " WS-S-N1 " " WS-S-N2 " " WS-S-N3 " "
        WS-S-N4 " " WS-S-S1 " " WS-S-S2

    DISPLAY "NOTE" " " WS-NOTE

    DISPLAY "END".

END PROGRAM BLACKJACK.
