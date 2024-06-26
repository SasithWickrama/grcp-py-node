import grpc
import node_pb2
import node_pb2_grpc
import socket
import hashlib

def join_cluster(target_node_ip, node_id, node_name):
    try:
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            response = stub.JoinCluster(node_pb2.JoinClusterRequest(node_id=str(node_id), node_name=node_name, ip_address=target_node_ip))
            print("Response - Joined cluster successfully.")
            print("Response status:", response)
    except grpc.RpcError as e:
        print("gRPC error join_cluster:", e.details())

def retrieve_data(target_node_ip, key):
    try:
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            response = stub.RetrieveData(node_pb2.RetrieveDataRequest(key=key))
            if response.value:
                print("Retrieved value:", response.value)
            else:
                print("Key not found.")
    except grpc.RpcError as e:
        print("gRPC error retrieve_data:", e.details())

def compute_hash(key):
    return int(hashlib.md5(key.encode()).hexdigest(), 16)  # Compute MD5 hash of the key

def send_to_node(target_node_ip, key, value):
    try:
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            response = stub.StoreData(node_pb2.StoreDataRequest(key=key, value=value))
            print("Data sent successfully to node at IP:", target_node_ip)
    except grpc.RpcError as e:
        print("gRPC error send_to_node:", e.details())

def notify_node_joined(target_node_ip, node_id, node_name, new_node_ip):
    try:
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            response = stub.NotifyNodeJoined(node_pb2.NotifyNodeJoinedRequest(
                node_id=str(node_id),  # Convert node_id to string
                node_name=node_name,
                ip_address=new_node_ip  # No need to encode new_node_ip
            ))
            print("Notified node joined successfully.")
    except grpc.RpcError as e:
        print("gRPC error notify_node_joined:", e.details())

def get_connected_node_ip(target_node_ip, node_id):
    try:
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            response = stub.GetConnectedNodeIP(node_pb2.GetConnectedNodeIPRequest(node_id=str(node_id)))  # Convert node_id to string
            return response.ip_address
    except grpc.RpcError as e:
        print("gRPC error get_connected_node_ip:", e.details())

if __name__ == "__main__":
    # target node IP address
    target_node_ip_template = "172.26.0.{}:50051"
    node_name_template = "Node{}"


    for node_id in range(1, 6):
        # Your code here
        print("Node ID:", node_id)
        # target node IP address
        target_node_ip = "172.26.0.{}:50051".format(node_id)  
        node_name = "Node{}".format(node_id)

        # Join the cluster
        join_cluster(target_node_ip, node_id, node_name)

        # key to retrieve
        key_to_retrieve = "SampleKey"  
        retrieve_data(target_node_ip, key_to_retrieve)

        # key and value to send
        key_to_send = "SampleKey"  
        value_to_send = "c05bb7fd2f3f0b1ad4465cf5e9c3b014" 
        send_to_node(target_node_ip, key_to_send, value_to_send)

        # new node IP address
        new_node_ip = "172.26.0.2:50051"  
        notify_node_joined(target_node_ip, node_id, node_name, new_node_ip)

        # node ID to get connected node IP
        node_id_to_get_ip = "1"  # node ID to get connected node IP (converted to string)
        connected_node_ip = get_connected_node_ip(target_node_ip, node_id_to_get_ip)
        if connected_node_ip:
            print("Connected node IP:", connected_node_ip)
        else:
            print("Failed to retrieve connected node IP.")


'''
if __name__ == "__main__":
    # target node IP address
    target_node_ip = "172.26.0.3:50051"  
    node_id = 2  # node ID
    node_name = "Node2"  # node name

    # Join the cluster
    join_cluster(target_node_ip, node_id, node_name)

    # key to retrieve
    key_to_retrieve = "SampleKey"  # key to retrieve
    retrieve_data(target_node_ip, key_to_retrieve)

    # key and value to send
    key_to_send = "SampleKey"  # key to send
    value_to_send = "c05bb7fd2f3f0b1ad4465cf5e9c3b014"  # value to send
    send_to_node(target_node_ip, key_to_send, value_to_send)

    # new node IP address
    new_node_ip = "172.26.0.4:50051"  # Change this to the IP of the new node
    notify_node_joined(target_node_ip, node_id, node_name, new_node_ip)

    # node ID to get connected node IP
    node_id_to_get_ip = "1"  # node ID to get connected node IP (converted to string)
    connected_node_ip = get_connected_node_ip(target_node_ip, node_id_to_get_ip)
    if connected_node_ip:
        print("Connected node IP:", connected_node_ip)
    else:
        print("Failed to retrieve connected node IP.")
'''