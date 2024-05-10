import grpc
import node_pb2
import node_pb2_grpc
import socket
import hashlib
from concurrent import futures
import time

class NodeService(node_pb2_grpc.NodeServiceServicer):
    def __init__(self, node_id, node_name, ip_address, initial_connected_nodes=None, initial_value_table=None):
        self.node_id = node_id
        self.node_name = node_name
        self.ip_address = ip_address
        self.connected_nodes = initial_connected_nodes if initial_connected_nodes is not None else {}
        self.value_table = initial_value_table if initial_value_table is not None else {}
        self.role = None  # Role will be determined dynamically

    def JoinCluster(self, request, context):
        try:
            new_node_id = request.node_id
            new_node_name = request.node_name
            new_node_ip = request.ip_address
            
            self.connected_nodes[new_node_id] = (new_node_name, new_node_ip)
            print("[{}] Updated connected nodes when JoinCluster: {}".format(self.node_name, self.connected_nodes))  # Print connected_nodes
            self.update_role()

            print("[{}] Node {} ({}) joined the cluster.".format(self.node_name, new_node_id, new_node_name))
            print("[{}] Updated connected nodes: {}".format(self.node_name, self.connected_nodes))
            print("[{}] Updated value table: {}".format(self.node_name, self.value_table))

            return node_pb2.JoinClusterResponse()
        except Exception as e:
            print("Exception occurred in JoinCluster: {}".format(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Error occurred: {}".format(e))
            return node_pb2.JoinClusterResponse()

    def StoreData(self, request, context):
        try:
            if not request.key:
                print("[{}] Error: Key is None.".format(self.node_name))
                return node_pb2.StoreDataResponse()

            if self.role == "receiver":
                # Store data and replicate if needed (not implemented)
                self.value_table[request.key] = request.value
            else:  # If hasher node
                target_node_id = self.get_target_receiver_node_id(request.key[:10])
                target_node_ip = self.get_connected_node_ip(target_node_id)
                if target_node_ip:
                    self.send_to_node(target_node_id, request, target_node_ip)
                    print("[{}] Data forwarded to receiver node {}.".format(self.node_name, target_node_id))
                    print("[{}] Updated value table fro StoreData method: {}".format(self.node_name, self.value_table))
                else:
                    print("[{}] Error: Unable to find IP address of node {}.".format(self.node_name, target_node_id))

            return node_pb2.StoreDataResponse()
        except Exception as e:
            print("Exception occurred in StoreData: {}".format(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Error occurred: {}".format(e))
            return node_pb2.StoreDataResponse()

    def RetrieveData(self, request, context):
        try:
            if self.role == "receiver":
                # If receiver node, relay request to a hasher node
                target_node_id = self.get_target_hasher_node_id(request.key[:10])
                target_node_ip = self.get_connected_node_ip(target_node_id)
                if target_node_ip:
                    self.send_to_node(target_node_id, request, target_node_ip)
                    print("[{}] Retrieve request forwarded to hasher node {}.".format(self.node_name, target_node_id))
                else:
                    print("[{}] Error: Unable to find IP address of node {}.".format(self.node_name, target_node_id))
            else:
                # If hasher node, retrieve data from local table
                if request.key in self.value_table:
                    return node_pb2.RetrieveDataResponse(value=self.value_table[request.key])
                else:
                    return node_pb2.RetrieveDataResponse()
        except Exception as e:
            print("Exception occurred in RetrieveData: {}".format(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Error occurred: {}".format(e))
            return node_pb2.RetrieveDataResponse()

    def compute_hash(self, key):
        short_key = key[:10]  # Take only the first 10 characters of the key
        hash_value = int(hashlib.md5(short_key.encode()).hexdigest(), 16)  # Compute MD5 hash of the short key
        print("[{}] Hash value for key '{}' is {}.".format(self.node_name, key, hash_value))
        return hash_value
        
    def update_role(self):
        previous_role = self.role
        self.role = "receiver" if len(self.connected_nodes) % 2 == 1 and len(self.connected_nodes) != 0 else "hasher"
        print("[{}] Updated role: {}".format(self.node_name, self.role))
        
        # Check if role has changed
        if previous_role != self.role:
            return "Role updated to {}".format(self.role)
        else:
            return "Role remains unchanged as {}".format(self.role)

    def broadcast_join_message(self, new_node_id, new_node_name, new_node_ip):
        for existing_node_id, existing_node_info in self.connected_nodes.items():
            existing_node_ip = existing_node_info[1]
            self.send_join_message(existing_node_id, existing_node_ip, new_node_id, new_node_name, new_node_ip)
            print("[{}] Join message sent to node {}.".format(self.node_name, existing_node_id))

    def send_join_message(self, target_node_id, target_node_ip, new_node_id, new_node_name, new_node_ip):
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            stub.NotifyNodeJoined(node_pb2.NotifyNodeJoinedRequest(
                node_id=new_node_id, node_name=new_node_name, ip_address=new_node_ip))
        print("[{}] Join message sent to node {}.".format(self.node_name, target_node_id))

    def send_to_node(self, node_id, request, target_node_ip):
        with grpc.insecure_channel(target_node_ip) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            stub.StoreData(request)
        print("[{}] Data sent to node {}.".format(self.node_name, node_id))

    def get_target_receiver_node_id(self, hash_key):
        receiver_node_id = self.compute_hash(hash_key) % len(self.connected_nodes)
        print("[{}] Target receiver node ID for hash key '{}' is {}.".format(self.node_name, hash_key, receiver_node_id))
        return receiver_node_id

    def get_target_hasher_node_id(self, hash_key):
        hasher_node_id = (self.compute_hash(hash_key) + 1) % len(self.connected_nodes)
        print("[{}] Target hasher node ID for hash key '{}' is {}.".format(self.node_name, hash_key, hasher_node_id))
        return hasher_node_id

    def GetConnectedNodeIP(self, request, context):
        try:
            node_id = request.node_id
            if node_id in self.connected_nodes:
                return node_pb2.GetConnectedNodeIPResponse(ip_address=self.connected_nodes[node_id][1])
            else:
                return node_pb2.GetConnectedNodeIPResponse(ip_address="")
        except Exception as e:
            print("Exception occurred in GetConnectedNodeIP: {}".format(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Error occurred: {}".format(e))
            return node_pb2.GetConnectedNodeIPResponse(ip_address="")

    def get_connected_node_ip(self, node_id):
        try:
            if node_id in self.connected_nodes:
                connected_node_ip = self.connected_nodes[node_id][1]
                print("[{}] Connected node IP for node ID {} is {}.".format(self.node_name, node_id, connected_node_ip))
                return connected_node_ip
            else:
                print("[{}] Node ID {} is not in the connected nodes.".format(self.node_name, node_id))
                return None
        except Exception as e:
            print("[{}] Exception occurred in get_connected_node_ip: {}".format(self.node_name, e))
            return None

def start_server(node_id, node_name, ip_address):
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        node_service = NodeService(node_id, node_name, ip_address)
        node_pb2_grpc.add_NodeServiceServicer_to_server(node_service, server)
        server.add_insecure_port(ip_address)
        server.start()
        print("[{}] Server started successfully.".format(node_name))
        try:
            while True:
                time.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            server.stop(0)
            print("[{}] Server stopped.".format(node_name))
    except Exception as e:
        print("Exception occurred in start_server: {}".format(e))

if __name__ == '__main__':
    # Iterate through each node ID from 0 to 4
    for node_id in range(1):
        # Generate node name and IP address
        node_name = 'Node_{}'.format(node_id)
        ip_address = '{}:{}'.format(socket.gethostbyname(socket.gethostname()), 50051)
        print("[{}] Node IP address {}.".format(node_name, ip_address))
        # Start the server
        start_server(node_id, node_name, ip_address)
