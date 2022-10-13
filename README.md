# offensive_text

### Data normalization

Normalise the list of files; train and test:
```
python3 read_data.py 
                     --to_normalise LIST_OF_FILES
                     --normalised_path LIST_OF_NORMALISED_PATHS_IN_ORDER
                     --language en
```
Concatenate files:
```
python3 read_data.py 
                     --normalised_path LIST_OF_NORMALISED_PATHS
                     --concat CONCATENATED_PATH
```

### Run models
Change the data paths in the config files to direct 
to the concatenated normalised path and the test.json
to direct to the normalised test files.

Important note: if the data_path parameter is a single file,
it will be split into train and validation. 
If you want the model to train on the whole data, 
you have to make it the first element of a list, like you can see
in the configs/English_train_whole_data.json file.
```
python3 run_configs.py 
                     --mode train
                     --configs ./configs 
                     --test_files test.json
```

After the training process finished, the best systems
will give a prediction on the given test files. 
These will be put into the predicted dictionary.
The training process is the same for the categorical subtask.

Run the following script to get the final result:
```
python3 run_configs.py 
                     --mode result
                     --configs ./configs 
                     --test_files test.json
```
If the test file does not contain labels, add the --test argument
to the above command.

## Rule system

Find the rule systems as well as their performance under _scripts/rule_system_

## Results on the samples

| **Test** | **System**                     | **TP** | **TN** | **FP** | **FN** | **Precision** | **Recall** | **F1** |
|-------------------|-----------------------------------------|-----------------|-----------------|-----------------|-----------------|-------------------|------------------|-----------------|
|     EN              | EN-all                                  | 64              | 23              | 11              | 2               | 85.3              | 97.0             | 90.8            |
|     EN              | DE-all-multi                            | 12              | 32              | 2               | 54              | 85.7              | 18.2             | 30.0            |
|     EN              | Rules                                   | 32              | 32              | 2               | 34              | 94.1              | 48.5             | 64.0            |
|     EN              | EN-all $\cup$ Rules                     | 64              | 22              | 12              | 2               | 84.2              | 97.0             | 90.1            |
|     EN              | DE-all-multi $\cup$ Rules               | 35              | 30              | 4               | 31              | 89.7              | 53.0             | 66.7            |
|     EN              | EN-all $\cup$ DE-all-multi              | 64              | 22              | 12              | 2               | 84.2              | 97.0             | 90.1            |
|     EN              | EN-all $\cup$ DE-all-multi $\cup$ Rules | 64              | 21              | 13              | 2               | 83.1              | 97.0             | 89.5            |
|     DE              | DE-all                                  | 12              | 62              | 5               | 21              | 70.6              | 36.4             | 48.0            |
|     DE              | EN-all-multi                            | 10              | 63              | 4               | 23              | 71.4              | 30.3             | 42.6            |
|     DE              | Rules                                   | 4               | 66              | 1               | 29              | 80.0              | 12.1             | 21.1            |
|     DE              | DE-all $\cup$ Rules                     | 13              | 61              | 6               | 20              | 68.4              | 39.4             | 50.0            |
|     DE              | EN-all-multi $\cup$ Rules               | 12              | 62              | 5               | 21              | 70.6              | 36.4             | 48.0            |
|     DE              | DE-all $\cup$ EN-all-multi              | 15              | 58              | 9               | 18              | 62.5              | 45.5             | 52.6            |
|     DE              | DE-all $\cup$ EN-all-multi $\cup$ Rules | 16              | 57              | 10              | 17              | 61.5              | 48.5             | 54.2            |
