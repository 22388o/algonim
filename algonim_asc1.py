from algosdk import logic, transaction

from pyteal import *


def asc1_sink_teal(algod_client,
                   asa_pieces_id,
                   player_alice,
                   player_bob):
    '''HELP asc1_sink_teal:
        (AlgodClient, int, str, str) - Returns AlgoNim ASC1 Sink raw TEAL
    '''
    # AlgoNim ASC1 Sink controls the following conditions:
    # 1. AlgoNim ASA Pieces Opt-In
    # 2. Empty Sink: Alice or Bob remove all the AlgoNim ASA Pieces total
    # supply from the Sink as winning proof.
    asa_pieces = algod_client.asset_info(asa_pieces_id)
    asa_pieces_id = Int(asa_pieces_id)
    asa_pieces_total = Int(asa_pieces['total'])
    addr_alice = Addr(player_alice)
    addr_bob = Addr(player_bob)

    # ASC1 Constants:
    tmpl_fee = Int(1000)

    # ASC1 Logic:
    # 1. AlgoNim ASA Pieces Opt-In
    asa_pieces_opt_in = And(Global.group_size() == Int(1),
                            Txn.group_index() == Int(0),
                            Txn.type_enum() == Int(4),
                            Txn.fee() <= tmpl_fee,
                            Txn.xfer_asset() == asa_pieces_id,
                            Txn.asset_amount() == Int(0),
                            Txn.asset_close_to() == Global.zero_address())

    # 2. Empty Sink
    empty_sink_alice = And(Global.group_size() == Int(4),
                           Txn.group_index() == Int(2),
                           Txn.type_enum() == Int(4),
                           Txn.fee() <= tmpl_fee,
                           Txn.xfer_asset() == asa_pieces_id,
                           Txn.asset_amount() == asa_pieces_total,
                           Txn.asset_receiver() == addr_alice,
                           Txn.asset_close_to() == Global.zero_address())

    empty_sink_bob = And(Global.group_size() == Int(4),
                         Txn.group_index() == Int(2),
                         Txn.type_enum() == Int(4),
                         Txn.fee() <= tmpl_fee,
                         Txn.xfer_asset() == asa_pieces_id,
                         Txn.asset_amount() == asa_pieces_total,
                         Txn.asset_receiver() == addr_bob,
                         Txn.asset_close_to() == Global.zero_address())

    empty_sink = Or(empty_sink_alice, empty_sink_bob)
    return Or(asa_pieces_opt_in, empty_sink)


def asc1_game_table_teal(algod_client,
                         asa_pieces_id,
                         asa_pieces_max_remove,
                         asa_turn_id,
                         player_alice,
                         player_bob,
                         sink):
    '''HELP asc1_game_table_teal:
        (AlgodClient, int, int, int, int, str, str, str) - Returns AlgoNim ASC1
        Game Table raw TEAL
    '''
    # AlgoNim ASC1 Game Table controls the following conditions:
    # 1. Dealer - Funding Game Table with AlgoNim ASA Pieces
    # 2. Play Turn - Player correctly removes ASA Pieces from the Game Table
    asa_pieces = algod_client.asset_info(asa_pieces_id)
    asa_pieces_id = Int(asa_pieces_id)
    asa_pieces_total = Int(asa_pieces['total'])
    asa_pieces_max_remove = Int(asa_pieces_max_remove)
    asa_turn_id = Int(asa_turn_id)
    addr_alice = Addr(player_alice)
    addr_bob = Addr(player_bob)
    addr_sink = Addr(sink)

    # ASC1 Constants:
    tmpl_fee = Int(1000)

    # ASC1 Logic:
    # 1. Dealer
    asa_pieces_opt_in = And(Global.group_size() == Int(2),
                            Txn.group_index() == Int(0),
                            Gtxn.type_enum(0) == Int(4),
                            Gtxn.fee(0) <= tmpl_fee,
                            Gtxn.xfer_asset(0) == asa_pieces_id,
                            Gtxn.asset_amount(0) == Int(0),
                            Gtxn.asset_close_to(0) == Global.zero_address())

    game_table_setup = And(Global.group_size() == Int(2),
                           Gtxn.type_enum(1) == Int(4),
                           Gtxn.fee(1) <= tmpl_fee,
                           Gtxn.xfer_asset(1) == asa_pieces_id,
                           Gtxn.asset_amount(1) == asa_pieces_total,
                           Gtxn.sender(1) == addr_alice,
                           Gtxn.asset_close_to(1) == Global.zero_address())

    dealer = And(asa_pieces_opt_in, game_table_setup)

    # 2. Play Turn
    play_turn_type = Or(Global.group_size() == Int(2),
                        Global.group_size() == Int(4))

    change_turn_alice_to_bob = And(play_turn_type,
                                   Gtxn.type_enum(0) == Int(4),
                                   Gtxn.fee(0) <= tmpl_fee,
                                   Gtxn.xfer_asset(0) == asa_turn_id,
                                   Gtxn.asset_amount(0) == Int(1),
                                   Gtxn.sender(0) == addr_alice,
                                   Gtxn.asset_receiver(0) == addr_bob,
                                   Gtxn.asset_close_to(
                                       0) == Global.zero_address())

    change_turn_bob_to_alice = And(play_turn_type,
                                   Gtxn.type_enum(0) == Int(4),
                                   Gtxn.fee(0) <= tmpl_fee,
                                   Gtxn.xfer_asset(0) == asa_turn_id,
                                   Gtxn.asset_amount(0) == Int(1),
                                   Gtxn.sender(0) == addr_bob,
                                   Gtxn.asset_receiver(0) == addr_alice,
                                   Gtxn.asset_close_to(
                                       0) == Global.zero_address())

    change_turn = Or(change_turn_alice_to_bob, change_turn_bob_to_alice)

    remove_asa_pieces = And(play_turn_type,
                            Txn.group_index() == Int(1),
                            Gtxn.type_enum(1) == Int(4),
                            Gtxn.fee(1) <= tmpl_fee,
                            Gtxn.xfer_asset(1) == asa_pieces_id,
                            Gtxn.asset_amount(1) >= Int(1),
                            Gtxn.asset_amount(1) <= asa_pieces_max_remove,
                            Gtxn.asset_receiver(1) == addr_sink,
                            Gtxn.asset_close_to(1) == Global.zero_address())

    play_turn = And(change_turn, remove_asa_pieces)
    return Or(dealer, play_turn)


def asc1_bet_escrow_teal(algod_client,
                         asa_pieces_id,
                         asa_turn_id,
                         addr_escrow_owner,
                         addr_adversary_player,
                         sink,
                         game_table,
                         match_hours_timeout):
    '''HELP asc1_sink_raw_teal:
        (AlgodClient, int, int, str, str, str, str, float) - Returns AlgoNim
        ASC1 Bet Escrow raw TEAL
    '''
    # AlgoNim Bet Escrow controls the following conditions:
    # 1. Opponent wins
    # 2. Bet escrow expires
    asa_pieces = algod_client.asset_info(asa_pieces_id)
    asa_pieces_id = Int(asa_pieces_id)
    asa_pieces_total = Int(asa_pieces['total'])
    asa_turn_id = Int(asa_turn_id)
    addr_owner = Addr(addr_escrow_owner)
    addr_adversary = Addr(addr_adversary_player)
    addr_sink = Addr(sink)
    addr_game_table = Addr(game_table)

    # Blockchain Parameters
    blockchain_params = algod_client.suggested_params()
    first_valid = blockchain_params.get("lastRound")

    # AlgoNim Bet Escrow expiration
    match_blocks_duration = int(match_hours_timeout * 3600 // 5)
    bet_escrow_expiry_block = first_valid + match_blocks_duration
    print("AlgoNim Bet Escrows Expiry block:", bet_escrow_expiry_block)
    bet_escrow_expiry_round = Int(bet_escrow_expiry_block)

    # ASC1 Constants:
    tmpl_fee = Int(1000)

    # ASC1 Logic:
    # 1. Opponent wins
    change_turn = And(Global.group_size() == Int(4),
                      Gtxn.type_enum(0) == Int(4),
                      Gtxn.fee(0) <= tmpl_fee,
                      Gtxn.xfer_asset(0) == asa_turn_id,
                      Gtxn.asset_amount(0) == Int(1),
                      Gtxn.sender(0) == addr_adversary,
                      Gtxn.asset_receiver(0) == addr_owner,
                      Gtxn.asset_close_to(0) == Global.zero_address())

    last_move = And(Global.group_size() == Int(4),
                    Gtxn.type_enum(1) == Int(4),
                    Gtxn.fee(1) <= tmpl_fee,
                    Gtxn.xfer_asset(1) == asa_pieces_id,
                    Gtxn.sender(1) == addr_game_table,
                    Gtxn.asset_receiver(1) == addr_sink,
                    Gtxn.asset_close_to(1) == Global.zero_address())

    winner_proof = And(Global.group_size() == Int(4),
                       Gtxn.type_enum(2) == Int(4),
                       Gtxn.fee(2) <= tmpl_fee,
                       Gtxn.xfer_asset(2) == asa_pieces_id,
                       Gtxn.sender(2) == addr_sink,
                       Gtxn.asset_receiver(2) == addr_adversary,
                       Gtxn.asset_amount(2) == asa_pieces_total,
                       Gtxn.asset_close_to(2) == Global.zero_address())

    collect_reward = And(Global.group_size() == Int(4),
                         Txn.group_index() == Int(3),
                         Gtxn.type_enum(3) == Int(1),
                         Gtxn.fee(3) <= tmpl_fee,
                         Gtxn.receiver(3) == addr_adversary,
                         Gtxn.amount(3) == Int(0),
                         Gtxn.close_remainder_to(3) == addr_adversary)

    win = And(change_turn, last_move, winner_proof, collect_reward)

    # 2. Bet Escrow Timeout
    bet_escrow_timeout = And(Global.group_size() == Int(1),
                             Txn.group_index() == Int(0),
                             Txn.type_enum() == Int(1),
                             Txn.fee() <= tmpl_fee,
                             Txn.receiver() == addr_owner,
                             Txn.amount() == Int(0),
                             Txn.close_remainder_to() == addr_owner,
                             Txn.first_valid() > bet_escrow_expiry_round)

    # 3. Close Bet Escrow
    close_bet_escrow = And(
        Cond([Global.group_size() == Int(4), win],
             [Global.group_size() == Int(1), bet_escrow_timeout]),
        Int(1) == Int(1))
    return close_bet_escrow, bet_escrow_expiry_block


def compile_raw_teal(asc1_source, new_asc1_fname):
    '''HELP compile_raw_teal:
        (PyTealObj, str) - Returns ASC1 Contract Account and LogicSig.
        GOAL must be in your PATH, if not so from the CLI enter:
        export PATH=/path/to/node:$PATH
    '''

    asc1_teal_fname = new_asc1_fname + ".teal"
    with open(asc1_teal_fname, "w+") as f:
        f.write(asc1_source.teal())
    asc1_tealc_fname = new_asc1_fname + ".tealc"
    stdout, stderr = execute(["goal", "clerk", "compile", "-o",
                              asc1_tealc_fname, asc1_teal_fname])
    if stderr != "":
        print(stderr)
        raise
    elif len(stdout) < 59:
        print("Error in compile TEAL")
        raise

    with open(asc1_tealc_fname, "rb") as f:
        asc1_bytes = f.read()
    asc1_lsig = transaction.LogicSig(asc1_bytes)
    addr_asc1 = logic.address(asc1_bytes)
    return asc1_lsig, addr_asc1
