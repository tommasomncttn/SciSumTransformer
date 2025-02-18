!pip install optuna

# ===========================================
# ||                                       ||
# ||       Section 1: Importing modules    ||
# ||                                       ||
# ===========================================

from fastai.text.all import *
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
import optuna

# ===========================================
# ||                                       ||
# ||       Section 2: Getting dataframes   ||
# ||                    and dataloader     ||
# ||                                       ||
# ===========================================

# Read in a CSV files

train_df = pd.read_csv("/content/drive/MyDrive/ML_proj/zaazazza/augmented_cleaned_train_df.csv")
test_df = pd.read_csv("/content/drive/MyDrive/ML_proj/zaazazza/clean_test_data.csv")
validation_df =  pd.read_csv("/content/drive/MyDrive/ML_proj/zaazazza/clean_validation_data.csv")

# Drop not needed columns

train_df = train_df.drop(train_df.columns[0:5], axis=1)
validation_df = validation_df.drop(validation_df.columns[0:5], axis=1)
test_df = test_df.drop(test_df.columns[0:5], axis=1)

# Create a data loader for text data using the "TextDataLoaders" class from the fastai library.

dls = TextDataLoaders.from_df(train_df, valid_df=validation_df, path='.', valid_pct=0.2, seed=None,
                              text_col=0, label_col=1, label_delim=None,
                              y_block=None, text_vocab=None, is_lm=False,
                              valid_col=None, tok_tfm=None,
                              tok_text_col='text', seq_len=72)

# ===========================================
# ||                                       ||
# ||       Section 3: Hyperparameter       ||
# ||                             tuning    ||
# ||                                       ||
# ===========================================

# Define a function that trains the model on specific hyperparams and returns the f1 score

def objective(trial):
    # Define the search space for hyperparameters
    dropout = trial.suggest_uniform('dropout', 0.2, 0.8)
    n_epochs = trial.suggest_int('n_epochs', 2, 10)
    learning_rate = trial.suggest_loguniform('learning_rate', 1e-5, 1e-1)

    # Create a text classification learner with the suggested hyperparameters
    learn = text_classifier_learner(dls, AWD_LSTM, drop_mult=dropout, metrics=accuracy)

    # Fine-tune the neural network for the suggested number of epochs using stochastic gradient descent
    learn.fine_tune(n_epochs, learning_rate, cbs=[ShowGraphCallback()])

    # Get the predicted probabilities for the validation data using the trained model.
    val_dl = dls.test_dl(validation_df['text'])
    val_preds, _ = learn.get_preds(dl=val_dl)

    # Get the predicted labels for the validation data.
    val_predicted_labels = val_preds.argmax(dim=1)

    # Compute the f1 score of the model on the validation data using the `f1_score` function.
    val_f1 = f1_score(validation_df["target"].values, val_predicted_labels)

    # Return the f1 score as the value to optimize
    return val_f1

# Create an optuna study and optimize the objective function 
#(we are maximizing the f1 socore)
study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler())
study.optimize(objective, n_trials=30)

# Print the best set of hyperparameters found by optuna and the corresponding f1 score on the validation data.
print('Best trial:')
best_trial = study.best_trial
print(f'  Value: {best_trial.value:.5f}')
print('  Params: ')
for key, value in best_trial.params.items():
    print(f'    {key}: {value}')

# Train the model with the best hyperparameters found by optuna and evaluate it on the test data.
best_dropout = best_trial.params['dropout']
best_n_epochs = best_trial.params['n_epochs']
best_learning_rate = best_trial.params['learning_rate']

# ===========================================
# ||                                       ||
# ||       Section 4: Train the model      ||
# ||                                       ||
# ===========================================

# Create a text classification learner using the fastai library.

learn = text_classifier_learner(dls, AWD_LSTM, drop_mult=best_dropout, metrics=accuracy)

# Fine-tune the neural network for four epochs using stochastic gradient descent

learn.fine_tune(best_n_epochs, best_learning_rate, cbs=[ShowGraphCallback()])

# ===========================================
# ||                                       ||
# ||       Section 5: Testing the model    ||
# ||                                       ||
# ===========================================

# Create a test dataloader from the test data using the `test_dl` method of the `dls` dataloaders object.
test_dl = dls.test_dl(test_df['text'])

# Get the predicted probabilities for the test data using the trained model.
preds, _ = learn.get_preds(dl=test_dl)

# Get the predicted labels for the test data.
predicted_labels = preds.argmax(dim=1)

# Convert the predicted labels to Python list and get the corresponding class names.
predicted_classes = [dls.vocab[i] for i in predicted_labels]

# Convert the predicted classes list to a tensor.
predicted_classes_tensor = torch.tensor(predicted_labels)

# Reshape the predicted tensor to have the same shape as the target tensor.
predicted_classes_tensor = predicted_classes_tensor.unsqueeze(1)

# Convert the target labels to a tensor.
target_tensor = torch.tensor(test_df["target"].values)

# Compute the accuracy and f1 score of the model on the test data using the `accuracy` and `f1_score` functions.
acc = accuracy(predicted_classes_tensor, target_tensor)
f1 = f1_score(target_tensor, predicted_classes_tensor)

# Print the accuracy and f1 score of the model on the test data.
print(f"Test accuracy: {acc}")
print(f"Test f1 score: {f1}")

# ===========================================
# ||                                       ||
# ||       Section 6: Export the model     ||
# ||                                       ||
# ===========================================

learn.export("AWD_LSTM_aug.pkl")
