import warnings
warnings.filterwarnings("ignore")

import os
import time
import shutil
import numpy as np
import pandas as pd
from joblib import Parallel
from joblib import delayed
from matplotlib import pylab as plt
from tqdm import tqdm_notebook as tqdm
from sklearn.model_selection import cross_val_score

from .batch_base import BatchBase

class RandSearch(BatchBase):
    """ 
    Random Search. 

    Parameters
    ----------    
    :type  para_space: dict or list of dictionaries
    :param para_space: It has three types:
    
        Continuous: 
            Specify `Type` as `continuous`, and include the keys of `Range` (a list with lower-upper elements pair) and
            `Wrapper`, a callable function for wrapping the values.  
        Integer:
            Specify `Type` as `integer`, and include the keys of `Mapping` (a list with all the sortted integer elements).
        Categorical:
            Specify `Type` as `categorical`, and include the keys of `Mapping` (a list with all the possible categories).
    
    :type max_runs: int, optional, default = 100
    :param max_runs: The maximum number of trials to be evaluated. When this values is reached, 
        then the algorithm will stop. 
        
    :type n_jobs: int or None, optional, optional, default = None
    :param n_jobs: Number of jobs to run in parallel.
        If -1 all CPUs are used. If 1 is given, no parallel computing code
        is used at all, which is useful for debugging. See the package `joblib` for details.

    :type  estimator: estimator object
    :param estimator: This is assumed to implement the scikit-learn estimator interface.
    
    :type  cv: cross-validation method, an sklearn object.
    :param cv: e.g., `StratifiedKFold` and KFold` is used.

    :type scoring: string, callable, list/tuple, dict or None, optional, default = None
    :param scoring: A sklearn type scoring function. 
        If None, the estimator's default scorer (if available) is used. See the package `sklearn` for details.
    
    :type refit: boolean, or string, optional, default = True
    :param refit: It controls whether to refit an estimator using the best found parameters on the whole dataset.
    
    :type rand_seed: int, optional, default = 0
    :param rand_seed: The random seed for optimization.
    
    :type verbose: boolean, optional, default = False
    :param verbose: It controls whether the searching history will be printed. 

    Examples
    ----------
    >>> import numpy as np
    >>> from sklearn import svm
    >>> from sklearn import datasets
    >>> from seqmm import RandSearch
    >>> from sklearn.model_selection import KFold
    >>> iris = datasets.load_iris()
    >>> ParaSpace = {'C':{'Type': 'continuous', 'Range': [-6, 16], 'Wrapper': np.exp2}, 
               'gamma': {'Type': 'continuous', 'Range': [-16, 6], 'Wrapper': np.exp2}}
    >>> estimator = svm.SVC()
    >>> cv = KFold(n_splits=5, random_state=0, shuffle=True)
    >>> clf = RandSearch(ParaSpace, max_runs = 100, estimator = estimator, cv = cv, 
                 scoring=None, n_jobs = None, refit=False, rand_seed = 0, verbose = False)
    >>> clf.fit(iris.data, iris.target)

    Attributes
    ----------
    :ivar best_score_: float
        The best average cv score among the evaluated trials.  

    :ivar best_params_: dict
        Parameters that reaches `best_score_`.

    :ivar best_estimator_: 
        The estimator refitted based on the `best_params_`. 
        Not available if `refit=False`.

    :ivar search_time_consumed_: float
        Seconds used for whole searching procedure.

    :ivar refit_time_: float
        Seconds used for refitting the best model on the whole dataset.
        Not available if `refit=False`.
    """    

    def __init__(self, para_space, max_runs = 100, estimator = None, cv = None, 
                 scoring=None, n_jobs = None, refit=False, rand_seed = 0, verbose = False):

        super(RandSearch,self).__init__(para_space, max_runs, n_jobs, verbose)

        self.cv = cv
        self.refit = refit
        self.scoring = scoring
        self.estimator = estimator        
        self.rand_seed = rand_seed     
        self.method = "Random Search"
        
    def _run(self, obj_func):
        """
        Main loop for searching the best hyperparameters. 
        
        """  
        para_set = pd.DataFrame()
        for item, values in self.para_space.items():
            if (values['Type']=="categorical"):
                para_set[item] = [np.random.choice(values['Mapping']) for i in range(self.max_runs)]
            elif (values['Type']=="integer"):
                para_set[item] = [np.round(np.random.choice(values['Mapping'])).astype(int) for i in range(self.max_runs)]
            elif (values['Type'] == "continuous"):
                para_set[item] = values['Wrapper'](np.random.uniform(values['Range'][0],values['Range'][1],self.max_runs))
                
        candidate_params = [{para_set.columns[j]: para_set.iloc[i,j] 
                             for j in range(para_set.shape[1])} 
                            for i in range(para_set.shape[0])] 
        if self.verbose:
            out = Parallel(n_jobs=self.n_jobs)(delayed(obj_func)(parameters)
                                for parameters in tqdm(candidate_params))
        else:
            out = Parallel(n_jobs=self.n_jobs)(delayed(obj_func)(parameters)
                                for parameters in candidate_params)
        self.logs = para_set.to_dict()
        self.logs.update(pd.DataFrame(out, columns = ["score"]))
        self.logs = pd.DataFrame(self.logs).reset_index(drop=True)
        if self.verbose:
            print("Search completed (%d/%d) with best score: %.5f."
                %(self.logs.shape[0], self.max_runs, self.logs["score"].max()))