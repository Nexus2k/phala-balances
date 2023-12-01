from substrateinterface import SubstrateInterface, Keypair
from substrateinterface.exceptions import SubstrateRequestException

import argparse
import json
import pandas as pd
import ast


CLI=argparse.ArgumentParser()
CLI.add_argument(
  "--list",
  nargs="*",
  type=str,
  default=[],
)

try:
    print("Connecting to substrate node...")
    substrate = SubstrateInterface(
        url="wss://khala-api.phala.network/ws"
    )
except ConnectionRefusedError:
    print("⚠️ Remote RPC server didn't respond")
    exit()

chain_decimals = substrate.token_decimals

# Update with your pool id's
args = CLI.parse_args()
total = 0
for address in args.list:
    print("Processing Address %s..." % address)
    addr_info = substrate.query(
        module='PhalaWrappedBalances',
        storage_function='StakerAccounts',
        params=[address]
    )
    invest_pools = ast.literal_eval(str(addr_info))
    share_price = {}
    for pool_id, _ in invest_pools["invest_pools"]:
        pool_info_string = substrate.query(
            module='PhalaBasePool',
            storage_function='Pools',
            params=[int(pool_id)]
        )
        pool_info = json.loads(str(pool_info_string).replace("'","\""))
        if "StakePool" in pool_info:
            continue
        share_price[int(pool_id)] = int(pool_info["Vault"]["last_share_price_checkpoint"]) / 10**chain_decimals
    for pool_cid in invest_pools["invest_pools"]:
        nft_info = substrate.query_map(
            module='Uniques',
            storage_function='Account',
            params=[address,pool_cid[1]],
            max_results=10
        )
        for nft_account, info in nft_info:
            nft_details = substrate.query_map(
                module='RmrkCore',
                storage_function='Properties',
                params=[pool_cid[1],nft_account],
                max_results=10
            )
            desc = ""
            balance = 0
            do_print = False
            for nft_data_field, nft_data in nft_details:
                key = str(nft_data_field)
                value = str(nft_data)
                if key == "description":
                    desc = value
                if key == "stake-info":
                    if value == "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00":
                        balance = 0
                    else:
                        balance = substrate.decode_scale('u128', value) / 10**chain_decimals
                        balance = balance * share_price.get(pool_cid[0], 1)
                        total += balance
                        do_print = True
            if do_print:
                print("%s: %.2f PHA" % (desc or pool_cid[0], balance))
print("Total: %.2f PHA" % (total))