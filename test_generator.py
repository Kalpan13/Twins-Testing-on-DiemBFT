import copy
from os import closerange
import random
import json
import time
import sys

def generate_replicas(nreplicas):
    current_node_id = 'A'
    replicas = []
    for i in range(nreplicas):
        replicas.append(current_node_id)
        current_node_id = (chr)(ord(current_node_id) + 1)
    return replicas

def generate_twins(nreplicas):
    current_node_id = 'A'
    twins = []
    for i in range(nreplicas):
        twins.append(current_node_id+'\'')
        current_node_id = (chr)(ord(current_node_id) + 1)
    return twins

def generate_partition_configs(nodes, no_of_partitions):
    if no_of_partitions == 1:
        return [[nodes]]

    if len(nodes) == no_of_partitions:
        return [[[node] for node in nodes]]

    partition_config_without_current_node = generate_partition_configs(nodes[:-1], no_of_partitions)
    all_possible_partitions = generate_partition_configs(nodes[:-1], no_of_partitions - 1)

    for i in range(len(all_possible_partitions)):
        all_possible_partitions[i].append([nodes[-1]])

    for i in range(len(partition_config_without_current_node)):
        for j in range(len(partition_config_without_current_node[i])):
            current_partition = copy.deepcopy(partition_config_without_current_node[i])
            current_partition[j].append(nodes[-1])
            all_possible_partitions.append(current_partition)

    return all_possible_partitions

def isProgressivePartition(partition, replicas):
    
    f = (len(replicas) - 1) // 3

    distinct_replicas_in_partition = len(partition)
    for replica in replicas:
        if replica in partition and (replica+'\'') in partition:
            # For all the replicas, A and its twin A' are considered a single replica
            distinct_replicas_in_partition = distinct_replicas_in_partition - 1
        
    if distinct_replicas_in_partition >= 2*f+1:
        return True
    return False

def isProgressivePartitionConfig(partition_config, replicas):

    for partition in partition_config:
        if isProgressivePartition(partition, replicas) == True:
            return True
    return False

def generate_progressive_partition_configs_with_leaders(partition_configs, replicas, twins, deterministic):
    partition_configs_with_leader = []
    partition_config_with_leader = {}
    first_round_potential_leaders = []

    for partition in partition_configs[0]:
        if isProgressivePartition(partition, replicas) == True:
            first_round_potential_leaders = partition
            break
        
    first_round_potential_leaders = list(set(first_round_potential_leaders) - set(twins))

    first_round_potential_leaders.sort()
    if deterministic == False:
        random.shuffle(first_round_potential_leaders)
    
    partition_config_with_leader["leader"] = [first_round_potential_leaders[0]]
    
    corresponding_twin = first_round_potential_leaders[0] + '\''
    if corresponding_twin in twins:       
        partition_config_with_leader["leader"].append(corresponding_twin)

    partition_config_with_leader['partitions'] = partition_configs[0]
    partition_configs_with_leader.append(partition_config_with_leader)
    previous_potential_leaders = first_round_potential_leaders
    
    for current_partition_config_index in range(1,len(partition_configs)):
        potential_leaders = []
        
        for partition in partition_configs[current_partition_config_index]:
            if isProgressivePartition(partition, replicas) == True:
                potential_leaders = partition
                break

        potential_leaders = list(set(potential_leaders) - set(twins))
        common_potential_leaders = list(set(potential_leaders) & set(previous_potential_leaders))
        
        partition_config_with_leader = {}
        common_potential_leaders.sort()

        if deterministic == False:
            random.shuffle(common_potential_leaders)
        
        partition_config_with_leader["leader"] = [common_potential_leaders[0]]
        
        corresponding_twin = common_potential_leaders[0] + '\''
        if corresponding_twin in twins:       
            partition_config_with_leader["leader"].append(corresponding_twin)
        
        partition_config_with_leader["partitions"] = partition_configs[current_partition_config_index]
        partition_configs_with_leader.append(partition_config_with_leader)

        previous_potential_leaders = potential_leaders

    return partition_configs_with_leader

def generate_round_configs(nreplicas, ntwins, npartitions, nrounds, deterministic, onlyfaultyleaders, maxpartitionsConfigs, onlyProgressivePartitionConfigs, message_types_to_drop, message_type_drop_probability, timeout_msg_drop_cnt):

    replicas = generate_replicas(nreplicas)
    twins = generate_twins(ntwins)

    servers = replicas + twins

    partition_configs =  generate_partition_configs(servers, npartitions)

    # Filtering out partition configurations that can never progress i.e. no partition contains at least 2f+1 replicas
    if onlyProgressivePartitionConfigs == True:
        for partition_config in partition_configs:
            if isProgressivePartitionConfig(partition_config, replicas) == False:
                partition_configs.remove(partition_config)

    # If an invalid configuration is passed then empty dictionary is returned
    if(len(partition_configs) == 0):
        return {}

    # Support for enumeration order for step 1 i.e whether the configuration should be generated deterministically or randomly
    if deterministic == False:
        random.shuffle(partition_configs)

    # Support for enumeration limits after step 1 as mentioned in Twins paper
    if(len(partition_configs) > maxpartitionsConfigs):
        partition_configs = partition_configs[:maxpartitionsConfigs]

    partition_configs_with_leader = []
    if onlyProgressivePartitionConfigs == False:
        for partition_config in partition_configs:
                
                for replica in replicas:
                    leaders = [replica]

                    # Providing an option whether only faulty replicas can become leader or not
                    corresponding_twin = replica + '\''
                    if corresponding_twin not in twins:
                        if onlyfaultyleaders == True:
                            continue
                    else:
                        leaders.append(corresponding_twin)
                            
                    partition_config_with_leader = {}
                    partition_config_with_leader['leader'] = leaders
                    partition_config_with_leader['partitions'] = partition_config
                    partition_configs_with_leader.append(partition_config_with_leader)            
    else:
        partition_configs_with_leader = generate_progressive_partition_configs_with_leaders(partition_configs, replicas, twins, deterministic)

    round_configs = {}
    no_of_partition_configs = len(partition_configs_with_leader)

    # Could not generate any valid configuration because of invlaid input and thus, returning empty JSON
    # Such a scenario could occurr if there are 5 servers (twins + replicas) and no of partitions requested are 6
    if no_of_partition_configs == 0:
        return {}

    # Support for type based message loss
    if len(message_types_to_drop) > 0:
        for partition_config_index in range(no_of_partition_configs):
            drop_probability =  random.random()
            if drop_probability < message_type_drop_probability:
                partition_configs_with_leader[partition_config_index]["MsgType"] = random.choice(message_types_to_drop)


    # Enumeration limits after step 3 mentioned in section 4.2 of Twins paper
    for current_round in range(1, nrounds+1):
    
        if deterministic == True or onlyProgressivePartitionConfigs == True:
            round_configs[current_round] = partition_configs_with_leader[current_round % no_of_partition_configs]
        else:
            leader_partition_config_selected = random.choice(partition_configs_with_leader)
            round_configs[current_round] = leader_partition_config_selected

    testcase_config={}
    testcase_config['no_of_replicas'] = len(replicas)
    testcase_config['no_of_twins'] = len(twins)
    testcase_config['no_of_rounds'] = nrounds
    testcase_config['round_configs'] = round_configs
    testcase_config['timeout_msg_drop_cnt'] = timeout_msg_drop_cnt
    return testcase_config

time1 = time.time()
testcase_config = generate_round_configs(nreplicas=4, ntwins=1, npartitions=2, nrounds=7, deterministic=False, onlyfaultyleaders=True, maxpartitionsConfigs=6, onlyProgressivePartitionConfigs=True,message_types_to_drop=["Proposal", "Vote"], message_type_drop_probability=0.7, timeout_msg_drop_cnt=3)
time2 = time.time()
print("Time taken", time2 - time1)

with open(sys.argv[1], 'w') as f:
    json.dump(testcase_config, f)
















    

