import copy
from os import closerange
import random
import json

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


def isProgressivePartitionConfig(partition_config, replicas):

    f = (len(replicas) - 1) // 3

    for partition in partition_config:
        distinct_replicas_in_partition = len(partition)
        for replica in replicas:
            if replica in partition and (replica+'\'') in partition:
                distinct_replicas_in_partition = distinct_replicas_in_partition - 1
        
        if distinct_replicas_in_partition >= 2*f+1:
            return True

    return False

# partitions = generate_partition_configs(['A','B','C','D','A\''],2)


# for partition in partitions:
#     print(partition, isProgressivePartitionConfig(partition, ['A', 'B', 'C', 'D']))

# selected_partitions = random.sample(partitions, 5)

# for selected_partition in selected_partitions:
#     print(selected_partition)

def generate_round_configs(nreplicas, ntwins, npartitions, nrounds, deterministic, onlyfaultyleaders, maxpartitionsConfigs, onlyProgressivePartitionConfigs):

    replicas = generate_replicas(nreplicas)
    twins = generate_twins(ntwins)

    servers = replicas + twins

    partition_configs =  generate_partition_configs(servers, npartitions)

    # Filtering out partition configurations that can never progress
    if onlyProgressivePartitionConfigs == True:
        for partition_config in partition_configs:
            if isProgressivePartitionConfig(partition_config, replicas) == False:
                partition_configs.remove(partition_config)

    # Support for enumeration order for step 1
    if deterministic == False:
        random.shuffle(partition_configs)

    # Support for enumeration limits after step 1 as mentioned in Twins paper
    if(len(partition_configs) > maxpartitionsConfigs):
        partition_configs = partition_configs[:maxpartitionsConfigs]

    partition_configs_with_leader = []

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

    round_configs = {}
    no_of_partition_configs = len(partition_configs_with_leader)    
    # Enumeration limits after step 3 mentioned in section 4.2 of Twins paper
    for current_round in range(nrounds):
        # Rounds start from 1 that's why using round_configs[current_round+1]
        if deterministic == True:
            round_configs[current_round + 1] = partition_configs_with_leader[current_round % no_of_partition_configs]
        else:
            leader_partition_config_selected = random.choice(partition_configs_with_leader)
            round_configs[current_round + 1] = leader_partition_config_selected

    #print(partition_configs_with_leader)
    # print(len(partition_configs_with_leader))

    testcase_config={}
    testcase_config['no_of_replicas'] = len(replicas)
    testcase_config['no_of_twins'] = len(twins)
    testcase_config['no_of_rounds'] = nrounds
    testcase_config['round_configs'] = round_configs
    return testcase_config

testcase_config = generate_round_configs(nreplicas=4, ntwins=1, npartitions=2, nrounds=16, deterministic=True, onlyfaultyleaders=True, maxpartitionsConfigs=15, onlyProgressivePartitionConfigs=False)

with open('sample_testcase_config', 'w') as f:
    json.dump(testcase_config, f)







              
















    

