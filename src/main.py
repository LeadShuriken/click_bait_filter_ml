from utils import fillSet, strToSetIndex, vectorize_sequences, tokenise_data, fetchData, pad_sequence
from modelHandlers import save_model, save_embeddings, teach_model_k_fold, teach_model_hold_out
from validate import validated_rand, plot_res
from db import remove_db_duplicates

from keras.utils.vis_utils import plot_model
from keras import layers
from keras import models
from keras import regularizers
from keras import optimizers
from keras import losses

import subprocess
import numpy as np
import os

H5PY_DEFAULT_READONLY = 1

dictSize = 3400
maxLength = 25
embDim = 16
batchSize = 200
epochs = 6
folds = 6
holdout = 200
plottingValSize = 10
rebuild_data = False
save_results = False
indicate_lr = False
t_board_save = True
lr_spike_scaler = .2
lr_scale_init = 1e-3
padding = 'post'

if rebuild_data:
    # REMOVING DB DUPLICATES
    remove_db_duplicates()

    # Exporting data
    process = subprocess.run(
        ['./get_data.sh', os.environ['MONGODB_POSITIVE']], cwd=r'./../')
    process = subprocess.run(
        ['./get_data.sh', os.environ['MONGODB_NEGATIVE']], cwd=r'./../')

# # Legacy Fetching Data
# out_data_set = np.array([])
# out_data_positive_raw, out_data_set = fillSet(
#     out_data_set, '../data/click_bait_db.json')
# out_data_negative_raw, out_data_set = fillSet(
#     out_data_set, '../data/click_bait_db_negative.json')
# out_data_set = {out_data_set[i]: i + 1 for i in range(0, len(out_data_set))}

# # Legacy To indexes
# out_data_positive = strToSetIndex(
#     out_data_set, out_data_positive_raw)
# out_data_negative = strToSetIndex(
#     out_data_set, out_data_negative_raw)

out_data_positive_raw = fetchData('../data/click_bait_db.json')
out_data_negative_raw = fetchData('../data/click_bait_db_negative.json')
out_data_set, out_data_positive, out_data_negative = tokenise_data(
    out_data_positive_raw, out_data_negative_raw,
    dictSize)
reverse_word_index = dict([(value, key)
                           for (key, value) in out_data_set.items()])

# Removing doubles ... happens
for i, A in np.ndenumerate(out_data_positive):
    for n, B in np.ndenumerate(out_data_negative):
        if np.array_equal(A, B):
            out_data_positive = np.delete(out_data_positive, i)
            out_data_negative = np.delete(out_data_negative, n)

# Mixing
seedInt = np.random.randint(0, 100)
train_data = np.concatenate((
    out_data_positive,
    out_data_negative))
np.random.seed(seedInt)
np.random.shuffle(train_data)

train_labels = np.concatenate((
    np.ones(len(out_data_positive)),
    np.zeros(len(out_data_negative))))
np.random.seed(seedInt)
np.random.shuffle(train_labels)

# Vectorizing Data and Labels
# x_train = vectorize_sequences(train_data, dictSize)
# y_train = np.asarray(train_labels).astype('float32')
x_train = pad_sequence(train_data, maxLength, padding)
y_train = np.asarray(train_labels).astype('float32')

partial_x_train = x_train[:plottingValSize]
partial_y_train = y_train[:plottingValSize]
train_data = train_data[:plottingValSize]

x_train = x_train[plottingValSize:]
y_train = y_train[plottingValSize:]

# Model
model = models.Sequential([
    layers.Embedding(dictSize, embDim, input_length=maxLength, name='input'),
    layers.Bidirectional(layers.LSTM(64, return_sequences=True)),
    layers.Bidirectional(layers.LSTM(32)),
    layers.Dense(24, kernel_regularizer=regularizers.l2(
        0.001), activation='relu'),
    layers.Dropout(.01),
    layers.Dense(6, kernel_regularizer=regularizers.l2(
        0.001), activation='relu'),
    layers.Dense(1, activation='sigmoid', name='output')], name='click_bait_model')

# apt-get install graphviz just pip not gona cut it
plot_model(model, show_shapes=True, show_layer_names=True,
           to_file='../model.png')

optimizers = optimizers.Adam(learning_rate=lr_scale_init)

model.compile(optimizer=optimizers,
              loss='binary_crossentropy', metrics=['acc'])

model.summary()

history, model, score = teach_model_k_fold(
    model, x_train, y_train, folds, epochs, batchSize,
    lr_spike_scaler=lr_spike_scaler, lr_scale_init=lr_scale_init, indicate_lr=indicate_lr, t_board=t_board_save)
# history, model, score = teach_model_hold_out(
#     model, x_train, y_train, holdout, epochs, batchSize,
#     lr_spike_scaler=lr_spike_scaler, lr_scale_init=lr_scale_init, indicate_lr=indicate_lr, t_board=t_board_save)

plot_res(history)
validated_rand(model, reverse_word_index, partial_x_train,
               partial_y_train, train_data)
print(score)

if not indicate_lr and save_results:
    save_model(model, out_data_set)
    save_embeddings(model, reverse_word_index, dictSize)
    # https://projector.tensorflow.org - fing score
    # saved_model_cli show --dir ../model/modeljava/ --all