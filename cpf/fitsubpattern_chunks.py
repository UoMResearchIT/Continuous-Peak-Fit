#!/usr/bin/env python

__all__ = ["get_manual_guesses", "get_chunk_background_guess", "fit_chunks"]

# CPF_XRD_FitSubpattern
# Script fits subset of the data with peaks of pre-defined Fourier orders

import os
import sys
import time
import matplotlib.pyplot as plt
import numpy as np
import numpy.ma as ma
from lmfit import Parameters, Model
from lmfit.model import save_modelresult  # , load_modelresult
import json
import cpf.PeakFunctions as pf
import cpf.IO_functions as io
import warnings



# =========================
#notes:
# - remove get_manual_guesses from FitSubpattern. no longer required there.
# - remove get_chunk_background_guess from FitSubpattern. no longer required there. 
# =========================

#def get_manual_guesses(peeks, orders, bounds, twotheta, debug=None):
def get_manual_guesses(settings_as_class, data_as_class, debug=False):
    """ 
    :param data_as_class:
    :param settings_as_class:
    :param debug:
    :return dfour:
    """
    
    peeks = len(settings_as_class.subfit_orders)
    t_th_guesses = np.array(settings_as_class.subfit_orders["PeakPositionSelection"])

    #confirm there are the same number of peaks selected as are to be fit.
    if len(t_th_guesses) != peeks:
        raise ValueError("The number of peaks and the postion selection do not match.")

    # for future use in setting limits
    dist = np.max(t_th_guesses[:, 2]) - np.min(t_th_guesses[:, 2])
    width_change = dist / (2 ** peeks)
    peak_vals = np.unique(t_th_guesses[:, 2])

    # Fit Fourier series to two-theta/d-spacing for each peak
    # FIX ME: this fitting should be done to the d-spacing not the tth/energy. Probably need to import
    # the detector functions to make this happen.
    dfour = []
    for j in range(peeks):
        peek = j + 1
        t_th_guess = t_th_guesses[t_th_guesses[:, 0] == peek, 1:]
        param_str = "peak_" + str(j)
        comp = "d"
        lims = pf.parse_bounds(
            settings_as_class.fit_bounds, data_as_class.tth.flatten(), 0, 0, param=["d-space"]
        )
        # Confirm that peak position selections are within the bounds.
        # If not fail as gracefully as possible.
        lims_tth = np.array(lims["d-space"])
        if (
                np.min(t_th_guess[:, 1]) < lims_tth[0]
                or np.max(t_th_guess[:, 1]) > lims_tth[1]
        ):
            raise ValueError(
                "At least one of the "
                "PeakPositionSelection"
                " values is outside of the bounds. Check values in "
                "range"
                " and "
                "PeakPositionSelection"
                "."
            )

        # get coefficient type
        coeff_type = pf.params_get_type(settings_as_class.subfit_orders, comp, peak=j)
        # if "d-space-type" in settings_as_class.subfit_orders["peak"][j]:
        #     coeff_type = settings_as_class.subfit_orders["peak"][j]["d-space-type"]
        # else:
        #     coeff_type = "fourier"

        # for guesses make sure there are not too many coefficients.
        n_coeff = pf.get_number_coeff(settings_as_class.subfit_orders, comp)
        
        if n_coeff > len(t_th_guess[:, 0]):
            o = int(np.floor(len(t_th_guess[:, 0]) / 2 - 1))
            # FIX ME: this should be a function!! and should check the series type.
        else:
            o = settings_as_class.subfit_orders["peak"][j]["d-space"]

        temp_param = Parameters()
        temp_param = pf.initiate_params(
            inp_param=temp_param,
            param_str=param_str,
            coeff_type=coeff_type,
            comp=comp,
            trig_orders=o,
            limits=lims["d-space"],
            value=t_th_guess[1, 1],
        )
        fout = pf.coefficient_fit(
            azimuth=t_th_guess[:, 0],
            ydata=t_th_guess[:, 1],
            inp_param=temp_param,
            param_str=param_str + "_" + comp,
            fit_method="leastsq",
        )
        temp_param = fout.params
        if debug:
            temp_param.pretty_print()
        dfour.append(
            pf.gather_param_errs_to_list(temp_param, param_str, comp)
        )
    return dfour


# def get_chunk_background_guess(twotheta, azimu, intens, orders, chunks, background_type, count, n):
def get_chunk_background_guess(settings_as_class, data_chunk_class, n, debug=False):
    """
    :param data_chunk_class:
    :param settings_as_class:
    :param chunks:
    :param count:
    :param n:
    :param debug:
    :return background_guess:
        
    FIXME: background_type has been removed/depreciated. It is no longer needed. It should be replaced by background_fixed
    """
    # j = count
    
    # Get indices of sorted two theta values excluding the masked values
    tth_ord = ma.argsort(data_chunk_class.tth.compressed())
    
    background_guess = [[0.0] for i in range(len(settings_as_class.subfit_orders["background"]))]
    
    if "background_fixed" in settings_as_class.fit_orders:
        # this is not yet implemented but the option exists here where it is needed first.
        raise NotImplementedError
        
    else:
        if len(settings_as_class.subfit_orders["background"]) == 1:
            # assume background is present either at the left or right edges of the region.
            # FIXME: this assumes a positive peak. It may not work for absorption peaks. Not tested though.
            background_guess[0][0] = np.min(
                [
                    np.mean(
                        data_chunk_class.intensity.compressed()[
                            tth_ord[:n]
                        ]
                    ),
                    np.mean(
                        data_chunk_class.intensity.compressed()[
                            tth_ord[-n:]
                        ]
                    ),
                ]
            )
        else:  # len(orders['background']) > 1:
            # first value (offset) is mean of left-hand values
            background_guess[0][0] = np.mean(
                data_chunk_class.intensity.compressed()[
                    tth_ord[:n]
                ]
            )
            # if there are more, then calculate a gradient guess.
            background_guess[1][0] = (
                                              np.mean(
                                                  data_chunk_class.intensity.compressed()[
                                                      tth_ord[-n:]
                                                  ]
                                              )
                                              - np.mean(
                                                  data_chunk_class.intensity.compressed()[
                                                    tth_ord[:n]
                                                  ]
                                              )
                                      ) / (
                                              data_chunk_class.tth.compressed()[
                                                  tth_ord[-1]
                                              ]
                                              - data_chunk_class.tth.compressed()[
                                                  tth_ord[0]
                                              ]
                                      )
            # leave all higher order terms as 0 -- assume they are small.
    
    return background_guess


# def get_chunk_guesses(peeks, orders, twotheta, intens, background_guess,
#                       azimu, chunks, conversion_factor, data_as_class, count, n,
#                       d_space, bounds, w_guess_fraction, dfour=None, debug=None):
def get_chunk_peak_guesses(settings_as_class, data_chunk_class, 
                                                        background_guess,
                                                        # chunks, 
                                                        # count, 
                                                        n, w_guess_fraction,
                                                        dfour, debug=False):
    """

    
    :param data_as_class:
    :param settings_as_class:
    :param background_guess:
    :param chunks:
    :param count:
    :param n:
    :param w_guess_fraction:
    :param dfour:
    :param debug:
    :return peaks, limits, p_fixed:
    """
    d_guess = []
    h_guess = []
    w_guess = []
    p_guess = []
    p_fixed = 0
    peaks = []
    lims = []
    # j = count

    for k in range(len(settings_as_class.subfit_orders["peak"])):
        # FIX ME: altered from locals call as now passed as None - check!
        if dfour: # If the positions have been pre-guessed extract values from dfour.
            if debug and k == 0:
                print("dfour in locals")
            
            coeff_type = pf.params_get_type(settings_as_class.subfit_orders, "d", peak=k)
            # if "d-space-type" in settings_as_class.subfit_orders["peak"][k]:
            #     coeff_type = settings_as_class.subfit_orders["peak"][k]["d-space-type"]
            # else:
            #     coeff_type = "fourier"
            
            t_th_guess = pf.coefficient_expand(
                np.mean(data_chunk_class.azm),
                dfour[k][0],
                coeff_type=coeff_type,
            )
            d_guess = data_chunk_class.conversion(
                t_th_guess,
                azm=np.mean(data_chunk_class.azm),
            )
            # Finds the index of the closest two-theta to the d-spacing input
            idx = (
                np.abs(data_chunk_class.tth - t_th_guess)
            ).argmin()
            # FIX ME: The mean of a number of the smallest values would be more stable.

            # Height is intensity of the closest pixel in d-spacing - background at that position
            h_guess = data_chunk_class.intensity[idx]
            if len(background_guess) > 1:
                h_guess = h_guess - (
                        background_guess[0][0]
                        + background_guess[1][0]
                        * (
                                data_chunk_class.tth[idx]
                                - data_chunk_class.tth.min()
                        )
                )
            elif len(background_guess) == 1:
                h_guess = h_guess - background_guess[0][0]

        else:  # 'guess' guesses from data slice - assuming a single peak
            # find the brightest pixels
            # get index of nth brightest pixel.
            idx = np.argsort(
                data_chunk_class.intensity.compressed()
            )[-n:][0]

            # height guess is nth highest intensity - background guess at this position
            h_guess = (data_chunk_class.intensity.compressed())[idx]
            if len(background_guess) > 1:
                h_guess = h_guess - (
                        background_guess[0][0]
                        + background_guess[1][0]
                        * (
                                data_chunk_class.tth.compressed()[
                                    idx
                                ]
                                - data_chunk_class.tth.min()
                        )
                )
            elif len(background_guess) == 1:
                h_guess = h_guess - background_guess[0][0]

            # d-spacing of the highest nth intensity pixel
            d_guess = data_chunk_class.dspace.compressed()[idx]

        # w_guess is fractional width of the data range
        w_guess = (
                (
                        np.max(data_chunk_class.tth)
                        - np.min(data_chunk_class.tth)
                )
                / w_guess_fraction
                / len(settings_as_class.subfit_orders["peak"])
        )
        # FIX ME: This is a bit crude. Is there a better way to do it?

        # If profile_fixed exists then set p_guess to profile_fixed values and set p_fixed to 1
        p_guess = 0.5  # Guess half if solving for profile
        p_fixed = (
            0  # Set to 0 so solving unless profile_fixed exists.
        )
        if "profile_fixed" in settings_as_class.subfit_orders["peak"][k]:
            # Profile fixed is the list of coefficients if the profile is fixed.
            # FIX ME: profile fixed must have the same number of coefficients as required by
            # profile.
            if "symmetry" in settings_as_class.subfit_orders["peak"][k]:
                symm = settings_as_class.subfit_orders["peak"][k]["symmetry"]
            else:
                symm = 1
            p_guess = pf.fourier_expand(
                np.mean(data_chunk_class.azm) * symm,
                inp_param=settings_as_class.subfit_orders["peak"][k]["profile_fixed"],
            )
            p_fixed = 1

        peaks.append(
            {
                "height": [h_guess],
                "d-space": [d_guess],
                "width": [w_guess],
                "profile": [p_guess],
            }
        )

        # DMF added needs checking - required to drive fit and avoid failures
        lims.append(
            pf.parse_bounds(
                settings_as_class.fit_bounds,
                data_chunk_class,
                param=["height", "d-space", "width", "profile"],
            )
        )
        data_chunk_class
        # lims.append(
        #     pf.parse_bounds(
        #         settings_as_class.fit_bounds,
        #         data_as_class.dspace.flatten()[chunks[j]],
        #         data_as_class.intensity.flatten()[chunks[j]],
        #         data_as_class.tth.flatten()[chunks[j]],
        #         param=["height", "d-space", "width", "profile"],
        #     )
        # )

    # limits = {
    #     "background": pf.parse_bounds(
    #             settings_as_class.fit_bounds,
    #             data_as_class.dspace.flatten()[chunks[j]],
    #             data_as_class.intensity.flatten()[chunks[j]],
    #             data_as_class.tth.flatten()[chunks[j]],
    #         param=["background"],
    #     )["background"],
    #     "peak": lims,
    # }
    limits = {
        "background": pf.parse_bounds(
                settings_as_class.fit_bounds,
                data_chunk_class,
            param=["background"],
        )["background"],
        "peak": lims,
    }
    return peaks, limits, p_fixed



def fit_chunks(
    data_as_class,
    settings_as_class,
    save_fit=False,
    debug=False,
    fit_method=None,
    give_back = "fitted",
):
    """
    Take the raw data, fit the chunks and return the chunk fits
    :param fit_method:
    :param data_as_class:
    :param settings_as_class:
    :param save_fit:
    :param debug:
    :param fit_method:
    :return chunk_params:
    """
    
    peeks = len(settings_as_class.subfit_orders["peak"])
    bg_length = len(settings_as_class.subfit_orders["background"])

    if "PeakPositionSelection" not in settings_as_class.subfit_orders:
        if peeks > 1:
            p = "peaks"
        else:
            p = "peak"
        print(
            "\nNo previous fits or selections. Assuming "
            + str(peeks)
            + " "
            + p
            + " and group fitting in azimuth...\n"
        )
        dfour = None
        # FIXME: passed as None now - check functions as expected
    else:
        print("\nUsing manual selections for initial guesses...\n")
        # FIXME: Need to check that the num. of peaks for which we have parameters is the same as the
        # number of peaks guessed at.
        #dfour = get_manual_guesses(peeks, orders, bounds, twotheta, debug=None)
        dfour = get_manual_guesses(settings_as_class, data_as_class, debug=False)
        
    # Get chunks according to detector type.
    chunks, azichunks = data_as_class.bins(settings_as_class)
    print(chunks)
    print(azichunks)
    print(len(chunks))
    print(len(azichunks))
    # Final output list of azimuths with corresponding twotheta_0,h,w
    
    # setup arrays
    new_azi_chunks = []
    if give_back == "fitted":
        out_vals = {}
        out_vals["d"] = [[] for _ in range(peeks)]
        out_vals["d_err"] = [[] for _ in range(peeks)]
        out_vals["h"] = [[] for _ in range(peeks)]
        out_vals["h_err"] = [[] for _ in range(peeks)]
        out_vals["w"] = [[] for _ in range(peeks)]
        out_vals["w_err"] = [[] for _ in range(peeks)]
        out_vals["p"] = [[] for _ in range(peeks)]
        out_vals["p_err"] = [[] for _ in range(peeks)]
        out_vals["bg"] = [[] for _ in range(bg_length)]
        out_vals["bg_err"] = [[] for _ in range(bg_length)]
        
        #bunch of settings
        # only compute the fit and save it if there are sufficient data
        min_dat = 21  # minimum data in each chunk
        n = 5  # how many data to use in constructing guesses.
        w_guess_fraction = 10.0
        # N.B. if min_dat/n is too large the guesses will become very strange.
        # FIXME: These should be input variables (for use in extremes)
        # FIXME: possibly do this better using scipy.signal.find or scipy.signal.find_peaks_cwt
    
    else:
        out_vals = []
    
    
    for j in range(len(chunks)):
        # print('\nFitting to data chunk ' + str(j + 1) + ' of ' + str(len(chunks)) + '\n')
        if debug:
            print("\n")
        print(
            "\rFitting to data chunk %s of %s "
            % (str(j + 1), str(len(chunks))),
            end="\r",
        )
        
        
        #make data class for chunks.
        chunk_data = data_as_class.duplicate()
        #reduce data to a subset
        # FIXME: this is crude but I am not convinced that it needs to be contained within the data class.
        # FEXME: maybe I need to reconstruct the data class so that dat_class.tth is a function that applies a mask when called. but this will be slower.
        chunk_data.intensity = chunk_data.intensity.flatten()[chunks[j]]
        chunk_data.tth       = chunk_data.tth.flatten()[chunks[j]]
        chunk_data.azm       = chunk_data.azm.flatten()[chunks[j]]
        chunk_data.dspace    = chunk_data.dspace.flatten()[chunks[j]]
        
        
        # find other output from intensities
        if give_back == "maxima":
            # get maximum from each chunk
            out_vals.append(np.max(chunk_data.intensity))
            new_azi_chunks.append(azichunks[j])
            
        elif give_back == "98thpercentile":
            # FIXME: this is crude and could be done better -- i.e. with a switch for the percentile
            # get 98th percentils from each chunk
            raise NotImplementedError
            #out_vals.append(np.max(chunk_data.intensity))
            
        elif give_back == "fitted":
            
            # Define parameters to pass to fit
            params = Parameters()
            # if orders: bg of form [num_orders_0,num_orders_1]
            # if coeffs: bg of form [[coeff1],[coeff2, coeff3, coeff4]]
    
            # FIXME: not meeting this condition means no chunk fitting
            # is this correct?
            # yes. 
            
            if ma.MaskedArray.count(chunk_data.intensity) >= min_dat:
        
                # append azimuth to output
                new_azi_chunks.append(azichunks[j])
        
                # Background estimates
                # background_guess = get_chunk_background_guess(twotheta, azimu, intens, orders,
                #                                               chunks, background_type, count=j, n=n)
                background_guess = get_chunk_background_guess(settings_as_class, chunk_data, n, debug=debug)
        
                # # Organise guesses to be refined.
                # peaks, limits, p_fixed = get_chunk_guesses(peeks, orders, twotheta, intens,
                #                                            background_guess,
                #                                            azimu, chunks, conversion_factor,
                #                                            data_as_class, j, n,
                #                                            d_space, bounds, w_guess_fraction,
                #                                            dfour, debug)
                peaks, limits, p_fixed = get_chunk_peak_guesses(settings_as_class, chunk_data, 
                                                            background_guess,
                                                            n, w_guess_fraction, dfour, debug)
        
                # Chunks limited to no Fourier expansion so only single value per polynomial order.
                for b in range(len(background_guess)):
                    if b == 0:
                        params.add(
                            "bg_c" + str(b) + "_f" + str(0),
                            background_guess[b][0],
                            min=limits["background"][0],
                            max=limits["background"][1],
                        )
                    else:
                        params.add(
                            "bg_c" + str(b) + "_f" + str(0), background_guess[b][0]
                        )
        
                for pk in range(len(peaks)):
                                        
                    params.add(
                        "peak_" + str(pk) + "_h0",
                        peaks[pk]["height"][0],
                        min=limits["peak"][pk]["height"][0],
                        max=limits["peak"][pk]["height"][1],
                    )
                    params.add(
                        "peak_" + str(pk) + "_d0",
                        peaks[pk]["d-space"][0],
                        min=limits["peak"][pk]["d-space"][0],
                        max=limits["peak"][pk]["d-space"][1],
                    )
                    params.add(
                        "peak_" + str(pk) + "_w0",
                        peaks[pk]["width"][0],
                        min=limits["peak"][pk]["width"][0],
                        max=limits["peak"][pk]["width"][1],
                    )
                    if "profile_fixed" in settings_as_class.subfit_orders["peak"][pk]:
                        params.add(
                            "peak_" + str(pk) + "_p0",
                            peaks[pk]["profile"][0],
                            min=limits["peak"][pk]["profile"][0],
                            max=limits["peak"][pk]["profile"][1],
                            vary=False,
                        )
                    else:
                        params.add(
                            "peak_" + str(pk) + "_p0",
                            peaks[pk]["profile"][0],
                            min=limits["peak"][pk]["profile"][0],
                            max=limits["peak"][pk]["profile"][1],
                        )
    
                if debug:
                    print("Initiallised chunk fit; "+str(j)+"/"+str(len(chunks)))
                    params.pretty_print()
                    print("\n")
                    # keep the original params for plotting afterwards
                    guess = params
            
                # Run actual fit
                fit = pf.fit_model2(
                    chunk_data, # needs to contain intensity, tth, azi (as chunks), conversion factor
                    settings_as_class.subfit_orders,
                    params,
                    # intens.flatten()[chunks[j]],
                    # twotheta.flatten()[chunks[j]],
                    # azichunks[j],
                    # num_peaks=len(peaks),
                    # nterms_back=len(background_guess),
                    # conv=conversion_factor,
                    # fixed=p_fixed,
                    fit_method=fit_method,
                    weights=None,
                    # params=params,
                )  
                    
                
                # out = pf.fit_model(
                #     intens.flatten()[chunks[j]],
                #     twotheta.flatten()[chunks[j]],
                #     azichunks[j],
                #     num_peaks=len(peaks),
                #     nterms_back=len(background_guess),
                #     conv=conversion_factor,
                #     fixed=p_fixed,
                #     fit_method=fit_method,
                #     weights=None,
                #     params=params,
                # )  # , max_n_fev=peeks*default_max_f_eval)
                params = fit.params  # update lmfit parameters
                
                if debug:
                    print("Final chunk fit; "+str(j)+"/"+str(len(chunks)))
                    params.pretty_print()
                
                for i in range(len(background_guess)):
                    out_vals["bg"][i].append(params["bg_c" + str(i) + "_f0"].value)
                    out_vals["bg_err"][i].append(
                        params["bg_c" + str(i) + "_f0"].stderr
                    )
                for i in range(peeks):
                    
                    out_vals["h"][i].append(params["peak_" + str(i) + "_h0"].value)
                    out_vals["h_err"][i].append(
                        params["peak_" + str(i) + "_h0"].stderr
                    )
                    out_vals["d"][i].append(params["peak_" + str(i) + "_d0"].value)
                    out_vals["d_err"][i].append(params["peak_" + str(i) + "_d0"].stderr)
                    
                    out_vals["w"][i].append(params["peak_" + str(i) + "_w0"].value)
                    out_vals["w_err"][i].append(
                        params["peak_" + str(i) + "_w0"].stderr
                    )
                    
                    # profile should now be bound by the settings in the parameter
                    out_vals["p"][i].append(params["peak_" + str(i) + "_p0"].value)
                    out_vals["p_err"][i].append(
                        params["peak_" + str(i) + "_p0"].stderr
                    )
                    # may have to set profile error when initiate params so have appropriate error value
                    # if fixed
                    
            
                    
            
                    # Temp addition: append chunk azimuths and fitted peak intensities to file
                    '''
                    azm_plot = np.tile(azimu.flatten()[chunks[j]][0], 300)
                    azm_plot = ma.array(azm_plot, mask=(~np.isfinite(azm_plot)))
                    gmodel = Model(
                            pf.peaks_model, independent_vars=["two_theta", "azimuth"])
                    tth_range = np.linspace(np.min(
                        twotheta.flatten()[chunks[j]]),
                        np.max(twotheta.flatten()[chunks[j]]),
                        azm_plot.size,
                    )
                    mod_plot = gmodel.eval(
                        params=params,
                        two_theta=tth_range,
                        azimuth=azm_plot,
                        conv=conversion_factor,
                    )
                    # Get the highest peak
                    temp_int = max(mod_plot)
                    temp_peak_ints = [temp_int]
                    temp_x = tth_range[np.where(mod_plot == temp_int)][0]
                    temp_tth = [temp_x]
                    temp_widths = []
                    temp_tth_range = tth_range
                    temp_mod_plot = mod_plot
                    # Find the widest peak width
                    for i in range(peeks):
                        temp_widths.append(params["peak_" + str(i) + "_w0"].value)
                    temp_max_width = max(temp_widths)
                    # print(temp_int, temp_x, temp_max_width)
                    # Use the max width to mask out array to search for next peak
                    for pk in range(len(peaks)-1):
                        upper = temp_x+(2*temp_max_width)
                        lower = temp_x-(2*temp_max_width)
                        # print(upper, lower)
                        # temp_int = max(mod_plot[np.where(temp_tth_range)])
                        temp_mod_plot = temp_mod_plot[np.where((temp_tth_range >= upper) | (temp_tth_range <= lower))]
                        temp_int = max(temp_mod_plot)
                        temp_peak_ints.append(temp_int)
                        # temp_int = max(mod_plot[np.where((temp_tth_range >= upper) | (temp_tth_range <= lower))])
                        temp_x = temp_tth_range[np.where(temp_mod_plot == temp_int)][0]
                        temp_tth.append(temp_x)
                        temp_tth_range = (temp_tth_range[(temp_tth_range >= upper) | (temp_tth_range <= lower)])
                        # print('peak', temp_peak_ints, temp_tth)
            
                    # Work out which peak is which - assume in 2theta order
                    temp_tth = sorted(temp_tth)
                    # Write to file per sub-pattern per peak
                    for pk in range(len(peaks)):
                        filename = io.make_outfile_name(
                                    f_name,
                                    directory=fdir,
                                    additional_text="ChunksHeights",
                                    orders=orders,
                                    extension=".txt",
                                    overwrite=True,
                                )
                        # print(azichunks[j], temp_peak_ints[pk])
                        if j==0:
                            with open(filename, "w") as myfile:
                                myfile.write("%f %f\n"  % (azichunks[j], temp_peak_ints[pk]))
                        else:
                            with open(filename, "a") as myfile:
                                myfile.write("%f %f\n"  % (azichunks[j], temp_peak_ints[pk]))
            
                    # print(stop)
                    # debug = True
                    '''
            
                # plot the fits.
                if debug:
                    tth_plot = chunk_data.tth#twotheta.flatten()[chunks[j]]
                    int_plot = chunk_data.intensity#intens.flatten()[chunks[j]]
                    azm_plot = chunk_data.azm#np.tile(chunk_data.azm.flatten()[chunks[j]][0], 300)
                    azm_plot = ma.array(azm_plot, mask=(~np.isfinite(azm_plot)))
                    # FIX ME: required for plotting energy dispersive data.
                    gmodel = Model(
                        pf.peaks_model2, independent_vars=["two_theta", "azimuth"], data_class = chunk_data,
                                orders = settings_as_class.subfit_orders, 
                    )
                    tth_range = np.linspace(
                        # np.min(twotheta.flatten()[chunks[j]]),
                        # np.max(twotheta.flatten()[chunks[j]]),
                        np.min(chunk_data.tth),
                        np.max(chunk_data.tth),
                        azm_plot.size,
                    )
                    mod_plot = gmodel.eval(
                        params=params,
                        two_theta=tth_range,
                        azimuth=azm_plot,
                        #conv=conversion_factor,
                    )
                    guess_plot = gmodel.eval(
                        params=guess,
                        two_theta=tth_range,
                        azimuth=azm_plot,
                        #conv=conversion_factor,
                    )
                    plt.plot(tth_plot, int_plot, ".", label="data")
                    plt.plot(
                        tth_range,
                        np.array(guess_plot).flatten(),
                        marker="",
                        color="green",
                        linewidth=2,
                        linestyle="dashed",
                        label="guess",
                    )
                    plt.plot(
                        tth_range,
                        np.array(mod_plot).flatten(),
                        marker="",
                        color="red",
                        linewidth=2,
                        label="fit",
                    )
                    #plt.xlim(tth_range)
                    plt.legend()
                    plt.title(((io.peak_string(settings_as_class.subfit_orders) + "; azimuth = %.1f" ) % azichunks[j]))
                    plt.show()
        
    
    return out_vals, new_azi_chunks
    

def fit_series(master_params, data, settings_as_class, debug=False, save_fit=False):
    
    
    orders = settings_as_class.subfit_orders
    
    
    # Initiate background parameters and perform an initial fit
    comp = "bg"
    for b in range(len(orders["background"])):
        param_str = "bg_c" + str(b)
        comp = "f"
        
        master_params.pretty_print()
        master_params = pf.un_vary_params(
            master_params, param_str, comp
        )  # set other parameters to not vary
        master_params = pf.vary_params(
            master_params, param_str, comp
        )  # set these parameters to vary
        if isinstance(
            orders["background"][b], list
        ):  # set part of these parameters to not vary
            master_params = pf.un_vary_part_params(
                master_params, param_str, comp, orders["background"][b]
            )
            
        master_params.pretty_print()
        
        azimuth = data[1]
        data_vals = data[0]["bg"][b]
        data_val_errors = data[0]["bg_err"][b]
            
        print(data_vals)
        print(data_val_errors)
                
        fout = pf.coefficient_fit(
            azimuth=azimuth,
            ydata=data_vals,
            inp_param=master_params,
            param_str=param_str + "_" + comp,
            symmetry=1,
            errs=data_val_errors,
            fit_method="leastsq",
        )
        master_params = fout.params
        
    # initiate peak(s)
    for j in range(len(orders["peak"])):
        
        # defines peak string to start parameter name
        param_str = "peak_" + str(j)
    
        comp_list = ["h", "d", "w", "p"]
        comp_names = ["height", "d-space", "width", "profile"]
        # arr_names = ["new_h_all", "new_d0", "new_w_all", "new_p_all"]
        # arr_err_names = [
        #     "new_h_all_err",
        #     "new_d0_err",
        #     "new_w_all_err",
        #     "new_p_all_err",
        # ]
    
        for cp in range(len(comp_list)):
            comp = comp_list[cp]
            if comp == "d":
                symmetry = 1
            else:
                symmetry = orders["peak"][j]["symmetry"]
                
                
            if comp_names[cp] + "_fixed" in orders["peak"][j]:
                fixed = 1
                # data_vals are not needed
                # data_val_errors are not needed.
            else:
                fixed = 0
                data_vals = data[0][comp][j]
                data_val_errors = data[0][comp][j]
                
            #     # FIX ME: this was not checked properly.the values it feeds are not necessarily correct
            #     # and the fixed parameters might be fit for.
            # coeff_type = pf.params_get_type(orders, comp, peak=j)
            n_coeff = pf.get_number_coeff(
                orders, comp, peak=j, azimuths=data[1]
            )
            # master_params = pf.initiate_params(
            #     master_params,
            #     param_str,
            #     comp,
            #     coeff_type=coeff_type,
            #     num_coeff=n_coeff,
            #     trig_orders=orders["peak"][j][comp_names[cp]],
            #     limits=lims[comp_names[cp]],
            #     value=vals,
            # )
            master_params = pf.un_vary_params(
                master_params, param_str, comp
            )  # set other parameters to not vary
            if fixed == 0:
                master_params = pf.vary_params(
                    master_params, param_str, comp
                )  # set these parameters to vary
                if isinstance(
                    orders["peak"][j][comp_names[cp]], list
                ):  # set part of these parameters to not vary
                    master_params = pf.un_vary_part_params(
                        master_params,
                        param_str,
                        comp,
                        orders["peak"][j][comp_names[cp]],
                    )
                # catch to make sure there are not more coefficients than chunks
                if n_coeff > len(np.unique(data[1])):  
                    o = int(np.floor(len(np.unique(data[1])) / 2 - 1))
                    un_vary = [x for x in range(0, o)]
                    master_params = pf.un_vary_part_params(master_params, param_str, comp, un_vary)
                fout = pf.coefficient_fit(
                    azimuth=data[1],
                    ydata=data_vals,
                    inp_param=master_params,
                    param_str=param_str + "_" + comp,
                    symmetry=symmetry,
                    errs=data_val_errors,
                    fit_method="leastsq",
                )
    
            master_params = fout.params
            
            # FIX ME. Check which params should be varying and which should not.
            # Need to incorporate vary and un-vary params as well as partial vary
    
    if 1:#debug:
        print("Parameters after initial Fourier fits")
        master_params.pretty_print()
    
    
        # plot output of fourier fits....

        y_lims = np.array([np.min(data[1]), np.max(data[1])])
        y_lims = np.around(y_lims / 180) * 180
        azi_plot = range(np.int(y_lims[0]), np.int(y_lims[1]), 2)
        # azi_plot = range(0, 360, 2)
        gmodel = Model(pf.coefficient_expand, independent_vars=["azimuth"])
    
        fig = plt.figure()
        
        
        comp_list = ["h", "d", "w", "p"]
        comp_names = ["height", "d-space", "width", "profile"]
        
        
        # loop over peak parameters and plot.
        ax=[]
        for i in range(len(comp_list)):
            for j in range(len(orders["peak"])):
            
                ax.append(fig.add_subplot(5, 1, i+1))
                ax[i].set_title(comp_names[i])
                for j in range(len(orders["peak"])):
                    param_str = "peak_" + str(j)
                    comp = comp_list[i]
                    if "symmetry" in orders["peak"][j].keys() and comp != "d":
                        symm = orders["peak"][j]["symmetry"]
                    else:
                        symm = 1
                    temp = pf.gather_param_errs_to_list(
                        master_params, param_str, comp
                    )
                    temp_tp = pf.get_series_type(master_params, param_str, comp)
                    if temp_tp == 5:
                        az_plt = np.array(data[1])
                    else:
                        az_plt = azi_plot
                    gmod_plot = gmodel.eval(
                            params=master_params, 
                            azimuth=np.array(az_plt)*symm, 
                            param=temp[0], 
                            coeff_type=temp_tp
                    )
                    ax[i].scatter(data[1], data[0][comp][j], s=10)
                    ax[i].plot(az_plt, gmod_plot, )
        
    
        #plot background 
        for k in range(len(orders["background"])):
            x_plt = len(orders["background"])
            y_plt = len(orders["background"]) * 4 + k +1
            print(x_plt, y_plt, i+k+1)
            ax.append(fig.add_subplot(5, x_plt, y_plt))
            ax[i+k+1].set_title("Background "+str(k))
    
            param_str = "bg_c" + str(k)
            comp = "f"
            temp = pf.gather_param_errs_to_list(
                master_params, param_str, comp
            )
            temp_tp = pf.get_series_type(master_params, param_str, comp)
            if temp_tp == 5:
                az_plt = np.array(data[1])
            else:
                az_plt = azi_plot
            gmod_plot = gmodel.eval(
                    params=master_params, 
                    azimuth=np.array(az_plt),
                    param=temp[0], 
                    coeff_type=temp_tp
            )
            ax[i+k+1].scatter(data[1], data[0]["bg"][k], s=10)
            ax[i+k+1].plot(az_plt, gmod_plot, )
    
        fig.suptitle(io.peak_string(orders) + "; Fits to Chunks")
    
        if save_fit:
            filename = io.make_outfile_name(
                settings_as_class.subfit_filename,
                directory=settings_as_class.output_directory,
                additional_text="ChunksFit",
                orders=orders,
                extension=".png",
                overwrite=False,
            )
            fig.savefig(filename)
        plt.show()
        plt.close()            
            
            
            
            
        # ax1 = fig.add_subplot(5, 1, 1)
        # ax1.set_title("D-spacing")
        # for j in range(len(orders["peak"])):
        #     param_str = "peak_" + str(j)
        #     comp = "d"
        #     temp = pf.gather_param_errs_to_list(
        #         master_params, param_str, comp
        #     )
        #     temp_tp = pf.get_series_type(master_params, param_str, comp)
        #     if temp_tp == 5:
        #         az_plt = np.array(data[1])
        #     else:
        #         az_plt = azi_plot
        #     gmod_plot = gmodel.eval(
        #             params=master_params, 
        #             azimuth=np.array(az_plt), 
        #             param=temp[0], 
        #             coeff_type=temp_tp
        #     )
        #     ax1.scatter(data[1], data[1]["d"][j], s=10)
        #     ax1.plot(az_plt, gmod_plot, )
    
    
        # # plt.subplot(512)
        # ax2 = fig.add_subplot(5, 1, 2)
        # ax2.set_title("height")
        # for j in range(len(orders["peak"])):
        #     if "symmetry" in orders["peak"][j].keys():
        #         symm = orders["peak"][j]["symmetry"]
        #     else:
        #         symm = 1
        #     param_str = "peak_" + str(j)
        #     comp = "h"
        #     temp = pf.gather_param_errs_to_list(
        #         master_params, param_str, comp
        #     )
        #     temp_tp = pf.get_series_type(master_params, param_str, comp)
        #     if temp_tp == 5:
        #         az_plt = np.array(data[1])
        #     else:
        #         az_plt = azi_plot
        #     gmod_plot = gmodel.eval(
        #             params=master_params, 
        #             azimuth=np.array(az_plt) * symm, 
        #             param=temp[0], 
        #             coeff_type=temp_tp
        #     )
        #     ax2.scatter(data[1], data[1]["h"][j], s=10)
        #     ax2.plot(az_plt, gmod_plot, )
    
        # ax3 = fig.add_subplot(5, 1, 3)
        # # plt.subplot(513)
        # ax3.set_title("width")
        # for j in range(len(orders["peak"])):
        #     if "symmetry" in orders["peak"][j].keys():
        #         symm = orders["peak"][j]["symmetry"]
        #     else:
        #         symm = 1
        #     param_str = "peak_" + str(j)
        #     comp = "w"
        #     temp = pf.gather_param_errs_to_list(
        #         master_params, param_str, comp
        #     )
        #     temp_tp = pf.get_series_type(master_params, param_str, comp)
        #     if temp_tp == 5:
        #         az_plt = np.array(data[1])
        #     else:
        #         az_plt = azi_plot
        #     gmod_plot = gmodel.eval(
        #             params=master_params, 
        #             azimuth=np.array(az_plt) * symm, 
        #             param=temp[0], 
        #             coeff_type=temp_tp
        #     )
        #     ax3.scatter(data[1], data[1]["w"][j], s=10)
        #     ax3.plot(az_plt, gmod_plot, )
    
        # ax4 = fig.add_subplot(5, 1, 4)
        # # plt.subplot(514)
        # ax4.set_title("Profile")
        # for j in range(len(orders["peak"])):
        #     if "symmetry" in orders["peak"][j].keys():
        #         symm = orders["peak"][j]["symmetry"]
        #     else:
        #         symm = 1
        #     param_str = "peak_" + str(j)
        #     comp = "p"
        #     temp = pf.gather_param_errs_to_list(
        #         master_params, param_str, comp
        #     )
        #     temp_tp = pf.get_series_type(master_params, param_str, comp)
        #     if temp_tp == 5:
        #         az_plt = np.array(data[1])
        #     else:
        #         az_plt = azi_plot
        #     gmod_plot = gmodel.eval(
        #             params=master_params, 
        #             azimuth=np.array(az_plt) * symm, 
        #             param=temp[0], 
        #             coeff_type=temp_tp
        #     )
        #     ax4.scatter(data[1], data[1]["p"][j], s=10)
        #     ax4.plot(az_plt, gmod_plot, )
    
        # for k in range(len(len_bg)):
        #     x_plt = len(len_bg)
        #     y_plt = len(len_bg) * 4 + k + 1
        #     ax5 = fig.add_subplot(5, x_plt, y_plt)
        #     ax5.set_title("Background")
    
        #     param_str = "bg_c" + str(k)
        #     comp = "f"
        #     temp = pf.gather_param_errs_to_list(
        #         master_params, param_str, comp
        #     )
        #     temp_tp = pf.get_series_type(master_params, param_str, comp)
        #     if temp_tp == 5:
        #         az_plt = np.array(data[1])
        #     else:
        #         az_plt = azi_plot
        #     gmod_plot = gmodel.eval(
        #             params=master_params, 
        #             azimuth=np.array(az_plt),
        #             param=temp[0], 
        #             coeff_type=temp_tp
        #     )
        #     ax5.scatter(data[1], new_bg_all[k], s=10)
        #     ax5.plot(az_plt, gmod_plot, )
    
        # fig.suptitle(io.peak_string(orders) + "; Fits to Chunks")
    
        # if save_fit:
        #     filename = io.make_outfile_name(
        #         f_name,
        #         directory=fdir,
        #         additional_text="ChunksFit",
        #         orders=orders,
        #         extension=".png",
        #         overwrite=False,
        #     )
        #     fig.savefig(filename)
        # plt.show()
        # plt.close()
    
    # put fits into new_params data structure.
    # new_params = ff.create_new_params(peeks, dfour, hfour, wfour, pfour, bgfour, orders['peak'])