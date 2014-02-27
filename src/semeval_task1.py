#!/usr/bin/python

"""
SemEval 2014, Task 1 -- Sentence Relatedness

This script has several requirements.
Firstly, you need to have the following libraries installed:
* NLTK
* Scikit-Learn
* SciPy / NumPy
* PyLab
* Requests (optional)

Secondly, you need to have a file containing word embeddings
as generated by word2vec, in txt format.
Using this will take a long time the first run, 
but this will be binarized after the first loading, 
cutting loading time to a few seconds.
Also note that the memory requirements for this is quite high (~8gig).
Running on e.g. Zardoz is recommended.

Thirdly, you need to have the SICK data files.

Before using the script, make sure to change the paths (above main)
so that they correspond with the locations of your files.

Running example:
python src/semeval_task1_test.py 
"""

__author__ = 'Johannes Bjerva'
__email__  = 'j.bjerva@rug.nl'

import os
import numpy as np
from sklearn.ensemble import RandomForestRegressor

import load_semeval_data
import save_semeval_data
import feature_extraction
import error_diagnostic
import config

def regression(X_train, y_train, X_test, y_test):
    """
    Train the regressor from Scikit-Learn.
    """
    # Random forest regressor w/ param optimization
    params = {'n_estimators':1000, 'criterion':'mse', 'max_depth':20, 'min_samples_split':1, #'estimators':400, depth:20
              'min_samples_leaf':1, 'max_features':2, 'bootstrap':True, 'oob_score':False,  #'max_features':'log2'
              'n_jobs':32, 'random_state':0, 'verbose':0, 'min_density':None, 'max_leaf_nodes':None}
    if config.DEBUG: params['verbose'] = 1

    regr = RandomForestRegressor(**params)

    # Train the model using the training sets
    regr.fit(X_train, y_train)

    # Plot the resutls
    save_semeval_data.plot_results(regr, params, X_test, y_test, feature_names)

    if config.DEBUG: 
        # Show the mean squared error
        print("Residual sum of squares: %.2f" % np.mean((regr.predict(X_test) - y_test) ** 2))
        # Explained variance score: 1 is perfect prediction
        print('Variance score: %.2f' % regr.score(X_test, y_test))
    
    return regr

# Array containing the names of all features, for plotting purposes
feature_names = np.array([
    'CDSM', 
    'WORDS2', 
    'WORDS3',
    'SYN_OVER', 
    'SYN_DIST', 
    'LENGTH',
    'PROVER',
    'DOM_NV', 
    'REL_NV', 
    'WRD_NV', 
    'MOD_NV',
    'WORDS1',
    #'DRS_COMPLEXITY',
    'INSTANCE',
    'RELATION',
    'dummy'
    ], dtype='|S7')
def get_features(line):
    """
    Feature extraction.
    Comment out / add lines to disable / add features.
    Add the name to the feature_names array.
    """
    johans_features = feature_extraction.get_johans_features(line[10],line[11])
    entailment_judgements = feature_extraction.get_entailment_judgements()
    features = [
        #feature_extraction.word_overlap(line[1], line[2]),      # Proportion of word overlap
        #feature_extraction.word_overlap2(line[1], line[2], line[3], line[4], line[12]),               # Proportion of word overlap with the help of paraphrases
        #feature_extraction.sentence_lengths(line[1], line[2]),  # Proportion of difference in sentence length    
        #feature_extraction.sentence_distance(line[1], line[2]) # Cosine distance between sentences
        #feature_extraction.synset_overlap(line[1], line[2]),    # Proportion of synset lemma overlap
        #feature_extraction.synset_distance(line[1], line[2]),   # Synset distance (Does not seem to help much?)
        #feature_extraction.instance_overlap(line[5], line[6], line[7], line[12]),  # Instances overlap with the help of paraphrases
        #feature_extraction.relation_overlap(line[5], line[6], line[7], line[12])  # Relation overlap in models with the help of paraphrases        johans_features[0],                             # prover output
        #johans_features[1],                             # domain novelty
        #johans_features[2],                             # relation novelty
        #johans_features[3],                             # wordnet novelty                
        #johans_features[4],                             # model novelty
        #johans_features[5],                             # word overlap
        #johans_features[6],                              # prediction.txt
        entailment_judgements[0],
        entailment_judgements[1],
        entailment_judgements[2]
        #abs(line[8], line[9]),              # DRS Complexity
        #TODO needs to be rewritten for using the xml files
        
            ]

    #features.extend(feature_extraction.entailment_judgements[str(line[0])])  # Get predictions from Johan's system

    return features

def retrieve_features(sick_train, sick_test):
    """
    Retrieve feature vectors, either by recalculating from text-files,
    or by loading from a pre-saved binary.
    """
    if config.RECALC_FEATURES:
        # Extract training features and targets
        print 'Feature extraction (train)...'
        train_sources = np.array([get_features(line) for line in sick_train])
        train_targets = np.array([line[0] for line in sick_train])

        # Extract trial features and targets
        print 'Feature extraction (trial)...'
        trial_sources = np.array([get_features(line) for line in sick_test])
        trial_targets = np.array([line[0] for line in sick_test])

        # Store to pickle for future reference
        with open('features_np.pickle', 'wb') as out_f:
            np.save(out_f, train_sources)
            np.save(out_f, train_targets)
            np.save(out_f, trial_sources)
            np.save(out_f, trial_targets)
    else:
        with open('features_np.pickle', 'rb') as in_f:
            train_sources = np.load(in_f)
            train_targets = np.load(in_f)
            trial_sources = np.load(in_f)
            trial_targets = np.load(in_f)

    return train_sources, train_targets, trial_sources, trial_targets

def main():
    # Load sick data
    sick_data = load_semeval_data.load_sick_data()

    # Split into training/test
    split = int(len(sick_data)*0.9)
    sick_train = sick_data[:split]
    sick_test = sick_data[split:]
    if config.DEBUG: print ('test size: {0}, training size: {1}'.format(len(sick_test), len(sick_train)))

    # Get training and trial features
    train_sources, train_targets, trial_sources, trial_targets = retrieve_features(sick_train, sick_test)

    # Train the regressor
    clf = regression(train_sources, train_targets, trial_sources, trial_targets)

    # Apply regressor to trial data
    outputs = clf.predict(trial_sources)

    # Evaluate regressor
    save_semeval_data.write_for_evaluation(outputs, [line[0] for line in sick_test]) #Outputs and sick_ids

    # Check errors
    error_diagnostic.output_errors(outputs, trial_targets, [line[0] for line in sick_test], [line[1:3] for line in sick_test]) #Outputs and sick_ids

    # Plot deviations
    save_semeval_data.plot_deviation(outputs, trial_targets)

    # Write to MESH
    if config.WRITE_TO_MESH:
        save_semeval_data.write_to_mesh(train_sources, train_targets, [line[0] for line in sick_train], True) #sick_ids
        save_semeval_data.write_to_mesh(trial_sources, trial_targets, [line[0] for line in sick_test], False) #sick_ids

    # Run the evaluation script
    os.system('R --no-save --slave --vanilla --args working/foo.txt working/SICK_trial.txt < src/sick_evaluation.R')


if __name__ == '__main__':
    main()


'''
# Calculate stop list
word_freqs = defaultdict(int)
for line in sick_data:
    for word in line[1]+line[2]:
        word_freqs[word] += 1

stop_list = set(sorted(word_freqs,key=word_freqs.get,reverse=True)[:3]) # 3 stop seems the best
stop_list.add('of') #FIXME
print 'stop list:', stop_list
'''
#DSM + Words
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.611219539386618"
[1] "Relatedness: Spearman correlation 0.579121096289511"
[1] "Relatedness: MSE 0.636769966364063"
'''

#DSM + Words + Synsets (1)
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.6240941025167"
[1] "Relatedness: Spearman correlation 0.581191940616606"
[1] "Relatedness: MSE 0.620184604639824"
'''

#DSM w/trigram + Words + Synsets (1)
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.629040484297528"
[1] "Relatedness: Spearman correlation 0.587369803749406"
[1] "Relatedness: MSE 0.611421097501485"
'''

#DSM w/trigram + Words + Synsets (5)
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.634456413747237"
[1] "Relatedness: Spearman correlation 0.59369997611572"
[1] "Relatedness: MSE 0.604260603099203"
'''

#Above + Length
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.644495416146579"
[1] "Relatedness: Spearman correlation 0.615426300643788"
[1] "Relatedness: MSE 0.591781380569611"
'''

#Regressor tuning
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.66953725062349"
[1] "Relatedness: Spearman correlation 0.637914417450239"
[1] "Relatedness: MSE 0.559007711760069"
'''

#With entailment (Gold)
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.796717745220322"
[1] "Relatedness: Spearman correlation 0.815944668105982"
[1] "Relatedness: MSE 0.37025897125941"
'''

#Boxer features
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.755935252390634"
[1] "Relatedness: Spearman correlation 0.730835956061164"
[1] "Relatedness: MSE 0.435116692987163"
'''

#New regressor
'''
[1] "Processing foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.790047753882667"
[1] "Relatedness: Spearman correlation 0.763151377170929"
[1] "Relatedness: MSE 0.382032158131169"
'''

# New features
'''
[1] "Processing working/foo.txt"
[1] "No data for the entailment task: evaluation on relatedness only"
[1] "Relatedness: Pearson correlation 0.869028349326605"
[1] "Relatedness: Spearman correlation 0.852014822656915"
[1] "Relatedness: MSE 0.250408557759324"
'''