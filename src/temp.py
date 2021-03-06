import os
import shutil
import sys
import json
sys.path.append('../config')

from client import Client
from config import configs
from cryptography import Cryptography
from validator import ValidatorFI
from network_playground import NetworkPlayground

class RunDiemBFT(process):

    def setup(config, config_id):
        self.nvalidators = int(config['nvalidators'])
        self.nclients = int(config['nclients'])
        self.nfaulty = int(config['nfaulty'])
        self.config = config

    def run():

        twin_config = {}
        with open("../twins_config.json") as f:
            twin_configs = json.load(f)
            twin_config = twin_configs[0]
        
        no_of_twins = twin_config["no_of_twins"]
        no_of_rounds = twin_config["no_of_rounds"]
        no_of_replicas = twin_config["no_of_replicas"]

        private_keys_validators = {}
        public_keys_validators = {}
        private_keys_clients = {}
        public_keys_clients = {}

        os.makedirs('../logs/config' + str(config_id))
        os.makedirs('../ledgers/config' + str(config_id))
        
        
        validators = new(ValidatorFI, num=no_of_replicas)
        clients = new(Client, num=nclients)
        nw_playground = new(NetworkPlayground, num=1)

        #TODO : Add twins
        parsed_config = parse_config(twin_config, validators)
        
        for v in validators:
            private_key, public_key = Cryptography.generate_key()
            private_keys_validators[v] = private_key
            public_keys_validators[v] = public_key

        for c in clients:
            private_key, public_key = Cryptography.generate_key()
            private_keys_clients[c] = private_key
            public_keys_clients[c] = public_key

        setup(nw_playground, (list(validators), config_id, parsed_config))

        for i, v in enumerate(validators):
            setup({v}, (self.config, config_id, i, list(validators), list(clients),
                        private_keys_validators[v], public_keys_validators, public_keys_clients, nw_playground, parsed_config))

        for i, c in enumerate(clients):
            setup({c}, (self.config, config_id, i, list(validators),
                        private_keys_clients[c], public_keys_validators))

        start(nw_playground)
        start(validators)
        start(clients)

        await(each(c in clients, has=received(('Done',), from_=c)))
        output("All clients done, informing all validators.", config_id)
        send(('Done',), to=validators)
        send(('Done',), to=nw_playground)

    def parse_config(config, validators):
        parsed_config = {}
        validators_list = list(validators)
        parsed_config["no_of_twins"] = config["no_of_twins"]
        parsed_config["no_of_rounds"] = config["no_of_rounds"]
        parsed_config["no_of_replicas"] = config["no_of_replicas"]
        parsed_config["round_configs"] = {}

        for round_num in config["round_configs"]:
            parsed_partitions = []
            for partition in config["round_configs"][round_num]["partitions"]:
                parsed_partition = []
                for process in partition:
                    parsed_partition.append(validators_list[ord(process)-ord('A')])

                parsed_partitions.append(parsed_partition)

            leader = config["round_configs"][round_num]["leader"][0]
            parsed_leader = validators_list[ord(leader)-ord('A')]

            parsed_config["round_configs"][int(round_num)] = {"leader": parsed_leader, "partitions": parsed_partitions}
        
        return parsed_config

                
def is_config_valid(config):
    if int(config['nvalidators']) < (3 * int(config['nfaulty']) + 1):
        print(
            "Number of validators should be more than thrice of number of faulty validators.")
        return False
    if (int(config['nfaulty']) > int(config['exclude_size'])) or (int(config['exclude_size']) > 2 * int(config['nfaulty'])):
        print(
            "Exlude size should be between nfaulty and 2*nfaulty")
        return False
    return True


def main():

    if os.path.exists('../logs/') and os.path.isdir('../logs/'):
        shutil.rmtree('../logs/')

    if os.path.exists('../ledgers/') and os.path.isdir('../ledgers/'):
        shutil.rmtree('../ledgers/')

    config_id = 0
    for config in configs:
        # if not is_config_valid(config):
        # output("The provided config", config,
        #         "is not valid. Skipping this config.")
        # continue
        p = new(RunDiemBFT)
        setup(p, (config, config_id))
        start(p)
        config_id += 1