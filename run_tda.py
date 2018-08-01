import argparse
import logging
import os
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


from sklearn.preprocessing import LabelEncoder
from sklearn import metrics

from analysis import Mapper, ChunkVisualiser
from classifiers import TDAClassifier, EnsembleClassifier, ClassificationVisualiser
from transforms import Flatten, FlattenTo3D, SmoothChunks, \
    TranslateChunks, AverageSpeed, AngleChangeSpeed, AmountOfMovement
from util import COCOKeypoints, coco_connections


def main(args):
    extension_free = os.path.splitext(args.dataset)[0]
    train_name = extension_free + '-train.npz'
    test_name = extension_free + '-test.npz'
    train = load_data(train_name)
    test = load_data(test_name)

    logging.info("Number of train dataset labels: {}".format(Counter(train[2])))
    logging.info("Number of test dataset labels: {}".format(Counter(test[2])))

    if args.tda:
        run_tda(train, test)
    if args.mapper:
        run_mapper(train, test)
    if args.ensemble:
        run_ensemble(train, test)
    if args.visualise:
        visualise_features(train[0], train[2])
        visualise_classes(train, test)
        plt.show()


def load_data(file_name):
    dataset_npz = np.load(file_name)
    chunks = dataset_npz['chunks']
    frames = dataset_npz['frames'].astype(np.int)
    labels = dataset_npz['labels']
    videos = dataset_npz['videos']

    return chunks, frames, labels, videos


def visualise_features(chunks, labels):
    chunk_speed = AverageSpeed(range(18)).transform(chunks)
    plot_feature_per_class(chunk_speed, labels, 'Average Speed')
    angle_change_speed = AngleChangeSpeed(coco_connections).transform(chunks)
    plot_feature_per_class(angle_change_speed, labels, 'Average Angle Change')
    movement = AmountOfMovement(range(18)).transform(chunks)
    plot_feature_per_class(movement, labels, 'Total distance')
    plt.show(block=False)


def plot_feature_per_class(feature, labels, title):
    logging.debug('Constructing dataframe')
    rows = [{'value': feature[i, j], 'keypoint': j, 'action': labels[i]}
            for i in range(feature.shape[0]) for j in range(feature.shape[1])]
    df = pd.DataFrame(rows, columns=['value', 'keypoint', 'action'])

    logging.debug('Preparing plot.')
    plt.figure()
    sns.lineplot(x='keypoint', y='value', hue='action', style='action', data=df)
    plt.title(title)


def append_train_and_test(train, test):
    chunks = np.append(train[0], test[0])
    frames = np.append(train[1], test[1])
    labels = np.append(train[2], test[2])
    videos = np.append(train[3], test[3])
    return chunks, frames, labels, videos


def visualise_classes(train, test):
    chunks, frames, labels, videos = append_train_and_test(train, test)
    translated_chunks = TranslateChunks().transform(chunks)
    visualiser = ChunkVisualiser(chunks, frames, translated_chunks)
    unique_labels = set(labels)
    nodes = {}
    for k in unique_labels:
        if k == -1:
            continue

        class_member_mask = (labels == k)
        node = np.where(class_member_mask)[0]
        name = str(k)
        nodes[name] = node

    visualiser.visualise_averages(nodes, True)


def run_ensemble(train, test):
    train_chunks, _, train_labels, _ = train
    test_chunks, test_frames, test_labels, test_videos = test
    test_translated_chunks = TranslateChunks().transform(test_chunks)

    le = LabelEncoder()
    train_labels = le.fit_transform(train_labels)
    test_labels = le.transform(test_labels)

    classifier = EnsembleClassifier()
    classifier.fit(train_chunks, train_labels)
    pred_labels = classifier.predict(test_chunks)

    accuracy = metrics.accuracy_score(test_labels, pred_labels)
    precision = metrics.precision_score(test_labels, pred_labels, average='weighted')
    recall = metrics.recall_score(test_labels, pred_labels, average='weighted')

    logging.info("Accuracy: {:.3f}\nPrecision: {:.3f}\nRecall: {:.3f}".format(
        accuracy, precision, recall))

    visualiser = ClassificationVisualiser()
    visualiser.plot_confusion_matrix(pred_labels, test_labels, le)
    visualiser.visualise_incorrect_classifications(
        pred_labels, test_labels, le, test_chunks, test_frames, test_translated_chunks, test_videos)


def run_tda(train, test):
    train_chunks, _, train_labels, _ = train
    test_chunks, test_frames, test_labels, test_videos = test
    test_translated_chunks = TranslateChunks().transform(test_chunks)

    le = LabelEncoder()
    train_labels = le.fit_transform(train_labels)
    test_labels = le.transform(test_labels)

    classifier = TDAClassifier(cross_validate=False)
    classifier.fit(train_chunks, train_labels)
    pred_labels = classifier.predict(test_chunks)

    accuracy = metrics.accuracy_score(test_labels, pred_labels)
    precision = metrics.precision_score(test_labels, pred_labels, average='weighted')
    recall = metrics.recall_score(test_labels, pred_labels, average='weighted')

    logging.info("Accuracy: {:.3f}\nPrecision: {:.3f}\nRecall: {:.3f}".format(
        accuracy, precision, recall))

    visualiser = ClassificationVisualiser()
    visualiser.plot_confusion_matrix(pred_labels, test_labels, le)
    visualiser.visualise_incorrect_classifications(
        pred_labels, test_labels, le, test_chunks, test_frames, test_translated_chunks, test_videos)


def run_mapper(test, train):
    chunks, frames, labels, videos = append_train_and_test(train, test)
    translated_chunks = TranslateChunks().transform(chunks)

    logging.info("Smoothing chunks.")
    translated_chunks = SmoothChunks().transform(translated_chunks)

    selected_keypoints = [
        COCOKeypoints.RShoulder.value,
        COCOKeypoints.LShoulder.value,
        COCOKeypoints.RElbow.value,
        COCOKeypoints.LElbow.value,
        COCOKeypoints.RWrist.value,
        COCOKeypoints.LWrist.value
    ]
    logging.info("Flattening data into a datapoint per chunk.")
    data = Flatten(selected_keypoints).transform(translated_chunks)
    logging.info("Applying mapping to tracks.")
    mapper = Mapper(chunks, frames, translated_chunks, labels)
    mapper.create_tooltips(videos)
    graph = mapper.mapper(data)
    logging.info("Visualisation of the resulting nodes.")
    mapper.visualise(videos, graph)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TDA analysis of the tracks.')
    parser.add_argument('--dataset', type=str, help='The path to the dataset')
    parser.add_argument('--mapper', action='store_true',
                        help='Run the mapper algorithm on the data')
    parser.add_argument('--tda', action='store_true',
                        help='Run a TDA algorithm on the data.')
    parser.add_argument('--visualise', action='store_true',
                        help='Specify if you wish to only visualise the classes in the dataset.')
    parser.add_argument('--ensemble', action='store_true',
                        help='Runs a voting classifier on TDA and feature engineering on the dataset.')

    logging.basicConfig(level=logging.DEBUG)
    args = parser.parse_args()

    main(args)
