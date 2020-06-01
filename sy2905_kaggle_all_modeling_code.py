# -*- coding: utf-8 -*-
"""sy2905_kaggle_all_modeling_code.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/17M14Nx2SVj0ybpNiwMJqhDw9pT1xLiCa

# Shoya Yoshida (sy2905) 

This notebook contains all of the modelling code I used. I ended up with 10+ notebooks, so I will concatenate them all into this one single file for ease.
"""

from google.colab import drive
drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# % cd drive/My Drive/ML/kaggle
# %tensorflow_version 1.x

train_folder= 'data/train/'
val_folder = 'data/valid/'
test_folder = 'data/test/'

import pandas as pd 
import numpy as np 
import math
from keras.preprocessing.image import ImageDataGenerator

"""# Setting up the ImageDataGenerator"""

IMAGE_SHAPE = 224
train_datagenerator = ImageDataGenerator(
    rescale = 1./255,
    zoom_range = [0.8,1.2],
    horizontal_flip = True, 
    width_shift_range=0.2,
    height_shift_range=0.2,
    brightness_range = (0.7,1.3),
    rotation_range = 20
)

test_and_val_datagenerator = ImageDataGenerator(
    rescale=1./255
)

training_data_gen = train_datagenerator.flow_from_directory(
    train_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=32,
    class_mode='categorical'
)

validation_data_gen = test_and_val_datagenerator.flow_from_directory(
    val_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=32,
    class_mode='categorical'
)

test_data_gen = test_and_val_datagenerator.flow_from_directory(
    test_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=32,
    class_mode=None,
    shuffle=False
)

"""# Visualizing the Images"""

# example of horizontal shift image augmentation
from numpy import expand_dims
from keras.preprocessing.image import load_img
from keras.preprocessing.image import img_to_array
from keras.preprocessing.image import ImageDataGenerator
from matplotlib import pyplot as plt


training_data_print = train_datagenerator.flow_from_directory(
    train_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=16,
    class_mode='categorical'
)

all_labels=['bacterial','covid','normal','viral']

t_x, t_y = next(training_data_print)
fig, m_axs = plt.subplots(4, 4, figsize = (16, 16))
for (c_x, c_y, c_ax) in zip(t_x, t_y, m_axs.flatten()):
    c_ax.imshow(c_x[:,:,0], cmap = 'bone', vmin = -1.5, vmax = 1.5)
    c_ax.set_title(', '.join([n_class for n_class, n_score in zip(all_labels, c_y) 
                             if n_score>0.5]))
    c_ax.axis('off')

pyplot.show();

"""# Baseline Simple Model"""

model = Sequential()
model.add(Conv2D(32, (3, 3), input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3),activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(32, (3, 3),activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(64, (3, 3),activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(128, (3, 3),activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Flatten())
model.add(Dense(64,activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(4,activation='softmax'))


model.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint

checkpoint = ModelCheckpoint("model_checkpoints/v0/simple_model_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)
history = model.fit_generator(
    training_data_gen,
    epochs=200, #300
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1
    ,class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""#V1: ChexNet Finetuning"""

# taken from https://github.com/brucechou1983/CheXNet-Keras/blob/master/models/keras.py in order to do transfer learning on CheXNet 

import importlib
from keras.layers import Input
from keras.layers.core import Dense
from keras.models import Model


class ModelFactory:
    """
    Model facotry for Keras default models
    """

    def __init__(self):
        self.models_ = dict(
            VGG16=dict(
                input_shape=(224, 224, 3),
                module_name="vgg16",
                last_conv_layer="block5_conv3",
            ),
            VGG19=dict(
                input_shape=(224, 224, 3),
                module_name="vgg19",
                last_conv_layer="block5_conv4",
            ),
            DenseNet121=dict(
                input_shape=(224, 224, 3),
                module_name="densenet",
                last_conv_layer="bn",
            ),
            ResNet50=dict(
                input_shape=(224, 224, 3),
                module_name="resnet50",
                last_conv_layer="activation_49",
            ),
            InceptionV3=dict(
                input_shape=(299, 299, 3),
                module_name="inception_v3",
                last_conv_layer="mixed10",
            ),
            InceptionResNetV2=dict(
                input_shape=(299, 299, 3),
                module_name="inception_resnet_v2",
                last_conv_layer="conv_7b_ac",
            ),
            NASNetMobile=dict(
                input_shape=(224, 224, 3),
                module_name="nasnet",
                last_conv_layer="activation_188",
            ),
            NASNetLarge=dict(
                input_shape=(331, 331, 3),
                module_name="nasnet",
                last_conv_layer="activation_260",
            ),
        )

    def get_last_conv_layer(self, model_name):
        return self.models_[model_name]["last_conv_layer"]

    def get_input_size(self, model_name):
        return self.models_[model_name]["input_shape"][:2]

    def get_model(self, class_len=14, model_name="DenseNet121", use_base_weights=True,
                  weights_path=None, input_shape=None):

        if use_base_weights is True:
            base_weights = "imagenet"
        else:
            base_weights = None

        base_model_class = getattr(
            importlib.import_module(
                f"keras.applications.{self.models_[model_name]['module_name']}"
            ),
            model_name)

        if input_shape is None:
            input_shape = self.models_[model_name]["input_shape"]

        img_input = Input(shape=input_shape)

        base_model = base_model_class(
            include_top=False,
            input_tensor=img_input,
            input_shape=input_shape,
            weights=base_weights,
            pooling="avg")
        x = base_model.output
        predictions = Dense(class_len, activation="sigmoid", name="predictions")(x)
        model = Model(inputs=img_input, outputs=predictions)

        if weights_path == "":
            weights_path = None

        if weights_path is not None:
            print(f"load model weights_path: {weights_path}")
            model.load_weights(weights_path)
        return model

chexnet_model = ModelFactory().get_model()
chexnet_model.load_weights('CheXNet_weights.h5')

from keras.models import Sequential
from keras.applications.vgg16 import VGG16
from keras.preprocessing.image import ImageDataGenerator
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer

chexnet_output = chexnet_model.layers[-2].output
output = Dense(32,activation='relu')(chexnet_output)
output = Dropout(0.5)(output)
output = Dense(4,activation='softmax')(output)

# output = Dropout(0.5)(chexnet_output)
# output = Dense(4,activation='softmax')(output)

# output ÷= Dense(4,activation='softmax')(chexnet_output)

model = Model(inputs=chexnet_model.inputs,outputs=output)
model.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])
model.summary()

from keras.callbacks import ModelCheckpoint

checkpoint = ModelCheckpoint("model_checkpoints/v1/chexnet_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",monitor='val_loss',save_best_only=True)
history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""# V2: CheXNet 2"""

chexnet_output = chexnet_model.layers[-2].output
output = Dense(256,activation='relu')(chexnet_output)
output = Dropout(0.7)(output)
output = Dense(32,activation='relu')(output)
output = Dropout(0.5)(output)
output = Dense(4,activation='softmax')(output)

# output = Dropout(0.5)(chexnet_output)
# output = Dense(4,activation='softmax')(output)

# output ÷= Dense(4,activation='softmax')(chexnet_output)

model = Model(inputs=chexnet_model.inputs,outputs=output)

# for model_layer in model.layers[1:6]:
#     model_layer.trainable = False

model.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])
model.summary()

from keras.callbacks import ModelCheckpoint

checkpoint = ModelCheckpoint("model_checkpoints/v2/chexnet_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)
history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""#V3: CheXNet 3"""

chexnet_output = chexnet_model.layers[-2].output
# output = Dense(32,activation='relu')(chexnet_output)
# output = Dropout(0.5)(output)
# output = Dense(4,activation='softmax')(output)

# # output = Dropout(0.5)(chexnet_output)
# # output = Dense(4,activation='softmax')(output)

output = Dense(4,activation='softmax')(chexnet_output)

model = Model(inputs=chexnet_model.inputs,outputs=output)
model.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy'])
model.summary()

checkpoint = ModelCheckpoint("model_checkpoints/v2.5/chexnet_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)
history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""# V5: VGG FineTune"""

from keras import Sequential, Model
from keras.applications.vgg16 import VGG16
from keras.preprocessing.image import ImageDataGenerator
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer,ZeroPadding2D

model = Sequential()
model.add(ZeroPadding2D((1,1),input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3)))
model.add(Conv2D(64, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(64, (3, 3), activation='relu'))
model.add(MaxPooling2D((2,2), strides=(2,2)))

model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(128, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(128, (3, 3), activation='relu'))
model.add(MaxPooling2D((2,2), strides=(2,2)))

model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(256, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(256, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(256, (3, 3), activation='relu'))
model.add(MaxPooling2D((2,2), strides=(2,2)))

model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(512, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(512, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(512, (3, 3), activation='relu'))
model.add(MaxPooling2D((2,2), strides=(2,2)))

model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(512, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(512, (3, 3), activation='relu'))
model.add(ZeroPadding2D((1,1)))
model.add(Conv2D(512, (3, 3), activation='relu'))
model.add(MaxPooling2D((2,2), strides=(2,2)))

model.add(Flatten())
model.add(Dense(4096, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(4096, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(4, activation='softmax'))


from keras.optimizers import Adam 
model.compile(optimizer=Adam(lr=3e-5),loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint("model_checkpoints/v5/vgg_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)

history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""#V6: DenseNet121 Finetune"""

from keras.applications import DenseNet121
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer
from keras.optimizers import Adam

densenet = DenseNet121(include_top=False,input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3))

x = densenet.layers[-1].output 
x = Flatten()(x)
x = Dense(512,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(256,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(4,activation='softmax')(x)

model = Model(inputs=densenet.inputs,output=x)
model.compile(optimizer=Adam(lr=3e-5),loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint("model_checkpoints/v7/densenet121_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)

history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""#V7: DenseNet169 FineTune"""

from keras.applications import DenseNet121,DenseNet169,DenseNet201
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer
from keras.optimizers import Adam
from keras import Sequential, Model

densenet = DenseNet169(include_top=False,input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3))

x = densenet.layers[-1].output 
x = Flatten()(x)
x = Dense(512,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(256,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(4,activation='softmax')(x)

model = Model(inputs=densenet.inputs,output=x)
model.compile(optimizer=Adam(lr=3e-5),loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint("model_checkpoints/v8/densenet169_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)

history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""# V8: DenseNet201 Finetune"""

from keras.applications import DenseNet121,DenseNet169,DenseNet201
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer
from keras.optimizers import Adam
from keras import Sequential, Model

densenet = DenseNet201(include_top=False,input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3))

x = densenet.layers[-1].output 
x = Flatten()(x)
x = Dense(512,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(256,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(4,activation='softmax')(x)

model = Model(inputs=densenet.inputs,output=x)
model.compile(optimizer=Adam(lr=3e-5),loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint("model_checkpoints/v9/densenet201_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)

history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""#V9 ResNet50 Finetune"""

from keras.applications import ResNet50
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer
from keras.optimizers import Adam
from keras import Sequential, Model

resnet = ResNet50(include_top=False,input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3))

x = resnet.layers[-1].output 
x = Flatten()(x)
x = Dense(512,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(256,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(4,activation='softmax')(x)

model = Model(inputs=resnet.inputs,output=x)
model.compile(optimizer=Adam(lr=3e-5),loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint("model_checkpoints/v10/resnet50_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)

history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""# V10 Finetune ResNet101"""

from keras.applications import ResNet101
from keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Input, Flatten,GlobalMaxPooling2D,BatchNormalization,InputLayer
from keras.optimizers import Adam
from keras import Sequential, Model

resnet = ResNet101(include_top=False,input_shape=(IMAGE_SHAPE,IMAGE_SHAPE,3))

x = resnet.layers[-1].output 
x = Flatten()(x)
x = Dense(512,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(256,activation='relu')(x)
x = Dropout(0.5)(x)
x = Dense(4,activation='softmax')(x)

model = Model(inputs=resnet.inputs,output=x)
model.compile(optimizer=Adam(lr=3e-5),loss='categorical_crossentropy',metrics=['accuracy'],weighted_metrics=['accuracy'])

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint("model_checkpoints/v11/resnet101_finetune_weights_{epoch:02d}-{val_accuracy:.2f}.hdf5",save_best_only=True)

history = model.fit_generator(
    training_data_gen,
    epochs= 400,
    validation_data=validation_data_gen,
    validation_steps = 113//32,
    steps_per_epoch= math.ceil(1127/32),
    verbose=1,
    class_weight = {
        0: 1.,
        1: 5., # weigh covid weights as 5x more than the others 
        2: 1.,
        3: 1.
    },
    callbacks=[checkpoint]
)

"""# Ensembling all of the Predictions"""

from keras.models import load_model

checkpoints_path = [            
   'model_checkpoints/v1/chexnet_finetune_weights_276-0.81.hdf5',
   'model_checkpoints/v2/chexnet_finetune_weights_320-0.83.hdf5',
   'model_checkpoints/v2.5/chexnet_finetune_weights_126-0.83.hdf5',
   'model_checkpoints/v3/inception_finetune_weights_245-0.75.hdf5',
   'model_checkpoints/v5/vgg_finetune_weights_360-0.84.hdf5',
   'model_checkpoints/v7/densenet121_finetune_weights_159-0.89.hdf5',
   'model_checkpoints/v8/densenet169_finetune_weights_54-0.83.hdf5',
   'model_checkpoints/v9/densenet201_finetune_weights_74-0.90.hdf5',
   'model_checkpoints/v10/resnet50_finetune_weights_96-0.85.hdf5',
   'model_checkpoints/v11/resnet101_finetune_weights_73-0.83.hdf5'
]
ensemble_models = [] 
for checkpoint_path in checkpoints_path:
    print(checkpoint_path)
    ensemble_models.append(load_model(checkpoint_path))

save_file_names = [
    'chexnet_finetune_1_v1.csv',
    'chexnet_finetune_2_v1.csv',
    'chexnet_finetune_2.5_v1.csv',
    'inception_finetune_v1.csv',
    'vgg_finetune_v1.csv',
    'densenet121_finetune_v1.csv',
    'densenet169_finetune_v1.csv',
    'densenet201_finetune_v1.csv',
    'resnet50_finetune_v1.csv',
    'resnet101_finetune_v1.csv'
]

all_preds = [] 
for i,trained_model in enumerate(ensemble_models):
    print(save_file_names[i])
    test_data_gen.reset()
    pred_probs = trained_model.predict_generator(test_data_gen)

    pred_prob_df = pd.DataFrame(pred_probs)
    pred_prob_df.to_csv('output/probs/v2/pred_probs_{}'.format(save_file_names[i]))
    all_preds.append(pred_probs)

import numpy as np 
# first the prediction output of each model 
labels = (validation_data_gen.class_indices)
labels = dict((v,k) for k,v in labels.items())

test_filenames = test_data_gen.filenames

for i,pred_set in enumerate(all_preds):
    # pred_prob_df = pd.DataFrame(pred_probs)
    # pred_prob_df.to_csv('output/probs/pred_probs_{}'.format(save_file_names[i])) # check if the chexnet finetunes are too close to be useful or not? 

    predicted_class_indices = np.argmax(pred_set,axis=1)    
    predictions = [labels[k] for k in predicted_class_indices]
    output_df = pd.DataFrame({'filename':test_filenames,'label':predictions})
    output_df['Id'] = output_df['filename'].str.extract('(\d+)')
    output_df = output_df[['Id','label']].copy()
    output_df['Id'] = output_df['Id'].astype(int)
    output_df = output_df.sort_values('Id')
    output_df.to_csv('output/preds/v2/{}'.format(save_file_names[i]),index=False)

average_probs = [] 
for i in range(all_preds[0].shape[0]):
    row_arr = []
    for p in all_preds:
        row_arr.append(p[i])
    row_probs = np.vstack(tuple(row_arr))
    avg_prob = np.mean(row_probs,axis=0)
    average_probs.append(avg_prob)

average_probs_arr = np.array(average_probs)
average_probs_arr

ensemble_pred_indices = np.argmax(average_probs_arr,axis=1)
labels = (validation_data_gen.class_indices)
labels = dict((v,k) for k,v in labels.items())
# print(labels)
predictions = [labels[k] for k in ensemble_pred_indices]
# predictions

test_filenames = test_data_gen.filenames
output_df = pd.DataFrame({'filename':test_filenames,'label':predictions})
output_df['Id'] = output_df['filename'].str.extract('(\d+)')
output_df = output_df[['Id','label']].copy()
output_df['Id'] = output_df['Id'].astype(int)
output_df = output_df.sort_values('Id')
output_df

output_df.to_csv('output/preds/v2/ensembled_approach_v2.csv',index=False)

"""# Error Analysis on the Validation Set"""

train_datagenerator = ImageDataGenerator(
    rescale = 1./255,
    zoom_range = [0.8,1.2],
    horizontal_flip = True, 
    width_shift_range=0.2,
    height_shift_range=0.2,
    brightness_range = (0.7,1.3),
    rotation_range = 20
)

test_and_val_datagenerator = ImageDataGenerator(
    rescale=1./255
)

training_data_gen = train_datagenerator.flow_from_directory(
    train_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=32,
    class_mode='categorical'
)

validation_data_gen = test_and_val_datagenerator.flow_from_directory(
    val_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=32,
    class_mode='categorical',
    shuffle=False
)

test_data_gen = test_and_val_datagenerator.flow_from_directory(
    test_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=32,
    class_mode=None,
    shuffle=False
)

from keras.models import load_model

checkpoints_path = [            
   'model_checkpoints/v1/chexnet_finetune_weights_276-0.81.hdf5',
   'model_checkpoints/v2/chexnet_finetune_weights_320-0.83.hdf5',
   'model_checkpoints/v2.5/chexnet_finetune_weights_126-0.83.hdf5',
   'model_checkpoints/v3/inception_finetune_weights_245-0.75.hdf5',
   'model_checkpoints/v5/vgg_finetune_weights_360-0.84.hdf5',
   'model_checkpoints/v7/densenet121_finetune_weights_159-0.89.hdf5',
   'model_checkpoints/v8/densenet169_finetune_weights_54-0.83.hdf5',
   'model_checkpoints/v9/densenet201_finetune_weights_74-0.90.hdf5',
   'model_checkpoints/v10/resnet50_finetune_weights_96-0.85.hdf5',
   'model_checkpoints/v11/resnet101_finetune_weights_73-0.83.hdf5'
]
ensemble_models = [] 
for checkpoint_path in checkpoints_path:
    print(checkpoint_path)
    ensemble_models.append(load_model(checkpoint_path))

all_preds = [] 
for i,trained_model in enumerate(ensemble_models):
    validation_data_gen.reset()
    pred_probs = trained_model.predict_generator(validation_data_gen)

    all_preds.append(pred_probs)

import numpy as np 
# first the prediction output of each model 
average_probs = [] 
for i in range(all_preds[0].shape[0]):
    row_arr = []
    for p in all_preds:
        row_arr.append(p[i])
    row_probs = np.vstack(tuple(row_arr))
    avg_prob = np.mean(row_probs,axis=0)
    average_probs.append(avg_prob)

average_probs_arr = np.array(average_probs)
average_probs_arr

ensemble_pred_indices = np.argmax(average_probs_arr,axis=1)
labels = (validation_data_gen.class_indices)
labels = dict((v,k) for k,v in labels.items())
# print(labels)
predictions = [labels[k] for k in ensemble_pred_indices]
# predictions

test_filenames = validation_data_gen.filenames
output_df = pd.DataFrame({'filename':test_filenames,'label':predictions,'label_index':ensemble_pred_indices})
output_df['Id'] = output_df['filename'].str.extract('(\d+)')
output_df = output_df[['Id','label','label_index']].copy()
output_df['Id'] = output_df['Id'].astype(int)
# output_df = output_df.sort_values('Id')
output_df.head(10)

val_real_labels = list(validation_data_gen.labels)
output_df['real_label'] = val_real_labels
output_df

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score,confusion_matrix

print('recall: {}'.format(recall_score(output_df['real_label'],output_df['label_index'],average='macro')))
print('precision: {}'.format(precision_score(output_df['real_label'],output_df['label_index'],average='macro')))
print('f1-score: {}'.format(f1_score(output_df['real_label'],output_df['label_index'],average='macro')))

cf_unnormalized = confusion_matrix(output_df['real_label'],output_df['label_index'])
cf = confusion_matrix(output_df['real_label'],output_df['label_index'],normalize='true')

cf_normalized_df = pd.DataFrame(cf,columns=list(validation_data_gen.class_indices.keys()))
cf_normalized_df['True Label'] = list(validation_data_gen.class_indices.keys())
cf_normalized_df.set_index('True Label', drop=True)
cf_df = pd.DataFrame(cf_unnormalized,columns=list(validation_data_gen.class_indices.keys()))
cf_df['True Label'] = list(validation_data_gen.class_indices.keys())
cf_df.set_index('True Label', drop=True)

"""# Analyzing the Output of the Learned Model with LIME"""

! pip install lime

from keras.preprocessing import image
from keras.applications.imagenet_utils import decode_predictions
from skimage.io import imread
import matplotlib.pyplot as plt
import numpy as np 
import keras 
import os 
import lime 
from lime import lime_image
from skimage.segmentation import mark_boundaries

# getting finetuned densenet201
best_model = ensemble_models[7]


sample_data_gen = test_and_val_datagenerator.flow_from_directory(
    val_folder,
    target_size=(IMAGE_SHAPE,IMAGE_SHAPE),
    batch_size=1,
    class_mode='categorical',
    shuffle=True
)

index_to_class = {
    0:'bacterial',
    1:'covid',
    2:'normal',
    3:'viral'
}

explainer = lime_image.LimeImageExplainer()

sample_data_gen.reset()
for i in range(10):
    image, y = sample_data_gen.next()
    y_real_label = index_to_class[np.argmax(y)]
    explanation = explainer.explain_instance(image[0], best_model.predict, top_labels=4, num_samples=1000)
    temp, mask = explanation.get_image_and_mask(explanation.top_labels[0], positive_only=True, num_features=5, hide_rest=False)
    print("real label is {}".format(y_real_label))
    plt.imshow(mark_boundaries(temp / 2 + 0.5, mask))
    plt.show();
    plt.clf()
    plt.cla()
    plt.close()