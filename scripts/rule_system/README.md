# Rules

The first step to train new rule system, or evaluate the existing rules is to generate the AMR graphs.

To prepare the data, run the potato_runner.py script.

```
    python3 potato_runner.py --amr AMR
                             --text TEXT
                             --lang {en,de}
                             [--feature FEATURE]
                             [--save SAVE]
                             [--train]
```

Once you have the output of this, you can run the frontend if you want to train or to evaluate existing datasets.

```
    streamlit run app.py -- 
                         -t train_dataset 
                         -v val_dataset 
                         -g amr
                         -sr features.json
                         [-hr HAND_WRITTEN]
```

To generate the predictions on the dataset, run:

```
    python3 evaluate.py 
                        -t amr
                        -f saved_features.json 
                        -d test_dataset
```