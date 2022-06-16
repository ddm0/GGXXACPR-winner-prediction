import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.layers import Normalization
from tensorflow.keras.layers import CategoryEncoding

#Open and read our replay data
data_path = "replay_data.csv"
data = pd.read_csv(data_path)

#Create the training and validation dataframes
val_df = data.sample(frac=0.2, random_state=13)
train_df = data.drop(val_df.index)

#A function that converts a dataframe into a dataset
def df_to_ds(df):
    df = df.copy()
    label = df.pop("MatchResult")
    ds = tf.data.Dataset.from_tensors((dict(df), label))
    ds = ds.shuffle(buffer_size=len(df))
    return ds

#Create our validation and training datasets
val_ds = df_to_ds(val_df)
train_ds = df_to_ds(train_df)

#Setup our features
#name, num_tokens
categorical_feature_list = [
    ["Character1", 26],
    ["Character2", 26],
    ["Action1", 377],
    ["Action2", 377]
    ]

#Setup our numerical features.
#name, integer size
numerical_feature_list = [
    ["Frame","uint32"],
    ["MatchCountdown","uint32"],
    ["Burst1","uint16"],
    ["Burst2","uint16"],
    ["Guard1","int16"],
    ["Guard2","int16"],
    ["Health1","uint16"],
    ["Health2","uint16"],
    ["RoundTimer","uint16"],
    ["PosX1","int32"],
    ["PosX2","int32"],
    ["PosY1","int32"],
    ["PosY2","int32"],
    ["RoundsWon1","uint8"],
    ["RoundsWon2","uint8"],
    ["Stun1","uint16"],
    ["Stun2","uint16"],
    ["Tension1","uint16"],
    ["Tension2","uint16"]
    ]

feature_inputs = []
encoded_features = []

#Encode our categorical features
for item in categorical_feature_list:
    #Create feature
    feature = keras.Input(shape=(1,), name=item[0], dtype="int32")
    feature_inputs.append(feature)

    #One hot encode
    encoder = CategoryEncoding(num_tokens=item[1], output_mode="one_hot")
    encoded_feature = encoder(feature)
    
    #Add to list
    encoded_features.append(encoded_feature)

#Encode our numerical features
for item in numerical_feature_list:
    #Create feature
    feature = keras.Input(shape=(1,), name=item[0], dtype=item[1])
    feature_inputs.append(feature)

    #Create feature dataset
    feature_ds = train_ds.map(lambda x, y: x[feature.name])
    feature_ds = feature_ds.map(lambda x: tf.expand_dims(x, -1))

    #Normalize features
    normalize = Normalization()
    normalize.adapt(feature_ds)
    encoded_feature = normalize(feature)
    
    #Add to list
    encoded_features.append(encoded_feature)

#Concatenate our features
features_tensor = layers.concatenate(encoded_features)

#Create our neural network
x = layers.Dense(32, activation="relu")(features_tensor)
x = layers.Dropout(0.5)(x)
out = layers.Dense(1, activation="sigmoid")(x)

#Create and train the model
model = keras.Model(feature_inputs, out)
model.compile(optimizer="adam",loss="binary_crossentropy", metrics=["accuracy"])
model.fit(train_ds, epochs=100, validation_data=val_ds)
