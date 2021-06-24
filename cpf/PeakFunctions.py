#!/usr/bin/env python

__all__ = ['create_newparams', 'params_to_newparams', 'ParamFitArr', 'PseudoVoigtPeak', 'gather_paramerrs_to_list',
           'gather_params_to_list', 'gather_params_from_dict', 'initiate_params', 'PeaksModel', 'vary_params',
           'unvary_params', 'FitModel', 'Fourier_expand', 'Fourier_fit', 'ChangeParams',
           'Fourier_backgrnd']

import numpy as np
import numpy.ma as ma
import sys
#import time
#from scipy.optimize import curve_fit
from scipy.interpolate import make_interp_spline, CubicSpline, interp1d
from lmfit import minimize, report_fit, Model

np.set_printoptions(threshold=sys.maxsize)

# Fitting functions required for fitting peaks to the data. 
# Called by FPF_XRD_FitSubpattern.


# Known limitations/bugs
# FIX ME: need hard limits to gauss - lorentz peak profile ratios


def parse_bounds(bounds, dspace, intens, twotheta, ndat=None, npeaks=1, param=None):
    """
    Turn text limits in bounds into numbers and return bounds in dictionary format.
    :param bounds: bounds dictionary
    :param dspace: dspacings of data
    :param intens: intensities of data
    :return: limits dictionary object
    """
    limits = {}
    if bounds is None:
        bounds = {
              "background": ['min', 'max'],
              "d-space":    ['min', 'max'],
              "height":     [ 0,    '2*max'],
              "profile":    [ 0,     1],
              "width":      [ 'range/(ndata)',  'range/2/npeaks'],
              }
    if ndat is None:
        ndat = np.size(dspace)

    choice_list = ['d-space', 'height', 'width', 'profile', 'background']
    if param is not None:
        choice_list = param
    
    for par in choice_list:
        if par is 'height' or par is 'background':
            vals = intens
        elif par is 'width':
            vals = twotheta
        else:
            vals = dspace
            
        b = bounds[par]
        b = [str(w).replace('inf', 'np.inf') for w in b]
        b = [str(w).replace('range', '(max-min)') for w in b]
        b = [w.replace('ndata', str(ndat)) for w in b]
        b = [w.replace('max', str(np.max(vals))) for w in b]
        b = [w.replace('min', str(np.min(vals))) for w in b]
        b = [w.replace('npeaks', str(npeaks)) for w in b]
        b = [eval(w) for w in b]
        limits[par] = b          
        
        
    # for j in range(5):
    #     if j == 0:
    #         par = 'd-space'
    #         vals = dspace
    #     elif j==1:
    #         par = 'height'
    #         vals = intens
    #     elif j==2:
    #         par = 'width'
    #         vals = dspace
    #     elif j==3:
    #         par = 'profile'
    #     elif j==4:
    #         par = 'background'
    #         vals = intens

    #     b = bounds[par]
    #     b = [str(w).replace('range', '(max-min)') for w in b]
    #     b = [w.replace('ndata', str(ndat)) for w in b]
    #     b = [w.replace('max', str(np.max(vals))) for w in b]
    #     b = [w.replace('min', str(np.min(vals))) for w in b]
    #     b = [eval(w) for w in b]
    #     limits[par] = b

    # if param is not None:
    #     limits = limits[param]

    return limits



def create_newparams(num_peaks, dfour, hfour, wfour, pfour, bgfour, order_peak):
    """
    Create the NewParams dictionary from results
    :param num_peaks: number of peaks int
    :param dfour: list of coefficients per peak float
    :param hfour: list of coefficients per peak float
    :param wfour: list of coefficients per peak float
    :param pfour: list of coefficients per peak float
    :param bgfour:
    :param order_peak:
    :return: NewParams dictionary
    """
    peaks = []
    for j in range(num_peaks):
        if 'symmetry' in order_peak[j]:  # orders['peak'][j]:  # FIX ME: the symmetry part of this is a horrible way
            # of doing it.
            peaks.append({"d-space": dfour[j][0],
                          "height": hfour[j][0],
                          "width": wfour[j][0],
                          "profile": pfour[j][0],
                          "symmetry": order_peak[j]['symmetry']})
                            # "symmetry": orders['peak'][j]['symmetry']})
        else:
            peaks.append({"d-space": dfour[j][0],
                          "height": hfour[j][0],
                          "width": wfour[j][0],
                          "profile": pfour[j][0]})
    NewParams = {"background": bgfour, "peak": peaks}

    return NewParams


def params_to_newparams(params, num_peaks, num_bg, order_peak):
    """
    Gather Parameters class to NewParams dictionary format
    :param params: lmfit Parameters class object
    :param num_peaks: number of peaks
    :param num_bg: number of background terms
    :return: NewParams dictionary object
    """

    peaks = []
    for i in range(num_peaks):
        new_str = 'peak_'+str(i)+'_d'
        dspace = gather_paramerrs_to_list(params, new_str)
        dspace_tp = get_series_type(params, new_str)
        new_str = 'peak_'+str(i)+'_h'
        hspace = gather_paramerrs_to_list(params, new_str)
        h_tp = get_series_type(params, new_str)
        new_str = 'peak_'+str(i)+'_w'
        wspace = gather_paramerrs_to_list(params, new_str)
        w_tp = get_series_type(params, new_str)
        new_str = 'peak_'+str(i)+'_p'
        pspace = gather_paramerrs_to_list(params, new_str)
        p_tp = get_series_type(params, new_str)
        
        if 'symmetry' in order_peak[i]:  # orders['peak'][j]:  # FIX ME: the symmetry part of this is a horrible
            # way of doing it.
            peaks.append({"d-space":      dspace[0],
                          "d-space_err":  dspace[1],
                          "d-space-type": coefficient_type_as_string(dspace_tp),                         
                          "height":       hspace[0],
                          "height_err":   hspace[1],
                          "height-type":  coefficient_type_as_string(h_tp),
                          "width":        wspace[0],
                          "width_err":    wspace[1],
                          "width-type":   coefficient_type_as_string(w_tp),
                          "profile":      pspace[0],
                          "profile_err":  pspace[1],
                          "profile-type": coefficient_type_as_string(p_tp),
                          "symmetry":     order_peak[i]['symmetry']})
        else:
            peaks.append({"d-space": dspace[0],
                          "d-space_err":  dspace[1],
                          "d-space-type": coefficient_type_as_string(dspace_tp),                         
                          "height":       hspace[0],
                          "height_err":   hspace[1],
                          "height-type":  coefficient_type_as_string(h_tp),
                          "width":        wspace[0],
                          "width_err":    wspace[1],
                          "width-type":   coefficient_type_as_string(w_tp),
                          "profile":      pspace[0],
                          "profile_err":  pspace[1],
                          "profile-type": coefficient_type_as_string(p_tp)})
    # Get background parameters
    bgspace = []
    bgspace_err = []
    for b in range(num_bg):
        new_str = 'bg_c'+str(b)+'_f'
        bgspc = gather_paramerrs_to_list(params, new_str)
        bgspace.append(bgspc[0])
        bgspace_err.append(bgspc[1])
    bg_tp = coefficient_type_as_string(get_series_type(params, new_str))
    
    NewParams = {"background": bgspace, "background_err": bgspace_err, "background-type": bg_tp, "peak": peaks}

    return NewParams


def flatten(li):
    """
    :param li:
    :return:
    """
    return sum(([x] if not isinstance(x, list) else flatten(x)
                for x in li), [])


def ParamFitArr(numP, LenBG, val=None, p=None, b=None, orda=None):
    """
    Makes array which represents all the fourier series in the fit.
    Arr{0} is a list of 4 element lists - one 4 element list for each peak.
    Arr[0] is the background representative.
    :param numP:
    :param LenBG:
    :param val:
    :param p:
    :param b:
    :param orda:
    :return:
    """
    if val:
        v = val
    else:
        v = 0

    if not p:
        p = [v, v, v, v]

    Arr = [[], []]
    for y in range(numP):
        Arr[0].append(p[:])
    for y in range(LenBG):
        Arr[1].extend([v][:])
    return Arr


# Gausian shape
def GaussianPeak(twotheta, tth0, W_all, H_all):
    """
    Gaussian shape
    :param twotheta:
    :param tth0:
    :param W_all:
    :param H_all:
    :return:
    """
    W_all = W_all / np.sqrt(np.log(4))
    GaussPeak = H_all * np.exp((-(twotheta - tth0) ** 2) / (2 * W_all ** 2))
    return GaussPeak


def LorentzianPeak(twotheta, tth0, W_all, H_all):
    """
    Lorentz shape
    :param twotheta:
    :param tth0:
    :param W_all:
    :param H_all:
    :return:
    """
    LPeak = H_all * W_all ** 2 / ((twotheta - tth0) ** 2 + W_all ** 2)
    return LPeak


def PseudoVoigtPeak(twotheta, tth0, W_all, H_all, LGratio):
    """
    Pseudo-Voigt
    :param twotheta:
    :param tth0:
    :param W_all:
    :param H_all:
    :param LGratio:
    :return:
    """
    # FIX ME: how should the ratio be fixed?
    # The ratio is between 1 and 0. it has to be limited.
    # But need options for fixed ratio and not fitting them.
    # How do I do this?
    #
    # I have defined a new variable called profile_fixed which fixes the value if present
    # if np.any(LGratio<0) or np.any(LGratio>1):
    # print 'The ratio is out of range'
    # stop

    PVpeak = LGratio * GaussianPeak(twotheta, tth0, W_all, H_all) + (1 - LGratio) * LorentzianPeak(twotheta, tth0,
                                                                                                   W_all, H_all)
    return PVpeak


def get_series_type(param, param_str, comp=None):
    """
    Make a nested list of parameters and errors from a lmfit Parameters class
    :param param: dict with multiple coefficients per component
    :param param_str: base string to select parameters
    :param comp: component to add to base string to select parameters
    :return: nested list of [parameters, errors] in alphanumerical order
    """
    if comp is not None:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    new_str = new_str+'_tp'
    if isinstance(param, dict) and new_str in param:
        out = param[new_str]
    elif isinstance(param, dict) and new_str not in param:
        out = 0
    else:
        out= None
    return out


def gather_paramerrs_to_list(param, param_str, comp=None, nterms=None):  # fix me: Doesn't run without Comp=None.
    # Maybe it was never validated before SAH ran it.
    """
    Make a nested list of parameters and errors from a lmfit Parameters class
    :param param: dict with multiple coefficients per component
    :param param_str: base string to select parameters
    :param comp: component to add to base string to select parameters
    :return: nested list of [parameters, errors] in alphanumerical order
    """

    if comp:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    param_list = []
    err_list = []
    total_params = []
    str_keys = [key for key, val in param.items() if new_str in key and 'tp' not in key]
    #print('yes', new_str, str_keys)
    for i in range(len(str_keys)):
        param_list.append(param[new_str + str(i)].value)
        err_list.append(param[new_str + str(i)].stderr)
    total_params.append(param_list)
    total_params.append(err_list)
    return total_params


def gather_params_to_list(param, param_str, comp=None):
    """
    Make a list of parameters from a lmfit Parameters class
    :param param: dict with multiple coefficients per component
    :param param_str: base string to select parameters
    :param comp: component to add to base string to select parameters
    :return: list of parameters in alphanumerical order
    """

    if comp:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    param_list = []
    str_keys = [key for key, val in param.items() if new_str in key]
    # print('yes', new_str, str_keys)
    for i in range(len(str_keys)):
        param_list.append(param[new_str + str(i)].value)
    return param_list


def gather_params_from_dict(param, param_str, comp):
    """
    Make a list of parameters from a dictionary
    :param param: dict with multiple coefficients per component
    :param param_str: base string to select parameters
    :param comp: component to add to base string to select parameters
    :return: list of parameters in alphanumerical order
    """

    if comp:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    param_list = []
    str_keys = [key for key, val in param.items() if new_str in key and 'tp' not in key]
    for i in range(len(str_keys)):
        param_list.append(param[new_str + str(i)])
    return param_list


def initiate_params(param, param_str, comp, coef_type=None, num_coef=None, trig_orders=None, limits=None, expr=None, value=None, ind_vars=None, vary=True):
    """
    Create all required coefficients for no. terms
    :param param: lmfit Parameter class (can be empty)
    :param param_str: base string to create lmfit parameter
    :param comp: string to add to base string to create lmfit parameter
    :param trig_orders: number of trigonometric orders
    :param limits: list [max,min] or None
    :param expr: str or None, str expression to use or 'calc'
    :param value: int if don't know nterms, use this many orders
    :param ind_vars: array-based independent variable to be added to parameters to use in expr
    :return:
    """
    if limits:
        new_max, new_min = limits
    else:
        new_min = -np.inf
        new_max = np.inf
    if value is None and limits is None:
        value = 0.01
    elif value is None and limits:
        value = new_min + (new_max-new_min)*3/5#/2#*2/3
        #N.B. if seems the initiating the splines with values exactly half way between man and min doesn't work. Anywhere else in the middle of the range seems to do so.
    # else: value=value
    value = np.array(value)  # force input to be array so that can be iterated over
    
    coef_type=coefficient_type_as_number(coef_type)
    #if coef_type == 5: #if the values at each azimuth are independent
    #    num_coef = value.shape
    if coef_type == 5: #if the values at each azimuth are independent we have to have a number of coefficients given. 
        if num_coef is not None:
            num_coef = num_coef
        elif value is not None:
            try:
                #trig_orders = int((len(value) - 1)/2) #FIX ME: coefficiennt series length -- make into separate function.
                num_coef = len(value)
            except:
                #trig_orders = int((value.size - 1)/2) #FIX ME: I dont know why the try except is needed but it is. it arose during the spline development
                num_coef = value.size  
        else:
            print(value)
            raise ValueError('Cannot define independent values without a number of coefficients.')
            
    elif trig_orders is None:
        try:
            #trig_orders = int((len(value) - 1)/2) #FIX ME: coefficiennt series length -- make into separate function.
            num_coef = len(value)
        except:
            #trig_orders = int((value.size - 1)/2) #FIX ME: I dont know why the try except is needed but it is. it arose during the spline development
            num_coef = value.size    
    else:
        num_coef = np.max(trig_orders)*2+1     
        # leave the spline with the 2n+1 coefficients so that it matches the equivalnet fourier series.
        # FIX ME: should we change this to make it more natural to understand?
    # First loop to add all the parameters so can be used in expressions
    #parm_list = []
    #for t in range(2 * np.max(trig_orders) + 1):
    for t in range(num_coef):
        if value.size == num_coef and value.size>1:
            v = value.item(t)
        elif coef_type != 0 or t==0:
            v = value.item(0)
        else:
            v=0
        if t == 0 or coef_type != 0:
        	param.add(param_str + '_' + comp + str(t), v, max=new_max, min=new_min, expr=expr, vary=vary)
        else:
        	param.add(param_str + '_' + comp + str(t), v, expr=expr, vary=vary)
    
    if comp != 's':
        param.add(param_str + '_' + comp + '_tp', coefficient_type_as_number(coef_type), expr=expr, vary=False)
    
    return param


def unvary_params(param, param_str, comp):
    """
    Set all but selected parameters to vary=False
    :param param: lmfit Parameter class
    :param param_str: base string to select with
    :param comp: string to add to base string to select with
    :return: updated lmfit Parameter class
    """
    if comp:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    str_keys = [key for key, val in param.items() if new_str in key and 'tp' not in key]
    # print(str_keys)
    for p in param:
        # print(p)
        if p not in str_keys:
            # print('yes')
            param[p].set(vary=False)
    return param

def unvary_part_params(param, param_str, comp, order=None):
    """
    Set single component of the selected parameters to vary=False
    :param param: lmfit Parameter class
    :param param_str: base string to select with
    :param comp: string to add to base string to select with
    :param order: order of the coefficients. parts missing are set to vary=False
    :return: updated lmfit Parameter class
    """
    if isinstance(order, list):
        orderr = max(order)
        for i in range(orderr):
            if not np.isin(i,order):
                param = unvary_single_param(param, param_str, comp, 2*i)
                if i>0:
                    param = unvary_single_param(param, param_str, comp, 2*i-1)
    return param
    
 
def unvary_single_param(param, param_str, comp, val):
    """
    Set single component of the selected parameters to vary=False
    :param param: lmfit Parameter class
    :param param_str: base string to select with
    :param comp: string to add to base string to select with
    :param val: order of coeffients to set to vary=False
    :return: updated lmfit Parameter class
    """
    if comp:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    new_str = new_str + str(val)
    str_keys = [key for key, val in param.items() if new_str in key]
    # print(str_keys)
    for p in param:
        # print(p)
        if p in str_keys:
            # print('yes')
            param[p].set(vary=False)
    return param

def vary_params(param, param_str, comp):
    """
    Set selected parameters to vary=True
    :param param: lmfit Parameter class
    :param param_str: base string to select with
    :param comp: string to add to base string to select with
    :return: updated lmfit Parameter class
    """
    if comp:
        new_str = param_str + '_' + comp
    else:
        new_str = param_str
    str_keys = [key for key, val in param.items() if new_str in key and 'tp' not in key]
    # print(str_keys)
    for p in str_keys:
        # print('yes')
        param[p].set(vary=True)
    return param


#def PeaksModel(twotheta, azi, num_peaks=None, nterms_back=None, Conv=None, **params):
def PeaksModel(twotheta, azi, Conv=None, **params):
    """Full model of intensities at twotheta and azi given input parameters
    :param twotheta: arr values float
    :param azi: arr values float
    :param num_peaks: total number of peaks int
    :param nterms_back: total number of polynomial expansion components for the background int
    :param Conv: inputs for the conversion call dict
    :param PenCalc: penalise background or not int
    :param params: lmfit parameter class dict
    :return lmfit model fit result
    """
    
    #t_start = time.time()
    
    # N.B. params now doesn't persist as a parameter class, merely a dictionary, so e.g. call key/value pairs as
    # normal not with '.value'

    # recreate backg array to pass to Fourier_backgrnd
    back_keys = [key for key, val in params.items() if 'bg_c' in key and 'tp' not in key]
    nterm_fouriers = []
    
    i=0
    backg=[]
    backg_tp = []
    while sum(nterm_fouriers) < len(back_keys):
        
        f = sum('bg_c' + str(i) in L for L in back_keys)
        nterm_fouriers.append(f)
        fbg = []
        for k in range(f):
            fbg.append(params['bg_c' + str(i) + '_f' + str(k)])
            if 'bg_c' + str(i) + '_f_tp' in params:
                b_tp=params['bg_c' + str(i) + '_f_tp']
            else:
                b_tp=0
                
        backg.append(np.array(fbg))
        backg_tp.append(b_tp)
        i = i+1
    
    # for i in range(int(nterms_back)):
    #     f = sum('bg_c' + str(i) in L for L in back_keys)
    #     nterm_fouriers.append(f)
    # backg = []
    # for j in range(int(nterms_back)):
    #     fbg = []
    #     for k in range(nterm_fouriers[j]):
    #         fbg.append(params['bg_c' + str(j) + '_f' + str(k)])
    #     backg.append(np.array(fbg))
    # print(backg)
    
    # for future logging
    # print('recreate backg to pass to fourier_backg\n', 'back_keys is ', back_keys)
    # print('backg is ', backg)
    I = Backgrnd((azi, twotheta), backg, coef_type=backg_tp)

    
    peak_keys = [key for key, val in params.items() if 'peak' in key and 'tp' not in key]
    num_peaks = 0
    nterm_peaks = 0
    while nterm_peaks < len(peak_keys):
        f = sum('peak_' + str(num_peaks) in L for L in peak_keys)
        nterm_peaks = nterm_peaks + f
        num_peaks = num_peaks+1

    # loop over the number of peaks
    Ipeak = []
    for a in range(int(num_peaks)):

        if 'peak_' + str(a) + '_s0' in params:
            symm = params['peak_' + str(a) + '_s0']
        else:
            symm = 1

        # May need to fix for mutliple Fourier coefficients per component
        param_str = 'peak_' + str(a)
        comp = 'd'
        parms = gather_params_from_dict(params, param_str, comp)
        coef_type = get_series_type(params, param_str, comp)
        Dall = coefficient_expand(azi, parms,coef_type=coef_type)
        comp = 'h'
        parms = gather_params_from_dict(params, param_str, comp)
        coef_type = get_series_type(params, param_str, comp)
        Hall = coefficient_expand(azi*symm, parms,coef_type=coef_type)
        comp = 'w'
        parms = gather_params_from_dict(params, param_str, comp)
        coef_type = get_series_type(params, param_str, comp)
        Wall = coefficient_expand(azi*symm, parms,coef_type=coef_type)
        comp = 'p'
        parms = gather_params_from_dict(params, param_str, comp)
        coef_type = get_series_type(params, param_str, comp)
        Pall = coefficient_expand(azi*symm, parms,coef_type=coef_type)

        # conversion
        TTHall = CentroidConversion(Conv, Dall, azi)
        Ipeak.append(PseudoVoigtPeak(twotheta, TTHall, Wall, Hall, Pall))
        I = I + Ipeak[a]

    # Elapsed time for fitting
    #t_end = time.time()
    #t_elapsed = t_end - t_start
    #print(t_elapsed)
    
    return I


def ChangeParams(constants, *fitparam):
    print('In changeparam', len(constants))
    twotheta = constants[0]
    azi = constants[1]
    ChangeArray = constants[2]
    Shapes = constants[3]
    Conv = constants[4]
    symm = constants[5]
    fixed = constants[6]

    print('changeparams:')
    print(twotheta, azi)
    print(ChangeArray)
    print(Shapes)
    print(Conv)
    print(symm)
    print(fixed)
    print(fitparam)
    Shapes = GuessApply(ChangeArray, Shapes, fitparam)
    # print(stop)
    print('In changes', Shapes)
    I, pen = PeaksModel_old(twotheta, azi, Shapes, Conv, symm, PenCalc=1)

    return I  # *pen


def FitModel(Intfit, twotheta, azimu, params, num_peaks, nterms_back, Conv=None, fixed=None,
             fit_method='leastsq', weights=None, max_nfev=None):
    # ChangeArray, Shapes, Conv=None, symm=None, fixed=None, method=None,
    # weights=None, bounds=None):
    """Initiate model of intensities at twotheta and azi given input parameters and fit
    :param Intfit: intensity values to fit arr
    :param twotheta: twotheta values arr
    :param azimu: azimu values arr
    :param params: lmfit Parameter class dict of parameters to fit
    :param num_peaks: total number of peaks in model int
    :param nterms_back: total number of polynomial component terms in background int
    :param Conv: inputs for the conversion call dict
    :param fixed: unsure
    :param method: lmfit choice of fitting method e.g. least squares
    :param weights: errors on intensity values arr of size Intfit
    :return: lmfit model result
    """

    # bounds passed but not used

    # p0array = GuessGet(ChangeArray, Shapes)
    # print('here', Intfit, twotheta, azimu, ChangeArray, Shapes)
    # params.pretty_print()
    gmodel = Model(PeaksModel, independent_vars=['twotheta', 'azi'])
    # print('parameter names: {}'.format(gmodel.param_names))
    # print('independent variables: {}'.format(gmodel.independent_vars))

    # minner = Minimizer(fcn2min, params, fcn_args=(x, data))
    # result = minner.minimize()
    # out = gmodel.fit(Intfit, params, twotheta=twotheta, azi=azimu, num_peaks=num_peaks, nterms_back=nterms_back,
    #                  Conv=Conv, fixed=fixed, nan_policy='propagate')
    out = gmodel.fit(Intfit, params, twotheta=twotheta, azi=azimu, Conv=Conv, nan_policy='propagate', max_nfev=max_nfev, xtol=1E-5)
    # print(out.fit_report())
    # print(out.params)
    # out.params.pretty_print()
    # result = popt.minimize()
    return out


def CentroidConversion(Conv, args_in, azi):
    # Conv['DispersionType'] is the conversion type
    # Conv[...] are the values required for the conversion
    # FIX ME: these functions should be a sub function of the detector types. but need to work out how to do it.
    
    if Conv == 0 or Conv['DispersionType'] is None:
        args_out = args_in

    elif Conv['DispersionType'] == 'AngleDispersive':
        # args_in are d-spacing
        # args_outis two thetas
        args_out = 2 * np.degrees(
            np.arcsin(Conv['conversion_constant'] / 2 / args_in))  # FIX ME: check this is correct!!!

    elif Conv['DispersionType'] == 'EnergyDispersive':

        args_out = []
        # for x in range(len(azi)):
        for x in range(azi.size):
            # determine which detector is being used
            # a=np.asscalar(np.where(Conv['azimuths'] == azi[x])[0])

            if azi.size == 1:
                a = np.array(np.where(Conv['azimuths'] == azi)[0][0])
                # a= np.asscalar(np.where(Conv['azimuths'] == azi)[0][0])
                args_out.append(
                    12.398 / (2 * args_in * np.sin(np.radians(Conv['calibs'].mcas[a].calibration.two_theta / 2))))
            else:
                #                print type(azi)
                #                print azi.mask[x]
                if not azi.mask[x]:
                    a = (np.where(Conv['azimuths'] == azi[x])[0][0])
                    args_out.append(12.398 / (
                            2 * args_in[x] * np.sin(np.radians(Conv['calibs'].mcas[a].calibration.two_theta / 2))))
                else:
                    args_out.append(0)
        if isinstance(azi, np.ma.MaskedArray):
            args_out = ma.array(args_out, mask=azi.mask)
    else:
        raise ValueError('Unrecognised conversion type')

    return args_out


def expand_comp_string(comp):
    
    if comp=='d':
        out = 'd-space'
    elif comp=='h':
        out = 'height'
    elif comp=='w':
        out='width'
    elif comp=='p':
        out='profile'
    elif comp=='bg' or 'f':
        out='background'
    else:
        raise ValueError('Unrecognised peak property type')
    return out


def params_get_type(orders, comp, peak=0):
    """
    Parameters
    ----------
    orders : TYPE
        DESCRIPTION.
    comp : TYPE
        DESCRIPTION.
    peak : TYPE, optional
        DESCRIPTION. The default is 1.

    Returns
    -------
    None.

    """
    comp_str = expand_comp_string(comp)+'-type'
    if comp_str in orders:
        coef_type = orders[comp_str]
    elif comp_str in orders['peak'][peak]:
        coef_type = orders['peak'][peak][comp_str]
    else:
        coef_type = 'fourier'
        
    return coef_type


def params_get_number_coef(orders, comp, peak=0, azims=None):
    
    parm_str = params_get_type(orders, comp, peak)
    parm_num = coefficient_type_as_number(parm_str)
    print(comp, parm_str, parm_num)
    if parm_num==5: #independent
        if azims is None:
            raise ValueError('Cannot define number of independent values without a number of coefficients.')
        else:  
            n_param = azims.shape[0]
        
    elif comp=='bg' or comp=='background' or comp=='f':
        n_param = np.max(orders['background'][peak])*2+1
        
    else: #everything else.
        n_param = np.max(orders['peak'][peak][expand_comp_string(comp)])*2+1
        
    return n_param
    
    
def Fourier_order(params):
    # Given list of Fourier coefficients return order (n) of the Fourier series.

    if isinstance(params, (list,)):
        order = int((len(params) - 1) / 2)
    elif isinstance(params, (float,)):
        order = int((np.size(params) - 1) / 2)
    elif isinstance(params, (int,)):
        order = 0
    else:
        print(params)
        print(type(params))
        raise ValueError('Parameter list is not list or float.')

    return order


def coefficient_type_as_number(coef_type):
    """
    :param series_type: string name of series. 
    :return: numerical index for series type
    """
    if coef_type == 'fourier' or coef_type==0:
        out = 0
    elif coef_type == 'spline_linear' or coef_type == 'linear' or coef_type==1:
        out = 1
    elif coef_type == 'spline_quadratic' or coef_type == 'quadratic' or coef_type==2:
        out = 2
    elif coef_type == 'spline_cubic_closed' or coef_type == 'spline_cubic' or coef_type == 'spline-cubic' or coef_type == 'cubic' or coef_type == 'spline' or coef_type==3:
        out = 3
    elif coef_type == 'spline_cubic_open' or coef_type == 4:
        out = 4
    elif coef_type == 'independent' or coef_type == 5:
        out = 5
    else:
        raise ValueError('Unrecognised coefficient series type, the valid options are ''fourier'', etc...')
        #FIX ME: write out all the licit options in the error message.
    return out
    
    

def coefficient_type_as_string(series_type):
    """
    :series_type: numeric series type. 
    :return: strong index for series type
    """
    if series_type == 0:# or series_type=='fourier':
        out = 'fourier'
    elif series_type == 1: # or series_type == 'spline_linear' or series_type == 'linear':
        out = 'spline_linear'
    elif series_type == 2: # or series_type == 'spline_quadratic' or series_type == 'quadratic':
        out = 'spline_quadratic'
    elif series_type==3: # or series_type == 'spline_cubic_closed' or series_type == 'spline_cubic' or series_type == 'spline-cubic' or series_type == 'cubic' or series_type == 'spline':
        out = 'spline_cubic'
    elif series_type==4: #series_type == 'spline_cubic_open' or series_type == 'spline-cubic-open' or series_type == 'cubic-open' or series_type == 'spline-open':
        out = 'spline_cubic_open'
    elif series_type == 5: #or series_type == 'independent': 
        out = 5
    else:
        raise ValueError('Unrecognised coefficient series type, the valid options are ''fourier'', etc...')
        #FIX ME: write out all the licit options in the error message.
    return out
    
    

def coefficient_expand(azimu, param=None, coef_type='fourier', comp_str=None, **params):
    
    coef_type = coefficient_type_as_number(coef_type)
    se = [0, 360]
    
    #print('param, coef expand', param)
    #print('param, coef expand', coef_type)
    if coef_type==0:
        out = Fourier_expand(azimu, param=param, comp_str=comp_str, **params)
    elif coef_type==1:
        out = Spline_expand(azimu, param=param, comp_str=comp_str, StartEnd = se, bc_type='natural', kind='linear', **params)
    elif coef_type==2:
        out = Spline_expand(azimu, param=param, comp_str=comp_str, StartEnd = se, bc_type='natural', kind='quadratic', **params)
    elif coef_type==3:
        out = Spline_expand(azimu, param=param, comp_str=comp_str, StartEnd = se, bc_type='periodic', kind='cubic', **params)
    elif coef_type==4:
        out = Spline_expand(azimu, param=param, comp_str=comp_str, StartEnd = se, bc_type='natural',  kind='cubic', **params)
    elif coef_type==5:
        out = Spline_expand(azimu, param=param, comp_str=comp_str, StartEnd = se, bc_type='natural',  kind='independent', **params)
    else:
        raise ValueError('Unrecognised coefficient series type, the valid options are ''fourier'', etc...')
        #FIX ME: write out all the licit options in the error message.
        
    return out


def coefficient_fit(ydata, azimu, param, terms=None, errs=None, param_str='peak_0', symm=1, fit_method='leastsq'):
    """Fit the Fourier expansion to number of required terms
    :param ydata: Component data array to fit float
    :param azimu: data array float
    :param param: lmfit Parameter class dict
    :param terms: number of terms to fit int
    :param errs: Component data array errors of size ydata
    :param param_str: str start of parameter name
    :param symm: symmetry in azimuth of the fourier to be fit
    :param fit_method: lmfit method default 'leastsq'
    :return: lmfit Model result
    """

    # get NaN values.
    idx = np.isfinite(azimu) & np.isfinite(ydata) 
    if type(terms) == list:
        terms = terms[0]
    if param:
        param = param
    else:
        param = Parameters()
        for t in range(2 * terms + 1): #FIX ME: coefficiennt series length -- make into separate function. 
            params.add(param_str + '_' + str(t), 1.)  # need limits

    if errs is None or errs.all is None:
        errs = np.ones(ydata.shape)

    coef_type = param.eval(param_str+'_tp')
    #print('coef fit', param)
    # param.pretty_print()
    fmodel = Model(coefficient_expand, independent_vars=['azimu'])
    # print('parameter names: {}'.format(fmodel.param_names))
    # print('independent variables: {}'.format(fmodel.independent_vars))
    # Attempt to mitigate failure of fit with weights containing 'None' values
    # Replace with nan and alter dtype from object to float64
    new_errs = errs[idx]
    new_errs[new_errs == None] = 1000 * new_errs[new_errs != None].max()
    new_errs = new_errs.astype('float64')
    out = fmodel.fit(ydata[idx], param, azimu=azimu[idx]*symm, coef_type=coef_type, method=fit_method, sigma=new_errs, comp_str=param_str,
                     nan_policy='propagate')

    return out

# spline expansion function
def Spline_expand(azimu, param=None, comp_str=None, StartEnd = [0, 360], bc_type='periodic', kind='cubic', **params):
    """Calculate Spline interpolation given input coefficients. 
    :param azimu: arr data array float
    :param param: list of values at spline tie points
    :param comp_str: str to determine which coefficients to use from params
    :param params: lmfit dict of coefficients as parameters
    :return:
    """
    
    if param is not None:
        if not isinstance(param, np.float64):
            param = np.array(param)
            if len(param.shape) > 1:
                if np.any(np.array(param.shape) > 1):
                    param = np.squeeze(param)
                elif np.all(np.array(param.shape) == 1):
                    param = np.squeeze(param)
                    param = np.array([param], float)
    else:
        # create relevant list of parameters from dict
        str_keys = [key for key, val in params.items() if comp_str in key and 'tp' not in key ]
        param = []
        for j in range(len(str_keys)):
            param.append(params[comp_str + str(j)])

    if kind=='independent':
        points = np.unique(azimu)
        #points = np.linspace(StartEnd[0], StartEnd[1], np.size(param)+1)
    elif bc_type == 'periodic':
        points = np.linspace(StartEnd[0], StartEnd[1], np.size(param)+1)
        param = np.append(param, param[0])
        #param.append(param[0])
    elif isinstance(bc_type, (list, tuple, np.ndarray)):
        points = bc_type
    else:
        points = np.linspace(StartEnd[0], StartEnd[1], np.size(param))

    if kind=='cubic':# and bc_type=='periodic':
        k=3
    elif kind=='quadratic':
        k=2
    elif kind=='linear' or kind=='independent':
        k=1
    else:
        raise ValueError('Unknown spline type.')
            
    fout = np.ones(azimu.shape)
    
    if azimu.size == 1:  # this line is required to catch error when out is single number.
        try:
            fout = param[0]
        except IndexError:
            fout = param
    else:
        fout[:] = param[0]
    # essentially d_0, h_0 or w_0
    if not isinstance(param, np.float64) and np.size(param) > 1:  
        if k==3:
            spl = CubicSpline(points, param, bc_type=bc_type, extrapolate='periodic')
        else:
            spl = make_interp_spline(points, param, k=k)
            #spl = interp1d(points, param, kind=kind)    
        
        fout = spl(azimu)

    return fout


def Fourier_order(params):
    # Given list of Fourier coefficients return order (n) of the Fourier series.

    if isinstance(params, (list,)):
        order = int((len(params) - 1) / 2)
    elif isinstance(params, (float,)):
        order = int((np.size(params) - 1) / 2)
    elif isinstance(params, (int,)):
        order = 0
    else:
        print(params)
        print(type(params))
        raise ValueError('Parameter list is not list or float.')

    return order

# fourier expansion function
def Fourier_expand(azimu, param=None, comp_str=None, **params):
    """Calculate Fourier expansion given input coefficients
    :param azimu: arr data array float
    :param param: list of Fourier coefficients float
    :param comp_str: str to determine which coefficients to use from params
    :param params: lmfit dict of coefficients as parameters
    :return:
    """
    #print('param, fourier expand', param)
    if param is not None:
        # FIX ME: Need to check the fourier is a licit length
        if not isinstance(param, np.float64):
            param = np.array(param)
            if len(param.shape) > 1:
                if np.any(np.array(param.shape) > 1):
                    param = np.squeeze(param)
                elif np.all(np.array(param.shape) == 1):
                    param = np.squeeze(param)
                    param = np.array([param], float)
        # param = tuple(param)

    else:
        # create relevant list of parameters from dict
        str_keys = [key for key, val in params.items() if comp_str in key and 'tp' not in key ]
        #print(str_keys, 'str_keys')
        param = []
        for j in range(len(str_keys)):
            #if str.startswith(comp_str, 'bg'):
            #    param.append(params[comp_str + '_f' + str(j)])
            #else:
            param.append(params[comp_str + str(j)])

    fout = np.ones(azimu.shape)
    # print(azimu, fout, 'azimu', type(param))
    if azimu.size == 1:  # this line is required to catch error when out is single number.
        try:
            fout = param[0]
        except IndexError:
            fout = param
    else:
        fout[:] = param[0]
    # essentially d_0, h_0 or w_0

    if not isinstance(param, np.float64) and np.size(param) > 1:
        for i in range(1, int((len(param) - 1) / 2) + 1):
            # len(param)-1 should never be odd because of initial a_0 parameter
            fout = fout + param[(2 * i) - 1] * np.sin(np.deg2rad(azimu) * i) + param[2 * i] * np.cos(
                np.deg2rad(azimu) * i)  # single col array
    # else:
    #  azimu = np.array(azimu)
    # fout = np.ones(azimu.shape)
    # fout[:] = out
    # out = fout*param
    return fout


def Fourier_fit(ydata, azimu, param, terms=None, errs=None, param_str='peak_0', symm=1, fit_method='leastsq'):
    """Fit the Fourier expansion to number of required terms
    :param ydata: Component data array to fit float
    :param azimu: data array float
    :param param: lmfit Parameter class dict
    :param terms: number of terms to fit int
    :param errs: Component data array errors of size ydata
    :param param_str: str start of parameter name
    :param symm: symmetry in azimuth of the fourier to be fit
    :param fit_method: lmfit method default 'leastsq'
    :return: lmfit Model result
    """

    # get NaN values.
    idx = np.isfinite(azimu) & np.isfinite(ydata) 
    if type(terms) == list:
        terms = terms[0]
    if param:
        param = param
    else:
        param = Parameters()
        for t in range(2 * terms + 1):
            params.add(param_str + '_' + str(t), 1.)  # need limits

    if errs is None or errs.all is None:
        errs = np.ones(ydata.shape)

    # param.pretty_print()
    fmodel = Model(Fourier_expand, independent_vars=['azimu'])
    # print('parameter names: {}'.format(fmodel.param_names))
    # print('independent variables: {}'.format(fmodel.independent_vars))
    # Attempt to mitigate failure of fit with weights containing 'None' values
    # Replace with nan and alter dtype from object to float64
    new_errs = errs[idx]
    new_errs[new_errs == None] = 1000 * new_errs[new_errs != None].max()
    new_errs = new_errs.astype('float64')
    out = fmodel.fit(ydata[idx], param, azimu=azimu[idx]*symm, method=fit_method, sigma=new_errs, comp_str=param_str,
                     nan_policy='propagate')

    return out


# fourier expansion function
def Fourier_backgrnd(azimutheta, param):
    """
    Calculate the Fourier expansion of the background terms
    :param azimutheta: list of arrays for azimuth and theta float
    :param param: list of input parameters
    :return: Fourier expansion result float arr
    """
    azimu, twotheta = azimutheta
    twothetaprime = twotheta - twotheta.min()
    backg = param
    bg_all = np.zeros(twotheta.shape)
    # print(backg, bg_all)

    # Not sure if this is correct, thought that if orders then array would be eg [5,0] and would want a fourier
    # expansion with 5 parms for offset and then no fourier expansion for slope i.e. 5 parms then 0.
    # But below would interpret this as effectively [0,0] instead.

    for i in range(len(backg)):
        try:
            nterms = len(backg[i])
        except TypeError:
            nterms = backg[i].size
        # print((nterms - 1) / 2)
        out = backg[i][0]
        for j in range(1, int((nterms - 1) / 2) + 1):
            out = out + backg[i][(2 * j) - 1] * np.sin(np.deg2rad(azimu) * j) + backg[i][2 * j] * np.cos(
                np.deg2rad(azimu) * j)
        bg_all = bg_all + (out * (twothetaprime ** float(i)))

    return bg_all

# fourier expansion function
def Backgrnd(azimutheta, param, coef_type=0):
    """
    Calculate the Fourier expansion of the background terms
    :param azimutheta: list of arrays for azimuth and theta float
    :param param: list of input parameters
    :return: Fourier expansion result float arr
    """
    
    azimu, twotheta = azimutheta
    twothetaprime = twotheta - twotheta.min()
    backg = param
    bg_all = np.zeros(twotheta.shape)
    # print(backg, bg_all)

    # Not sure if this is correct, thought that if orders then array would be eg [5,0] and would want a fourier
    # expansion with 5 parms for offset and then no fourier expansion for slope i.e. 5 parms then 0.
    # But below would interpret this as effectively [0,0] instead.

    for i in range(len(backg)):
        # try:
        #     nterms = len(backg[i])
        # except TypeError:
        #     nterms = backg[i].size
        # # print((nterms - 1) / 2)
        #out = backg[i][0]
        # for j in range(1, int((nterms - 1) / 2) + 1):
        #     out = out + backg[i][(2 * j) - 1] * np.sin(np.deg2rad(azimu) * j) + backg[i][2 * j] * np.cos(
        #         np.deg2rad(azimu) * j)
        out = coefficient_expand(azimu, param[i], coef_type[i])
        bg_all = bg_all + (out * (twothetaprime ** float(i)))

    return bg_all
