from keras.models import Sequential, Model, load_model
from keras.layers.core import Flatten, Dense, Dropout, Lambda
from keras.layers.convolutional import Convolution2D, MaxPooling2D
from keras.layers import Activation
from keras.optimizers import Adam
from keras.callbacks import ModelCheckpoint
from keras import backend as K, Input
from keras.preprocessing.image import ImageDataGenerator
from keras.initializers import RandomNormal, Constant
from sklearn.metrics import f1_score, roc_curve, auc
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy.random as rng
import cv2
import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import warnings
import random
from itertools import combinations, product
import time
import csv

warnings.simplefilter('ignore')
gpu_options = tf.compat.v1.GPUOptions(allow_growth=True)
sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options))

#PARAMETER
INPUT_IMAGES = (80, 80, 1)
NUM_PAIRS = 12000
BATCH_SIZE = 32
NUM_PART = 4
IMAGE_DATASET = "/home/m433788/Thesis/data_asli/4_subregion/asli"

#TRIPLET LOSS
def triplet_loss(y_true, y_pred, margin=0.2):
	anchor, positive, negative = y_pred[:, 0], y_pred[:, 1], y_pred[:, 2]
	# Step 1: Compute the (encoding) distance between the anchor and the positive
	pos_dist = K.sum(
		K.square(anchor - positive), axis=1)
	# Step 2: Compute the (encoding) distance between the anchor and the negative
	neg_dist = K.sum(
		K.square(anchor - negative), axis=1)
	# Step 3: subtract the two previous distances and add alpha.
	basic_loss = (pos_dist - neg_dist) + margin
	# Step 4: Take the maximum of basic_loss and 0.0. Sum over the training examples.
	loss = K.sum(K.maximum(basic_loss, 0.0))
	return loss

#ACCURACY
def calculate_accuracy(predict_issame, actual_issame):
	tp = np.sum(np.logical_and(predict_issame, actual_issame))
	fp = np.sum(np.logical_and(predict_issame, np.logical_not(actual_issame)))
	tn = np.sum(np.logical_and(np.logical_not(
		predict_issame), np.logical_not(actual_issame)))
	fn = np.sum(np.logical_and(np.logical_not(predict_issame), actual_issame))

	prc = float(tp / (tp+fp))
	acc = float((tp+tn)/len(predict_issame))
	return prc, acc

#DISTANCE METRICS
def euclidean_distance(vects):
	x, y = vects
	sum_square = K.sum(K.square(x - y), axis=1, keepdims=True)
	return K.sqrt(K.maximum(sum_square, K.epsilon()))

def eucl_dist_output_shape(shapes):
	shape1, shape2 = shapes
	return (shape1[0], 1)

#MODEL
def base_network(input_shape):  # Inisialisasi model siamese triplet

	zero_mean = RandomNormal(mean=0.0, stddev=0.01, seed=None)
	bias_value = Constant(value=0.5)

	model = Sequential()
	model.add(Convolution2D(32, (7, 7), activation='relu', input_shape=input_shape, padding='same',
                         kernel_initializer=zero_mean, bias_initializer=bias_value))
	model.add(MaxPooling2D((2, 2), strides=2, padding='same'))
	model.add(Convolution2D(64, (5, 5), activation='relu', padding='same',
                         kernel_initializer=zero_mean, bias_initializer=bias_value))
	model.add(MaxPooling2D((2, 2), strides=2, padding='same'))
	model.add(Convolution2D(128, (3, 3), activation='relu', padding='same',
                         kernel_initializer=zero_mean, bias_initializer=bias_value))
	model.add(MaxPooling2D((2, 2), strides=2, padding='same'))
	model.add(Convolution2D(128, (3, 3), activation='relu', padding='same',
                         kernel_initializer=zero_mean, bias_initializer=bias_value))
	model.add(MaxPooling2D((2, 2), strides=2, padding='same'))
	model.add(Convolution2D(256, (2, 2), activation='relu', padding='same',
                         kernel_initializer=zero_mean, bias_initializer=bias_value))
	model.add(MaxPooling2D((2, 2), strides=2, padding='same'))
	model.add(Flatten())
	model.add(Dense(160, activation='tanh',
                 kernel_initializer=zero_mean, bias_initializer=bias_value))

	return model

#SIAMESE NETWORK
def siamese_net_1(base_model, input_shape):
	input_1 = Input(input_shape)
	input_2 = Input(input_shape)

	enc_1 = base_model(input_1)
	enc_2 = base_model(input_2)

	distances = Lambda(euclidean_distance,
					output_shape=eucl_dist_output_shape)([enc_1, enc_2])

	model = Model([input_1, input_2], distances)

	return model

def siamese_net_2(base_model, input_shape):
	input_1 = Input(input_shape)
	input_2 = Input(input_shape)

	enc_1 = base_model(input_1)
	enc_2 = base_model(input_2)

	distances = Lambda(euclidean_distance,
					output_shape=eucl_dist_output_shape)([enc_1, enc_2])

	model = Model([input_1, input_2], distances)

	return model

def siamese_net_3(base_model, input_shape):
	input_1 = Input(input_shape)
	input_2 = Input(input_shape)

	enc_1 = base_model(input_1)
	enc_2 = base_model(input_2)

	distances = Lambda(euclidean_distance,
					output_shape=eucl_dist_output_shape)([enc_1, enc_2])

	model = Model([input_1, input_2], distances)

	return model

def siamese_net_4(base_model, input_shape):
	input_1 = Input(input_shape)
	input_2 = Input(input_shape)

	enc_1 = base_model(input_1)
	enc_2 = base_model(input_2)

	distances = Lambda(euclidean_distance,
					output_shape=eucl_dist_output_shape)([enc_1, enc_2])

	model = Model([input_1, input_2], distances)

	return model

#PREPROCESSING
def pre_process_image(image):  # Fungsi untuk mengubah ukuran gambar
	image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	image = cv2.resize(image, dsize=(INPUT_IMAGES[0], INPUT_IMAGES[1]))
	return np.asarray(image)

#GET DATA
def cached_imread(image_path, image_cache):
	if image_path not in image_cache:
		image = cv2.imread(image_path)
		image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		image = cv2.resize(image, dsize=(INPUT_IMAGES[0], INPUT_IMAGES[1]))
		image = image.reshape(INPUT_IMAGES[0], INPUT_IMAGES[1], INPUT_IMAGES[2])
		image_cache[image_path] = image
	return image_cache[image_path]

def preprocess_images(image_names, datagen, image_cache):
	X = np.zeros(
		(len(image_names), INPUT_IMAGES[0], INPUT_IMAGES[1], INPUT_IMAGES[2]))
	for i, image_name in enumerate(image_names):
		#idx, _, _ = image_name.split('@')
		image = cached_imread(os.path.join(
			IMAGE_DATASET, image_name), image_cache)
		X[i] = datagen.random_transform(image)
	return X

def image_triple_generator(path_csv=''):
	df = pd.read_csv(path_csv, header=0)
	df = df.values.tolist()

	datagen_args = dict()
	datagen_left = ImageDataGenerator(**datagen_args)
	datagen_right = ImageDataGenerator(**datagen_args)
	image_cache = {}

	while True:
		# loop once per epoch
		num_recs = len(df)
		num_batches = num_recs // BATCH_SIZE
		for bid in range(num_batches):
			# loop once per batch
			batch_indices = df[bid * BATCH_SIZE: (bid + 1) * BATCH_SIZE]
			# make sure image data generators generate same transformations
			Xleft = preprocess_images([b[0] for b in batch_indices],
                             datagen_left, image_cache)
			Xright = preprocess_images([b[1] for b in batch_indices],
                              datagen_right, image_cache)
			Y = np.array([b[2] for b in batch_indices])
			yield [Xleft, Xright], Y

#NEW MODEL
basenet = base_network(input_shape=INPUT_IMAGES)

#DEFINE LOAD MODEL
model_1 = load_model('/home/m433788/Thesis/Baru/hapus/weights_model_pelatihan_4SR_1.hdf5',
					 custom_objects={'triplet_loss': triplet_loss})
model_2 = load_model('/home/m433788/Thesis/Baru/hapus/weights_model_pelatihan_4SR_2.hdf5',
					 custom_objects={'triplet_loss': triplet_loss})
model_3 = load_model('/home/m433788/Thesis/Baru/hapus/weights_model_pelatihan_4SR_3.hdf5',
					 custom_objects={'triplet_loss': triplet_loss})
model_4 = load_model('/home/m433788/Thesis/Baru/hapus/weights_model_pelatihan_4SR_4.hdf5',
					 custom_objects={'triplet_loss': triplet_loss})

#GET WEIGHTS
weights_1 = model_1.get_weights()
weights_2 = model_2.get_weights()
weights_3 = model_3.get_weights()
weights_4 = model_4.get_weights()

#SET WEIGHTS IN NEW MODEL
siameseNet_1 = siamese_net_1(base_model=basenet, input_shape=INPUT_IMAGES)
siameseNet_1.set_weights(weights_1)
for layer in siameseNet_1.layers:
	layer.trainable = False

siameseNet_2 = siamese_net_2(base_model=basenet, input_shape=INPUT_IMAGES)
siameseNet_2.set_weights(weights_2)
for layer in siameseNet_2.layers:
	layer.trainable = False

siameseNet_3 = siamese_net_3(base_model=basenet, input_shape=INPUT_IMAGES)
siameseNet_3.set_weights(weights_3)
for layer in siameseNet_3.layers:
	layer.trainable = False

siameseNet_4 = siamese_net_4(base_model=basenet, input_shape=INPUT_IMAGES)
siameseNet_4.set_weights(weights_4)
for layer in siameseNet_4.layers:
	layer.trainable = False

siameseNet_1.summary()

#RUNTIME STARTS
start_time = time.time()

def normalize(data):
	miny = min(data)
	maxy = max(data)
	data = [(pred - miny) / (maxy - miny) for pred in data]
	return data

#EVALUATE
def evaluate():
	ytest, ytest_1, ytest_2, ytest_3, ytest_4 = [], [], [], [], []
	s = []
	pair_generator_1 = image_triple_generator(
		'/home/m433788/Thesis/data_asli/CSV/4SR_test_1.csv')
	pair_generator_2 = image_triple_generator(
		'/home/m433788/Thesis/data_asli/CSV/4SR_test_2.csv')
	pair_generator_3 = image_triple_generator(
		'/home/m433788/Thesis/data_asli/CSV/4SR_test_3.csv')
	pair_generator_4 = image_triple_generator(
		'/home/m433788/Thesis/data_asli/CSV/4SR_test_4.csv')
	num_test_steps = NUM_PAIRS // BATCH_SIZE
	curr_test_steps = 0

	for index, (([X1_1, X2_1], Ytest), ([X1_2, X2_2], Ytest), ([X1_3, X2_3], Ytest), ([X1_4, X2_4], Ytest)) in enumerate(zip(pair_generator_1, pair_generator_2, pair_generator_3, pair_generator_4)):
		if curr_test_steps == num_test_steps:
			break

		Ytest_1 = siameseNet_1.predict([X1_1, X2_1])
		Ytest_2 = siameseNet_2.predict([X1_2, X2_2])
		Ytest_3 = siameseNet_3.predict([X1_3, X2_3])
		Ytest_4 = siameseNet_4.predict([X1_4, X2_4])

		ytest_1.extend(Ytest_1.flatten().tolist())
		ytest_2.extend(Ytest_2.flatten().tolist())
		ytest_3.extend(Ytest_3.flatten().tolist())
		ytest_4.extend(Ytest_4.flatten().tolist())

		ytest.extend(Ytest)
		curr_test_steps += 1

	#Normalize
	ytest_1 = normalize(ytest_1)
	ytest_2 = normalize(ytest_2)
	ytest_3 = normalize(ytest_3)
	ytest_4 = normalize(ytest_4)

	ytest1, ytest2 = [], []

	#Average Region 2 and 4
	for i in range(len(ytest)):
		ypred = (ytest_2[i] + ytest_4[i]) / 2
		ytest1.append(ypred)
	
	tpr, fpr, th = roc_curve(ytest, ytest1)

	threshold = np.arange(0, 1, 0.0001)
	for thd in threshold:
		ypred = []
		for pred in ytest1:
			if pred <= thd:
				ypred.append(0)
			else:
				ypred.append(1)

		prc, acc = calculate_accuracy(ypred, ytest)
		print("1. Threshold: {}, Precision: {}, and Accuracy: {}\n".format(thd, prc, acc))

	return tpr, fpr
	
tpr, fpr = evaluate()

roc_auc = auc(fpr, tpr)
plt.plot(fpr, tpr, 'g', label='AUC %s = %0.2f' %
         ('Model 4 Subregion', roc_auc))
plt.plot([0, 1], [0, 1], 'r--')
plt.legend(loc='lower right')
plt.ylabel('True Positive Rate')
plt.xlabel('False Positive Rate')
plt.title('ROC Curve')
plt.savefig('/home/m433788/Thesis/Baru/pengujian/roc_curve_4_subregion.jpg')
plt.close()

with open('AUC_Pengujian_4_Subregion.csv', 'w', newline='') as file:
	writer = csv.writer(file, delimiter='@')
	writer.writerow(["model", "fpr", "tpr"])
	for i in range(len(tpr)):
		writer.writerow(["4_subregion", fpr[i], tpr[i]])
