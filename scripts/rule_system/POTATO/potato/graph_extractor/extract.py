import json
import os
from collections import defaultdict

import networkx as nx
import pandas as pd
import stanza
from potato.dataset.utils import default_pn_to_graph, ud_to_graph
from networkx.algorithms.isomorphism import DiGraphMatcher
from sklearn.metrics import precision_recall_fscore_support
from tqdm import tqdm
from potato.grammar.text_to_4lang import TextTo4lang
from potato.graph.utils import GraphFormulaMatcher
from potato.text.pipeline import CachedStanzaPipeline


class GraphExtractor:
    def __init__(self, cache_dir=None, cache_fn=None, lang=None):
        self.cache_dir = cache_dir
        self.cache_fn = cache_fn
        self.lang = lang
        self.nlp = None
        self.matcher = None

    def init_nlp(self):
        if self.lang == "en_bio":
            nlp = stanza.Pipeline("en", package="craft")
        else:
            nlp = stanza.Pipeline(self.lang)
        self.nlp = CachedStanzaPipeline(nlp, self.cache_fn)

    def parse_iterable(self, iterable, graph_type="fourlang"):
        if graph_type == "fourlang":
            with TextTo4lang(
                lang=self.lang, nlp_cache=self.cache_fn, cache_dir=self.cache_dir
            ) as tfl:
                for sen in tqdm(iterable):
                    fl_graphs = list(tfl(sen))
                    g = fl_graphs[0]
                    for n in fl_graphs[1:]:
                        g = nx.compose(g, n)
                    yield g

        if graph_type == "ud":
            self.init_nlp()
            for sen in tqdm(iterable):
                doc = self.nlp(sen)
                g, _ = ud_to_graph(doc.sentences[0])
                for doc_sen in doc.sentences[1:]:
                    n, _ = ud_to_graph(doc_sen)
                    g = nx.compose(g, n)
                yield g


class FeatureEvaluator:
    def __init__(self, graph_format="ud"):
        self.graph_format = graph_format

    def match_features(self, dataset, features):
        graphs = dataset.graph.tolist()

        matches = []
        predicted = []

        matcher = GraphFormulaMatcher(features, converter=default_pn_to_graph)

        for i, g in tqdm(enumerate(graphs)):
            feats = matcher.match(g)
            for key, feature in feats:
                matches.append(features[feature])
                predicted.append(key)
                break
            else:
                matches.append("")
                predicted.append("")

        d = {
            "Sentence": dataset.text.tolist(),
            "Predicted label": predicted,
            "Matched rule": matches,
        }
        df = pd.DataFrame(d)
        return df

    def one_versus_rest(self, df, entity):
        mapper = {entity: 1}

        one_versus_rest_df = df.copy()
        one_versus_rest_df["one_versus_rest"] = [
            mapper[item] if item in mapper else 0 for item in df.label
        ]

        return one_versus_rest_df

    def rank_features(self, cl, features, orig_data, false_negatives):
        subset_data = orig_data.iloc[false_negatives]
        df, accuracy = self.evaluate_feature(cl, features, subset_data)

        features_stat = []

        for i, feature in enumerate(features):
            features_stat.append(
                (
                    feature,
                    df.iloc[i].Precision,
                    df.iloc[i].Recall,
                    df.iloc[i].Fscore,
                    df.iloc[i].Support,
                )
            )

        def rank(feature):
            return len(df.iloc[features.index(feature[0])].True_positive_graphs)

        return sorted(features_stat, key=rank, reverse=True)

    def train_feature(self, cl, feature, data, graph_format="ud"):
        feature_graph = default_pn_to_graph(feature)[0]

        graphs = data.graph.tolist()
        labels = self.one_versus_rest(data, cl).one_versus_rest.tolist()
        path = "trained_features.tsv"
        trained_features = []
        with open(path, "w+") as f:
            for i, g in enumerate(graphs):
                matcher = DiGraphMatcher(
                    g,
                    feature_graph,
                    node_match=GraphFormulaMatcher.node_matcher,
                    edge_match=GraphFormulaMatcher.edge_matcher,
                )
                if matcher.subgraph_is_isomorphic():
                    for iso_pairs in matcher.subgraph_isomorphisms_iter():
                        nodes = []
                        for k in iso_pairs:
                            if feature_graph.nodes[iso_pairs[k]]["name"] == ".*":
                                nodes.append(g.nodes[k]["name"])
                        if not nodes:
                            g2_to_g1 = {v: u for (u, v) in iso_pairs.items()}
                            for u, v, attrs in feature_graph.edges(data=True):
                                if attrs["color"] == ".*":
                                    edge = g.get_edge_data(g2_to_g1[u], g2_to_g1[v])[
                                        "color"
                                    ]
                                    nodes.append(edge)
                        nodes_str = ",".join(nodes)
                        label = labels[i]
                        sentence = data.iloc[i].text
                        f.write(f"{feature}\t{nodes_str}\t{sentence}\t{label}\n")
                        trained_features.append(
                            (feature, nodes_str, sentence, str(label))
                        )

        return self.cluster_feature(trained_features)

    def cluster_feature(self, trained_features):
        def to_dot(graph, feature):
            lines = ["digraph finite_state_machine {"]
            lines.append("\tdpi=70;label=" + '"' + feature + '"')
            # lines.append('\tordering=out;')
            # sorting everything to make the process deterministic
            node_lines = []
            node_to_name = {}
            for node, n_data in graph.nodes(data=True):
                printname = node
                if "color" in n_data and n_data["color"] == "red":
                    node_line = '\t{0} [shape = circle, label = "{1}", \
                            style=filled, fillcolor=red];'.format(
                        printname, printname.split("_")[0]
                    ).replace(
                        "-", "_"
                    )
                if "color" in n_data and n_data["color"] == "green":
                    node_line = '\t{0} [shape = circle, label = "{1}", \
                            style="filled", fillcolor=green];'.format(
                        printname, printname.split("_")[0]
                    ).replace(
                        "-", "_"
                    )
                node_lines.append(node_line)
            lines += sorted(node_lines)

            edge_lines = []
            for u, v, edata in graph.edges(data=True):
                if "color" in edata:
                    edge_lines.append(
                        '\t{0} -> {1} [ label = "{2}" ];'.format(u, v, edata["color"])
                    )

            lines += sorted(edge_lines)
            lines.append("}")
            return "\n".join(lines)

        graphs = {}
        if os.path.isfile("longman_zero_paths_one_exp"):
            with open("longman_zero_paths_one_exp.json") as f:
                graphs = json.load(f)

        words = {}
        for fields in trained_features:
            words[fields[1] + "_" + fields[3]] = int(fields[3])
            feature = fields[0]
        graph = nx.MultiDiGraph()

        for word in words:
            if words[word] == 1:
                color = "green"
            else:
                color = "red"
            graph.add_node(word, color=color)
            word_clean = word.split("_")[0]
            if word_clean in graphs:
                hypernyms = graphs[word_clean]
                for hypernym in hypernyms:
                    hypernym_words = hypernyms[hypernym]
                    for w in hypernym_words:
                        if hypernym == "1":
                            graph.add_edge(word, w, color=hypernym)

        # Show words!
        # d = Source(to_dot(graph, feature))
        # d.engine = "circo"
        # d.format = "png"

        selected_words = self.select_words(trained_features)

        word_features = []

        word_features.append(feature.replace(".*", "|".join(selected_words)))

        # return d.render(view=True), word_features
        return word_features

    def select_words(self, trained_features):
        features = []
        labels = []

        for fields in trained_features:
            features.append(fields[1])
            labels.append(int(fields[3]))
        words_to_measures = {
            word: {"TP": 0, "FP": 0, "TN": 0, "FN": 0} for word in set(features)
        }
        for word in words_to_measures:
            for i, label in enumerate(labels):
                if label and features[i] == word:
                    words_to_measures[word]["TP"] += 1
                if label and features[i] != word:
                    words_to_measures[word]["FN"] += 1
                if not label and features[i] == word:
                    words_to_measures[word]["FP"] += 1
                if not label and features[i] != word:
                    words_to_measures[word]["TN"] += 1

        for word in words_to_measures:
            TP = words_to_measures[word]["TP"]
            FP = words_to_measures[word]["FP"]
            TN = words_to_measures[word]["TN"]
            FN = words_to_measures[word]["FN"]

            precision = TP / (TP + FP)
            recall = TP / (TP + FN)

            words_to_measures[word]["precision"] = precision
            words_to_measures[word]["recall"] = recall

        selected_words = set()

        for word in words_to_measures:
            if words_to_measures[word]["precision"] > 0.9 and (
                words_to_measures[word]["TP"] > 1
                or words_to_measures[word]["recall"] > 0.01
            ):
                selected_words.add(word)

        return selected_words

    def evaluate_feature(self, cl, features, data, graph_format="ud"):
        measure_features = []
        graphs = data.graph.tolist()
        labels = self.one_versus_rest(data, cl).one_versus_rest.tolist()

        whole_predicted = []
        matched = defaultdict(list)

        # We want to view false negative examples for all rules, not rule specific
        false_neg_g = []
        false_neg_s = []
        false_neg_indices = []
        matcher = GraphFormulaMatcher(features, converter=default_pn_to_graph)
        for i, g in enumerate(graphs):
            feats = matcher.match(g)
            label = 0
            for key, feature in feats:
                matched[i].append(features[feature][0])
                label = 1
            whole_predicted.append(label)

            if label == 0 and labels[i] == 1:
                false_neg_g.append(g)
                sen = data.iloc[i].text
                lab = data.iloc[i].label
                false_neg_s.append((sen, lab))
                false_neg_indices.append(i)

        accuracy = []
        for pcf in precision_recall_fscore_support(
            labels, whole_predicted, average=None
        ):
            accuracy.append(pcf[1])

        for feat in features:
            measure = [feat[0]]
            false_pos_g = []
            false_pos_s = []
            true_pos_g = []
            true_pos_s = []
            predicted = []
            for i, g in enumerate(graphs):
                feats = matched[i]
                label = 1 if feat[0] in feats else 0
                if label == 1 and labels[i] == 0:
                    false_pos_g.append(g)
                    sen = data.iloc[i].text
                    lab = data.iloc[i].label
                    false_pos_s.append((sen, lab))
                if label == 1 and labels[i] == 1:
                    true_pos_g.append(g)
                    sen = data.iloc[i].text
                    lab = data.iloc[i].label
                    true_pos_s.append((sen, lab))
                predicted.append(label)
            for pcf in precision_recall_fscore_support(labels, predicted, average=None):
                measure.append(pcf[1])
            measure.append(false_pos_g)
            measure.append(false_pos_s)
            measure.append(true_pos_g)
            measure.append(true_pos_s)
            measure.append(false_neg_g)
            measure.append(false_neg_s)
            measure.append(false_neg_indices)
            measure.append(predicted)
            measure_features.append(measure)

        df = pd.DataFrame(
            measure_features,
            columns=[
                "Feature",
                "Precision",
                "Recall",
                "Fscore",
                "Support",
                "False_positive_graphs",
                "False_positive_sens",
                "True_positive_graphs",
                "True_positive_sens",
                "False_negative_graphs",
                "False_negative_sens",
                "False_negative_indices",
                "Predicted",
            ],
        )

        return df, accuracy
