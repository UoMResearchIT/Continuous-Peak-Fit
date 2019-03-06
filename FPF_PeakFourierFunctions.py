# /usr/bin/python

import numpy as np
import numpy.ma as ma
import copy, os, sys
from PIL import Image
import math
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.path as mlp
from scipy.optimize import curve_fit
np.set_printoptions(threshold='nan')


### Inputs ###
# and setup


# Fitting functions #



#Gausian shape
def GaussianPeak(twotheta, tth0, W_all, H_all):
    W_all = W_all/np.sqrt(np.log(4))
    GaussPeak = H_all*np.exp((-(twotheta-tth0)**2)/(2*W_all**2))
    return GaussPeak

# Lorentz shape.
def LorentzianPeak(twotheta, tth0, W_all, H_all):
    LPeak = H_all*W_all**2/((twotheta-tth0)**2 + W_all**2)
    return LPeak


#Pseudo-Voigt.
def PseudoVoigtPeak(twotheta, tth0, W_all, H_all, LGratio):

    #FIX ME: how should the ratio be fixed?
    # The ratio is between 1 and 0. it has to be limited.
    # But need options for fixed ratio and not fitting them.
    # How do I do this?
    #
    # I have defined a new variable called profile_fixed which fixes the value if present

    if np.any(LGratio<0) or np.any(LGratio>1):
        print 'The ratio is out of range'
        #stop

    PVpeak = LGratio*GaussianPeak(twotheta, tth0, W_all, H_all) + (1-LGratio)*LorentzianPeak(twotheta, tth0, W_all, H_all)
    return PVpeak


def Fourier_order(params):
    # Given list of Fourier coefficients retrun order (n) of the Fourier series.
    
    if isinstance(params,(list,)):
        order = (len(params)-1)/2
    elif isinstance(params,(float,)):
        order = (np.size(params)-1)/2
    else:
        print 'Unknown type'
        stop

    return order


# fourier expansion function
def Fourier_expand(azimu, *param):

    param=np.array(param)
    if (len(param.shape) > 1):
        if np.any(np.array(param.shape) > 1) :
            param = np.squeeze(param)
            # print param,'1'
        elif np.all(np.array(param.shape) == 1):
            param = np.squeeze(param)
            param = np.array([param],float)
            # print param, '2'

    param=tuple(param)
    out = np.ones(azimu.shape)
    out[:] = param[0]
    # essentially d_0, h_0 or w_0

    if len(param)>1:
        for i in xrange(1, ((len(param)-1)/2)+1): # len(param)-1 should never be odd because of initial a_0 parameter
            out = out + param[(2*i)-1]*np.sin(np.deg2rad(azimu)*i) + param[2*i]*np.cos(np.deg2rad(azimu)*i) #single col array
    #else:
      #  azimu = np.array(azimu)
       # fout = np.ones(azimu.shape)
        #fout[:] = out
        #out = fout*param

    return out



def Fourier_fit(azimu,ydata,terms,param=None,errs=1):

    #print type(terms)
    if(type(terms)==list):
        terms = terms[0]
    #print terms
    #print param
    if param:
        param=param
    else:
        param = [0 for i in range((2*terms+1))]
    param=tuple(param)
    popt,pcurv = curve_fit(Fourier_expand,azimu,ydata,p0=param,sigma=errs)


    return popt,pcurv


##warning about number of free parms e.g. if n is num. chunks/2





# fourier expansion function
def Fourier_backgrnd(azimutheta, param):

    azimu,twotheta = azimutheta
    twothetaprime = twotheta-twotheta.min()
    backg=param
    bg_all = np.zeros(twotheta.shape)
    
    for i in xrange(len(backg)):
        nterms = len(backg[i])
        out = backg[i][0]
        for j in xrange(1, ((nterms-1)/2)+1): 
            out = out + backg[i][(2*j)-1]*np.sin(np.deg2rad(azimu)*j) + backg[i][2*j]*np.cos(np.deg2rad(azimu)*j)
            # print j, 'j'
        bg_all = bg_all + (out*(twothetaprime**float(i)))

    return bg_all


def FitPenaltyFunction(Azimuths, FourierValues, valid_range,Weight=1000000):

    # print Azimuths
    # print FourierValues
    # print valid_range

    # print np.size(FourierValues)
    if np.size(FourierValues) > 1:
        Vals = Fourier_expand(Azimuths, FourierValues)
    else:
        Vals = FourierValues


    Penalise = 0
    if np.min(Vals) < valid_range[0]:
        Penalise = valid_range[0] - np.min(Vals)

    if np.max(Vals) > valid_range[1]:
        Penalise = np.max(Vals) - valid_range[0]

    Penalise = Penalise**4*Weight + 1
    return Penalise


def singleInt(twothetaWL,*sparms):

    #global wavelength

    #split two theta and wavelength (if present)
    if len(twothetaWL) == 5:
        twotheta,azimu,lenbg,wavelength,profile = twothetaWL
    elif len(twothetaWL) == 4:
        twotheta,azimu,lenbg,wavelength = twothetaWL
        # twotheta = twothetaWL[0]
        # wavelength = twothetaWL[1]
    else:
        twotheta,azimu,lenbg = twothetaWL
        # twotheta = twothetaWL

    sparms=np.array(sparms)
    #print params.shape
    if (len(sparms.shape) > 1):
        if np.any(np.array(sparms.shape) > 1) :
            sparms = np.squeeze(sparms)
            #print params,'1'
        elif np.all(np.array(sparms.shape) == 1):
            sparms = np.squeeze(sparms)
            sparms = np.array([sparms],float)
            #print params, '2'
    sparms=tuple(sparms)

    ##fit d,w,h as single number with no Fourier terms
    #print 'sparams', sparms
    d_0=sparms[0]
    H_all=sparms[1]
    W_all=sparms[2]
    tmpbackg = np.array(sparms[3:3+lenbg[0]])
    backg = []
    for b in xrange(len(lenbg)):
        if b == 0:
            start = 0
            end = lenbg[b]
        else: 
            start = lenbg[b-1]
            end = lenbg[b]+start 
        backg.append(tmpbackg[start:end])
    if len(sparms) == lenbg+4:
        profile = sparms[lenbg[0]+3]
    tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))

    bg_all = Fourier_backgrnd((azimu,twotheta),backg)
    #print bg_all
    #print backg
    # bg either single num. or size of azimu array
    # print bg_all, 'bg_all'
    Int = PseudoVoigtPeak(twotheta, tth0, W_all, H_all, profile) + bg_all

    dpen  = FitPenaltyFunction(azimu, tth0, [np.min(twotheta), np.max(twotheta)])
    hpen  = FitPenaltyFunction(azimu, H_all, [0, np.max(H_all)])
    wpen  = FitPenaltyFunction(azimu, W_all, [0, (np.max(twotheta)-np.min(twotheta))])
    ppen  = FitPenaltyFunction(azimu, profile, [0, 1])
    bgpen = FitPenaltyFunction(azimu, backg, [0, np.inf])

    Int = Int * dpen * hpen * wpen * ppen * bgpen
    # print 'dpen  ',dpen
    # print 'hpen  ',hpen
    # print 'wpen  ',wpen
    # print 'ppen  ',ppen
    # print 'bgpen ',bgpen
    #stop 


    return Int



def singleFit(intens,twotheta,azimu,dspace,d0s,heights,widths,profile,fixed,wavelength,bg=None):


    '''
    All expansion parameters fitted
    '''
    #check for bg here, won't work if try to pass to fit
    if not bg:
        bg = backg
    intens=np.array(intens,dtype='float64')
    twotheta=np.array(twotheta,dtype='float64')
    azimu = np.array(azimu,dtype='float64')

    lenbg=[]
    for val in bg:
        lenbg.append(len(val))
    lenbg=np.array(lenbg)

    if fixed == 0:
        allparms = np.concatenate((d0s,heights,widths,[item for sublist in bg for item in sublist], profile), axis=None)
        #allparms.append(profile)
        #print allparms.size
        dataForFit = (twotheta, azimu,lenbg,wavelength)
        #print np.size(allparms)
        param_bounds=([-np.inf]*np.size(allparms),[np.inf]*np.size(allparms))
        param_bounds[0][-1] = 0  #force min Pseudo voigt ratio to be greater than zero
        param_bounds[1][-1] = 1  #force max Pseudo voigt ratio to be less than 1
        param_bounds[0][2] = 0   #force min height to be greater than zero
        param_bounds[0][3] = 0   #force min width to be greater than zero

    else:
        allparms = np.concatenate((d0s,heights,widths,[item for sublist in bg for item in sublist]), axis=None)
        dataForFit = (twotheta, azimu,lenbg,wavelength,profile)
        param_bounds=(-np.inf*np.ones(allparms.shape),np.inf*np.ones(allparms.shape))

    #print 'Curve_fit inputs:'
    #print allparms
    #print dataForFit
    #print param_bounds
    
    try:
        popt,pcurv = curve_fit(singleInt, dataForFit, intens, p0=allparms, bounds=param_bounds)

    except RuntimeError:
        print("Error - curve_fit failed")
        popt = np.zeros(allparms.shape)
        print popt
        print np.size(popt)
        pcurv = np.ones((popt.shape[0], popt.shape[0])) *5.

        print popt
        print pcurv

    return popt,pcurv






# def bgfit(intens,twotheta,azimu,dspace,d0s,heights,widths,wavelength,bg=None):


#     def back_change(fullarray,*bgparms):

#         '''
#         Change background only
#         '''

#         twothet,azi,lenbg,d_0,H_all,W_all = fullarray
#         bgparms=np.array(bgparms)
#         if (len(bgparms.shape) > 1):
#             if np.any(np.array(bgparms.shape) > 1) :
#                 bgparms = np.squeeze(bgparms)
#             elif np.all(np.array(bgparms.shape) == 1):
#                 bgparms = np.squeeze(bgparms)
#                 bgparms = np.array([bgparms],float)   
#         bgparms=tuple(bgparms)

#         tmpbackg = bgparms
#         backg = []
#         for b in xrange(len(lenbg)):
#             if b == 0:
#                 start = 0
#                 end = lenbg[b]
#             else: 
#                 start = lenbg[b-1]
#                 end = lenbg[b]+start 
#             backg.append(tmpbackg[start:end])

#         tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))

#         bg_all = Fourier_backgrnd((azi,twothet),backg)

#         Int = PseudoVoigtPeak(twotheta, tth0, W_all, H_all) + bg_all
        
#         return Int


#     heights=heights
#     if not bg:
#         bg = backg
#     allparms = np.concatenate(([item for sublist in bg for item in sublist]), axis=None)
#     lenbg=[]
#     for val in bg:
#         lenbg.append(len(val))
#     lenbg=np.array(lenbg)
#     intens=np.array(intens,dtype='float64')
#     twotheta=np.array(twotheta,dtype='float64')
#     azimu = np.array(azimu,dtype='float64')
#     popt,pcurv = curve_fit(back_change,(twotheta,azimu,lenbg,d0s,heights,widths),intens,p0=allparms)
#     #popt,pcurv = curve_fit(testInt, twotheta,intens, p0=[d0s,heights,widths])
#     return popt,pcurv









def ParamFit(param_change,param_fit,intens,twotheta,azimu,dspace,d0s,heights,widths,profiles,wavelength,bg=None):

    def Paramchange(fullarray,*fitparms):

        #expand input array
        twothet,azi,lenbg,tmpbackg = fullarray

        #get arrays of constants (all but background)
        D_all=d0s
        H_all=heights
        W_all=widths
        P_all=profiles

        # Organise the parameter to be fitted.
        fitparms=np.array(fitparms)
        #print params.shape
        if (len(fitparms.shape) > 1):
            if np.any(np.array(fitparms.shape) > 1) :
                fitparms = np.squeeze(fitparms)
            elif np.all(np.array(fitparms.shape) == 1):
                fitparms = np.squeeze(fitparms)
                fitparms = np.array([fitparms],float)   
        fitparms=tuple(fitparms)
        #d_0 = Fourier_expand(azi, fitparms)
        fit_all = Fourier_expand(azi, fitparms)
        # print d_0

        #Copy expanded values back into the correct place.
        #print param_change
        if param_change == 'd-space':
            D_all=np.array(fit_all)
        elif param_change == 'height':
            H_all=np.array(fit_all)
        elif param_change == 'width':
            W_all=np.array(fit_all)
        elif param_change == 'profile':
            P_all=np.array(fit_all)
        elif param_change == 'background':
            tmpbackg=np.array(fit_all)
        else:
            print 'Unknown!!!'
            stop

        #make backgorund fourier from array (either original or fitted array)
        #FIX ME: why is this not done outside this fitting routine? 
        backg = []
        for b in xrange(len(lenbg)):
            if b == 0:
                start = 0
                end = lenbg[b]
            else: 
                start = lenbg[b-1]
                end = lenbg[b]+start 
            backg.append(tmpbackg[start:end])
        
        bg_all = Fourier_backgrnd((azi,twothet),backg)

        #print wavelength
        tth_all = 2.*np.degrees(np.arcsin(wavelength/2/D_all))

        # print stop
        Int = PseudoVoigtPeak(twotheta, tth_all, W_all, H_all, P_all) + bg_all

        return Int

    '''
    Only d_0 fitted.
    '''
    #d0s=tuple(d0s)
    # print d0s, 'd0s 1'
    heights=heights

    #check for bg here, won't work if try to pass to fit
    if not bg:
        bg = backg
    flatbg = np.array(np.concatenate(([item for sublist in bg for item in sublist]), axis=None))
    lenbg=[]
    for val in bg:
        lenbg.append(len(val))
    lenbg=np.array(lenbg)
    
    intens=np.array(intens,dtype='float64')
    twotheta=np.array(twotheta,dtype='float64')
    azimu = np.array(azimu,dtype='float64')
    
    popt,pcurv = curve_fit(Paramchange,(twotheta,azimu,lenbg,flatbg),intens,p0=param_fit)
    #popt,pcurv = curve_fit(testInt, twotheta,intens, p0=[d0s,heights,widths])
    return popt,pcurv






# def dfit(intens,twotheta,azimu,dspace,d0s,heights,widths,wavelength,bg=None):

#     def dchange(fullarray,*dparms):

#         '''
#         Only d0s changing
#         '''
#         #d0s = list(d0s)
#         twothet,azi,lenbg,tmpbackg = fullarray
#         dparms=np.array(dparms)
#         #print params.shape
#         if (len(dparms.shape) > 1):
#             if np.any(np.array(dparms.shape) > 1) :
#                 dparms = np.squeeze(dparms)
#             elif np.all(np.array(dparms.shape) == 1):
#                 dparms = np.squeeze(dparms)
#                 dparms = np.array([dparms],float)   
#         dparms=tuple(dparms)
#         d_0 = Fourier_expand(azi, dparms)
#         # print d_0
#         H_all=heights
#         W_all=widths
#         #print wavelength
#         tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))

#         backg = []
#         for b in xrange(len(lenbg)):
#             if b == 0:
#                 start = 0
#                 end = lenbg[b]
#             else: 
#                 start = lenbg[b-1]
#                 end = lenbg[b]+start 
#             backg.append(tmpbackg[start:end])
        
#         bg_all = Fourier_backgrnd((azi,twothet),backg)
#         # print stop
#         Int = PseudoVoigtPeak(twotheta, tth0, W_all, H_all) + bg_all

#         return Int

#     '''
#     Only d_0 fitted.
#     '''
#     #d0s=tuple(d0s)
#     # print d0s, 'd0s 1'
#     heights=heights
#     #check for bg here, won't work if try to pass to fit
#     if not bg:
#         bg = backg
#     flatbg = np.array(np.concatenate(([item for sublist in bg for item in sublist]), axis=None))
#     lenbg=[]
#     for val in bg:
#         lenbg.append(len(val))
#     lenbg=np.array(lenbg)
#     intens=np.array(intens,dtype='float64')
#     twotheta=np.array(twotheta,dtype='float64')
#     azimu = np.array(azimu,dtype='float64')
#     popt,pcurv = curve_fit(dchange,(twotheta,azimu,lenbg,flatbg),intens,p0=d0s)
#     #popt,pcurv = curve_fit(testInt, twotheta,intens, p0=[d0s,heights,widths])
#     return popt,pcurv





# def hfit(intens,twotheta,azimu,newd0s,widths,hparms,wavelength,bg=None):

#     symm = 1

#     def hchange(fullarray,*hparms):

#         '''
#         Only h changing
#         '''
#         #d0s = list(d0s)
#         twothet,azi,lenbg,tmpbackg = fullarray

#         hparms=np.array(hparms)
#         if (len(hparms.shape) > 1):
#             if np.any(np.array(hparms.shape) > 1) :
#                 hparms = np.squeeze(hparms)
#             elif np.all(np.array(hparms.shape) == 1):
#                 hparms = np.squeeze(hparms)
#                 hparms = np.array([hparms],float)   
#         hparms=tuple(hparms)
#         d_0 = newd0s
#         H_all = Fourier_expand(azi, hparms)
#         W_all = widths
#         #print wavelength
#         tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))

#         backg = []
#         for b in xrange(len(lenbg)):
#             if b == 0:
#                 start = 0
#                 end = lenbg[b]
#             else: 
#                 start = lenbg[b-1]
#                 end = lenbg[b]+start 
#             backg.append(tmpbackg[start:end])

#         bg_all = Fourier_backgrnd((azi,twothet),backg)
#         # print stop
#         Int = PseudoVoigtPeak(twotheta, tth0, W_all, H_all) + bg_all

#         return Int
#     '''
#     Only h fitted.
#     '''
#     #d0s=tuple(d0s)
#     # print d0s, 'd0s 1'
#     #check for bg here, won't work if try to pass to fit
#     if not bg:
#         bg = backg
#     flatbg = np.array(np.concatenate(([item for sublist in bg for item in sublist]), axis=None))
#     lenbg=[]
#     for val in bg:
#         lenbg.append(len(val))
#     lenbg=np.array(lenbg)
#     intens=np.array(intens,dtype='float64')
#     twotheta=np.array(twotheta,dtype='float64')
#     azimu = np.array(azimu,dtype='float64') * symm
#     popt,pcurv = curve_fit(hchange,(twotheta,azimu,lenbg,flatbg),intens,p0=hparms)

#     return popt,pcurv






# def wfit(intens,twotheta,azimu,newd0s,newheights,wparms,wavelength,bg=None):


#     symm = 1

#     def wchange(fullarray,*wparms):

#         '''
#         Only w changing
#         '''
#         #d0s = list(d0s)
#         twothet,azi,lenbg,tmpbackg = fullarray
#         wparms=np.array(wparms)
#         if (len(wparms.shape) > 1):
#             if np.any(np.array(wparms.shape) > 1) :
#                 wparms = np.squeeze(wparms)
#             elif np.all(np.array(wparms.shape) == 1):
#                 wparms = np.squeeze(wparms)
#                 wparms = np.array([wparms],float)   
#         wparms=tuple(wparms)

#         d_0 = newd0s
#         H_all = newheights
#         W_all = Fourier_expand(azi, wparms)
#         #print wavelength
#         tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))

#         backg = []
#         for b in xrange(len(lenbg)):
#             if b == 0:
#                 start = 0
#                 end = lenbg[b]
#             else: 
#                 start = lenbg[b-1]
#                 end = lenbg[b]+start 
#             backg.append(tmpbackg[start:end])

#         bg_all = Fourier_backgrnd((azi,twothet),backg)
#         # print stop
#         Int = PseudoVoigtPeak(twotheta, tth0, W_all, H_all) + bg_all

#         return Int
#     '''
#     Only w fitted.
#     '''
#     #d0s=tuple(d0s)
#     # print d0s, 'd0s 1'
#     #check for bg here, won't work if try to pass to fit
#     if not bg:
#         bg = backg
#     flatbg = np.array(np.concatenate(([item for sublist in bg for item in sublist]), axis=None))
#     lenbg=[]
#     for val in bg:
#         lenbg.append(len(val))
#     lenbg=np.array(lenbg)
#     intens=np.array(intens,dtype='float64')
#     twotheta=np.array(twotheta,dtype='float64')
#     azimu = np.array(azimu,dtype='float64') *symm
#     popt,pcurv = curve_fit(wchange,(twotheta,azimu,lenbg,flatbg),intens,p0=wparms)

#     return popt,pcurv



def Allchange(fullarray,*allparms):

    ##fit d,w,h as single number with no Fourier terms

    #sortout allparms
    allparms=np.array(allparms)
    if (len(allparms.shape) > 1):
        if np.any(np.array(allparms.shape) > 1) :
            allparms = np.squeeze(allparms)
        elif np.all(np.array(allparms.shape) == 1):
            allparms = np.squeeze(allparms)
            allparms = np.array([allparms],float)  

    #determine if profile is beting fitted for and organise the fitted numbers
    if len(fullarray) == 6: #profile is a fitted parameter
        twothet,azi,lenbg,parmnums,wavelength,symm = fullarray
    elif len(fullarray) == 7: 
        twothet,azi,lenbg,parmnums,wavelength,symm,profiles = fullarray

    # print twothet.shape,azi.shape,parmnums.shape
    start = 0
    starth = parmnums[0]
    startw = parmnums[0:2].sum()
    if len(fullarray) == 6:
        startp = parmnums[0:3].sum()
    endp = parmnums.sum()

    d0s = allparms[0:starth]
    heights = allparms[starth:startw]
    if len(fullarray) == 6:
        widths = allparms[startw:startp]
        profiles = allparms[startp:endp]
    else:
        widths = allparms[startw:endp]


    print profiles
    

    tmpbackg = allparms[endp:]
    backg = []
    for b in xrange(len(lenbg)):
        if b == 0:
            startbg = 0
            endbg = lenbg[b]
        else: 
            startbg = lenbg[b-1]
            endbg = lenbg[b]+startbg
        backg.append(tmpbackg[startbg:endbg])

    # print d0s,heights,widths
    d_0 = Fourier_expand(azi, d0s)
    H_all = Fourier_expand(azi*symm, heights)
    W_all = Fourier_expand(azi*symm, widths)
    P_all = Fourier_expand(azi*symm, profiles)
    print np.max(d_0), np.min(d_0)
    tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))
    bg_all = Fourier_backgrnd((azi,twothet),backg)
    # print d_0,H_all,W_all,tth0,bg

    newall =  PseudoVoigtPeak(twothet, tth0, W_all, H_all, P_all) + bg_all

    #print newall.shape

    return newall


def Allfit(intens,twotheta,azimu,d0s,heights,widths,profiles,wavelength,bg=None,symm=None, fix=None):

    print fix

    '''
    All expansion parameters fitted
    '''

    #check for bg here, won't work if try to pass to fit
    if not bg:
        bg = backg
    #allparms = np.concatenate((d0s,heights,widths,profiles,[item for sublist in bg for item in sublist]), axis=None)
    lenbg=[]
    for val in bg:
        lenbg.append(len(val))
    lenbg=np.array(lenbg)
    print 'profile', profiles
    inp = []
    if fix == None: #if profile not fixed fit for profile otherwise it is a constant.
        parmnums = np.array([len(d0s),len(heights),len(widths),len(profiles)])
        inp      = (twotheta,azimu,lenbg,parmnums,wavelength,symm)
        allparms = np.concatenate((d0s,heights,widths,profiles,[item for sublist in bg for item in sublist]), axis=None)
    else:
        parmnums = np.array([len(d0s),len(heights),len(widths)])
        inp      = (twotheta,azimu,lenbg,parmnums,wavelength,symm,profiles)
        allparms = np.concatenate((d0s,heights,widths,[item for sublist in bg for item in sublist]), axis=None)
    
    # print 'parmnums', parmnums

    # #check for bg here, won't work if try to pass to fit
    # if not bg:
    #     bg = backg
    # allparms = np.concatenate((d0s,heights,widths,profiles,[item for sublist in bg for item in sublist]), axis=None)
    # lenbg=[]
    # for val in bg:
    #     lenbg.append(len(val))
    # lenbg=np.array(lenbg)

    intens=np.array(intens,dtype='float64')
    twotheta=np.array(twotheta,dtype='float64')
    azimu = np.array(azimu,dtype='float64')

    popt,pcurv = curve_fit(Allchange,inp,intens,p0=allparms, maxfev = 12000)
    #popt,pcurv = curve_fit(Allchange,(twotheta,azimu,lenbg,parmnums,wavelength,symm),intens,p0=allparms, maxfev = 12000)
    #popt,pcurv = curve_fit(testInt, twotheta,intens, p0=[d0s,heights,widths])
    return popt,pcurv

'''
def CalculatePeaks(Params, twothet, azi, wavelength):

    #calcuate the background.
    print Params
    print Params['background']
    out = Fourier_backgrnd((azi,twothet),Params['background'])

    #Calcualte the peak shapes and add them to the background.
    #FIX ME: check this loops over move than one peak

    for j in xrange(len(Params['peak'])):
        # print d0s,heights,widths
        d_0  = Fourier_expand(azi, Params['peak'][j]['d-space'])
        H_all = Fourier_expand(azi, Params['peak'][j]['height'])
        W_all = Fourier_expand(azi, Params['peak'][j]['width'])
        P_all = Fourier_expand(azi, Params['peak'][j]['profile'])

        tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))
        
        out = out + PseudoVoigtPeak(twothet, tth0, W_all, H_all)

    return out


def AllchangeNEW(fullarray,*allparms):

    ##fit d,w,h as single number with no Fourier terms

    twothet,azi,Params,wavelength = fullarray
    #twothet,azi,lenbg,parmnums,wavelength = fullarray
    # print twothet.shape,azi.shape,parmnums.shape

    print allparms
    print Params
    allparms = allparms[0]
    newall = CalculatePeaks(allparms, twothet, azi, wavelength)#H_all*np.exp((-(twothet-tth0)**2)/(2*W_all**2))) + bg_all

    # allparms=np.array(allparms)
    # if (len(allparms.shape) > 1):
    #     if np.any(np.array(allparms.shape) > 1) :
    #         allparms = np.squeeze(allparms)
    #     elif np.all(np.array(allparms.shape) == 1):
    #         allparms = np.squeeze(allparms)
    #         allparms = np.array([allparms],float)  
    # start = 0
    # starth = parmnums[0]
    # startw = parmnums[0:2].sum()
    # end = parmnums.sum()
    # d0s = allparms[0:starth]
    # heights = allparms[starth:startw]
    # widths = allparms[startw:end]
    # tmpbackg = allparms[end:]
    # backg = []
    # for b in xrange(len(lenbg)):
    #     if b == 0:
    #         startbg = 0
    #         endbg = lenbg[b]
    #     else: 
    #         startbg = lenbg[b-1]
    #         endbg = lenbg[b]+startbg
    #     backg.append(tmpbackg[startbg:endbg])

    # # print d0s,heights,widths
    # d_0 = Fourier_expand(azi, d0s)
    # H_all = Fourier_expand(azi, heights)
    # W_all = Fourier_expand(azi, widths)
    # tth0 = 2.*np.degrees(np.arcsin(wavelength/2/d_0))
    # bg_all = Fourier_backgrnd((azi,twothet),backg)
    # # print d_0,H_all,W_all,tth0,bg

    # newall =  (H_all*np.exp((-(twothet-tth0)**2)/(2*W_all**2))) + bg_all

    # #print newall.shape

    return newall


def LineariseParams(dict):

    #turn compound dictionaries into single array.
    #Also retruns the orders of each array.
    orders = []
    peak = []
    

    #backg
    print dict['background']
    print len(dict['background'])
    bg = []
    for j in xrange(len(dict['background'])):
        bg.append( (len(dict['background'][j])-1)/2 )

    orders.append({'background':  bg})

    print orders

    #peaks
    key_names = dict['peak'][0].keys()
    asdf = []
    for j in xrange(len(dict['peak'])):
        #print ((np.array(dict['peak'][j]['d-space'],dtype='float64').size)-1)/2 
        #print ((np.array(dict['peak'][j]['height'],dtype='float64').size)-1)/2 
        #print ((np.array(dict['peak'][j]['width'],dtype='float64').size)-1)/2
        #print ((np.array(dict['peak'][j]['profile'],dtype='float64').size)-1)/2

        asdf.append({"d-space":     ((np.array(dict['peak'][j]['d-space'],dtype='float64').size)-1)/2,
                      "height":     ((np.array(dict['peak'][j]['height'],dtype='float64').size)-1)/2,
                      "width":      ((np.array(dict['peak'][j]['width'],dtype='float64').size)-1)/2,
                      "profile":    ((np.array(dict['peak'][j]['profile'],dtype='float64').size)-1)/2})

        # orders['peak'][j]['d-space']  = (len(dict['peak'][j]['d-space'])-1)/2
        # orders['peak'][j]['height']  = (len(dict['peak'][j]['height'])-1)/2
        # orders['peak'][j]['width']  = (len(dict['peak'][j]['width'])-1)/2
        # orders['peak'][j]['profile']  = (len(dict['peak'][j]['profile'])-1)/2

        # FIX ME: we should be able to iteraave over the length of keys and get infor without knowing names,
        # for k in xrange(len(key_names)):
        #     # print d0s,heights,widths
        #     nm = key_names[k]
        #     vals = np.array(dict['peak'][j][nm])
        #     orda  = (vals.size - 1)/2

        #     print 'nm',  nm, type([nm])
        #     print 'j', j, type(j)
        #     print 'orda', orda, type(orda)
        #     if k==0:
        #         peak.append({nm: orda})
        #     else:
        #         print peak
        #         print type(peak)
        #         peak.update({nm: orda})
            #peak[nm] = orda

        asdf = asdf
        print asdf
        orders.append({'peak': asdf})

    print orders
    print dict
    print orders[1]['peak']
    print orders['peak'][j]['width']
    print stop


# def AllfitNew(intens,twotheta,azimu,ParamDict,wavelength,bg=None):


#     # '''
#     # All expansion parameters fitted
#     # '''
    
#     print ParamDict['peak']
#     print len(ParamDict['peak'][0]['d-space'])
#     print len(ParamDict['peak'][0]['height'])
#     print len(ParamDict['peak'][0]['width'])

#     #parmnums = np.array([len(d0s),len(heights),len(widths)])
#     # print 'parmnums', parmnums

#     #check for bg here, won't work if try to pass to fit
#     # if not bg:
#     #     bg = backg
#     # allparms = np.concatenate((d0s,heights,widths,[item for sublist in bg for item in sublist]), axis=None)
#     # lenbg=[]
#     # for val in bg:
#     #     lenbg.append(len(val))
#     # lenbg=np.array(lenbg)
#     intens=np.array(intens,dtype='float64')
#     twotheta=np.array(twotheta,dtype='float64')
#     azimu = np.array(azimu,dtype='float64')
#     pd = np.array(ParamDict)
#     print 'this is pd', pd

#     print 'this is paramdict', ParamDict['peak']

#     popt,pcurv = curve_fit(AllchangeNEW,(twotheta,azimu,ParamDict,wavelength),intens,p0=ParamDict)
#     #popt,pcurv = curve_fit(Allchange,(twotheta,azimu,lenbg,parmnums,wavelength),intens,p0=allparms)
#     #popt,pcurv = curve_fit(testInt, twotheta,intens, p0=[d0s,heights,widths])
#     return popt,pcurv




def update_backgrnd(params,lenbg,lenparams):

    backg = []
    for b in xrange(len(lenbg)):
        if b == 0:
            startbg = lenparams
            endbg = startbg+lenbg[b]
        else: 
            startbg = lenparams+lenbg[b-1]
            endbg = lenbg[b]+startbg 
        backg.append(list(params[startbg:endbg]))
    return backg
