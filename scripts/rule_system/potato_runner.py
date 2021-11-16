import sys

sys.path.append("../bert_system")
from argparse import ArgumentParser
from potato.dataset.dataset import Dataset
from potato.dataset.utils import amr_pn_to_graph
from potato.models.trainer import GraphTrainer
import re
import pandas as pd
import json
from read_data import read_csv


toxic_or_not = {'NOT': 'OTHER', 'HOF': 'TOXIC', 'OTHER': 'OTHER', 'OFFENSE': 'TOXIC', 1: 'TOXIC', 0: 'OTHER'}
label_dict = {'OTHER': 0, 'TOXIC': 1}


def create_data(str_path, graph_path, lang):
    if "xlsx" in str_path:
        str_data = pd.read_excel(str_path, engine='openpyxl')
    else:
        str_data = read_csv(str_path, names=['text', 'label', 'category', 'directed'])
    text = 'text' if 'text' in str_data else ('comment_text' if 'comment_text' in str_data else 'c_text')
    label = 'task1' if 'task1' in str_data else ('task_1' if 'task_1' in str_data else
                                                 ('label' if 'label' in str_data else 'Sub1_Toxic'))
    str_sentences = [(text, toxic) for (text, toxic) in zip(str_data[text], str_data[label])]
    with open(graph_path) as graph:
        graph_data = graph.read()
    dataset = Dataset(str_sentences, label_vocab=label_dict, lang=lang)
    graphs = []
    for gd in re.split(r'# ::id [0-9]*', graph_data)[1:]:
        gd = gd.replace('/ #', '/ hashtag_').replace('~', '[zirca]')
        graphs.append(amr_pn_to_graph(gd, edge_attr="color", clean_nodes=True)[0])
    dataset.set_graphs(graphs)
    return dataset.to_dataframe()


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument("--amr", help="Path to the amr graphs")
    args.add_argument("--text", help="Path to the train/dev/test data")
    args.add_argument("--train", action="store_true")
    args.add_argument("--lang", choices=["en", "de"])
    args.add_argument("--feature", help="Where to save the features after training", default="features.json")
    args.add_argument("--save", help="Where to save the dataset", default="dataset")
    arg = args.parse_args()
    df = create_data(arg.text, arg.amr, arg.lang).dropna()
    df.to_pickle(arg.save)
    if arg.train:
        trainer = GraphTrainer(df, lang="de")
        features = trainer.prepare_and_train()
        with open(arg.feature, "w") as f:
            json.dump(features, f, indent=4)
