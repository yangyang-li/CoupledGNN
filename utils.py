import numpy as np
import pickle as pkl
import scipy.sparse as sp
import sys,math
from scipy.sparse import csr_matrix

#load the node embeddings generated by deepwalk
def load_embeddings(filename):
    file = open(filename)
    [n_nodes,dimension] = [int(x) for x in file.readline().split(" ")]
    embeddings = dict()
    for line in file:
        parts = line.split(" ")
        node_id = int(parts[0])
        node_e = []
        for i in range(dimension):
            node_e.append(float(parts[i+1]))
        embeddings[node_id] = node_e
    if len(embeddings) <n_nodes:
        print(" less embedings than nodes!",len(embeddings),n_nodes)
    embeddings_list = []
    for i in range(n_nodes):
        embeddings_list.append(embeddings[i])
    return embeddings_list

def load_data(dataset_str,filepath):
    """
    Loads input data from gcn/data directory

    ind.dataset_str.***.x => a list recording the observation for each sample, x[i] = [(t1,u1),(t2,u2),...,(tn,un)]
    ind.dataset_str.***.y => a list recording the prediction for each sample, y[i] = dict(u1,u2,...,un)
    ind.dataset_str.graph => a dict in the format {index: [index_of_neighbor_nodes]} as collections.
    ind.dataset_str.emb_32 => a list recording the embeddings of each node
    ind.dataset_str.features => a list recording the features of each ndoe

    All objects above must be saved using python pickle module.
    :param dataset_str: Dataset name
    :return: All data input files loaded (as well the training/test data).
    """
    names = ['train.x', 'train.y','val.x', 'val.y','test.x', 'test.y', 'graph','features']
    objects = []
    for i in range(len(names)):
        with open(filepath+"Data/ind.{}.{}".format(dataset_str, names[i]), 'rb') as f:
            if sys.version_info > (3, 0):
                objects.append(pkl.load(f, encoding='latin1'))
            else:
                objects.append(pkl.load(f))

    train_x,train_y,val_x,val_y,test_x,test_y,graph,vertex_features = tuple(objects)

    #get adjacency matrix
    edges = dict()
    users = set()
    for src in graph:
        dsts = graph[src]
        users.add(src)
        for j in range(len(dsts)):
            dst = dsts[j]
            if src != dst:
                edges[(src,dst)] = 1
            users.add(dst)
    print("total number of users:",len(users))
    print("total number of edges:",len(edges))

    row = []
    col = []
    data = []
    for e in edges.keys():
        (src,dst) = e
        weight = edges[e]
        row.append(src)
        col.append(dst)
        data.append(weight)
    adj = csr_matrix((data,(row,col)),shape=(len(users),len(users)))


    #get influence representations
    node_vec = load_embeddings(filepath + "Data/" + dataset_str + '.emb_32')
    n_nodes = adj.shape[0]
    inputs_features = []
    for i in range(n_nodes):
        inputs_features.append([])
    print("dimension of node embeddings:", len(node_vec), len(node_vec[0]))
    print("dimension of vertex features:", len(vertex_features), len(vertex_features[0]))
    for i in range(n_nodes):
        inputs_features[i] = inputs_features[i] + node_vec[i]
    for i in range(n_nodes):
        inputs_features[i] = inputs_features[i] + vertex_features[i]
    print("total number of influence dimensions:", len(inputs_features[0]))

    return adj, train_x,train_y,val_x,val_y,test_x,test_y,inputs_features


def sparse_to_tuple(sparse_mx):
    """Convert sparse matrix to tuple representation."""
    def to_tuple(mx):
        if not sp.isspmatrix_coo(mx):
            mx = mx.tocoo()
        coords = np.vstack((mx.row, mx.col)).transpose()
        values = mx.data
        shape = mx.shape
        return coords, values, shape

    if isinstance(sparse_mx, list):
        for i in range(len(sparse_mx)):
            sparse_mx[i] = to_tuple(sparse_mx[i])
    else:
        sparse_mx = to_tuple(sparse_mx)

    return sparse_mx


def normalize_adj(adj):
    """ normalize adjacency matrix."""
    adj = sp.coo_matrix(adj)
    rowsum = np.array(adj.sum(1))
    d_inv_sqrt = np.power(rowsum, -0.5).flatten()
    d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.
    d_mat_inv_sqrt = sp.diags(d_inv_sqrt)
    return adj.dot(d_mat_inv_sqrt).transpose().dot(d_mat_inv_sqrt).tocoo()


def preprocess_adj(adj,normalize):
    """Preprocessing of adjacency matrix for simple GCN model and conversion to tuple representation."""
    if normalize:
            adj_normalized = normalize_adj(adj)
    else:
            adj_normalized = sp.coo_matrix(adj).tocoo()
    return sparse_to_tuple(adj_normalized)


def construct_feed_dict(support, placeholders):
    """Construct feed dictionary."""
    feed_dict = dict()
    (indices,_,_) = support
    indices_inverse = np.zeros(shape=[len(indices),2],dtype=np.int64)
    for i in range(len(indices)):
        [x,y] = indices[i]
        indices_inverse[i][0] = y
        indices_inverse[i][1] = x
    feed_dict.update({placeholders['support_indices']: indices_inverse})

    return feed_dict

