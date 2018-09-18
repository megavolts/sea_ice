# ! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
seaice.core.profile.py : toolbox to work on property profile

"""
import logging
import seaice
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

__name__ = "profile"
__author__ = "Marc Oggier"
__license__ = "GPL"
__version__ = "1.1"
__maintainer__ = "Marc Oggier"
__contact__ = "Marc Oggier"
__email__ = "moggier@alaska.edu"
__status__ = "dev"
__date__ = "2017/09/13"
__comment__ = "profile.py contained function to handle property profile"
__CoreVersion__ = 1.1

__all__ = ["discretize_profile", "select_profile", "delete_profile", "uniformize_section"]

TOL = 1e-6
subvariable_dict = {'conductivity': ['conductivity measurement temperature']}

class Profile(pd.DataFrame):
    """

    """
    def __getstate__(self):
        d = self.__dict__.copy()
        if 'logger' in d.keys():
            d['logger'] = d['logger'].name
        return d

    def __setstate__(self, d):
        if 'logger' in d.keys():
            d['logger'] = logging.getLogger(d['logger'])

    def __init__(self, *args, **kwargs):
        super(Profile, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def get_property(self):
        """
        Return physical properties stored in the profiles

        :return: str, list
            List of property or None if there is no property stored in the profile
        """

        if 'variable' not in self.keys():
            return None
        else:
            property = []
            for var_group in self.variable.unique():
                property += var_group.split(', ')
            return property

    def get_name(self):
        """
        Return the core name of the profile

        :return name: string
        """
        self.logger = logging.getLogger(__name__)
        name = self.name.unique()
        if name.__len__() > 1:
            self.logger.warning(' %s more than one name in the profile: %s ' % (name[0], ', '.join(name)))
        return self.name.unique()[0]

    def clean(self, inplace=True):
        """
        Clean profile by removing all empty property
        :return:
        """
        self.logger = logging.getLogger(__name__)

        variable = self.get_property()
        null_property = self.columns[self.isnull().all(axis=0)].tolist()
        kept_property = [prop for prop in variable if prop not in null_property]

        if null_property:
            self.logger.info('Property are empty, deleting: %s' % ', '.join(null_property))
            if kept_property:
                self['variable'] = None
            else:
                self['variable'] = ', '.join(kept_property)

        if inplace:
            self.dropna(axis=1, how='all', inplace=True)
        else:
            return self.dropna(axis=1, how='all')

    def add_profile(self, profile):
        """
        Add new profile to existing profile.
        Profile name should match.
        :param profile: seaice.Profile()
        """
        if profile.get_name() is self.get_name():
            self = self.merge(profile, how='outer').reset_index(drop=True)
            return self
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.warning('Profile name does not match %s, %s' %(profile.get_name(). self.get_name()))

    def delete_property(self, property):
        """
        Remove property

        :param property:
        :return:
        """
        if not isinstance(property, list):
            property = [property]

        new_property = self.get_property()
        for prop in property:
            if prop in self.get_property():
                self.drop(prop, axis=1, inplace=True)
                new_property.remove(prop)

                if prop in subvariable_dict.keys():
                    for _subprop in subvariable_dict[prop]:
                        self.drop(_subprop, axis=1, inplace=True)

         # write variable
        self['variable'] = ', '.join(new_property)

    def discretize(self, y_bins=None, y_mid=None, display_figure=False, fill_gap=False, fill_extremity=False):
        return 'nothing'

    def set_vertical_reference(profile, h_ref=None, new_v_ref=None, inplace=True):
        """

        :param profile:
        :param h_ref:
        :param new_v_ref: default, same as profile origin
        :return:
        """
        logger = logging.getLogger(__name__)
        if new_v_ref is None:
            if profile.v_ref.unique().__len__() > 1:
                logger.error("vertical reference for profile are not consistent")
            else:
                new_v_ref = profile.v_ref.unique()[0]

        if inplace:
            new_profile = set_profile_orientation(profile, new_v_ref)
        else:
            new_profile = set_profile_orientation(profile.copy(), new_v_ref)

        if h_ref is not None:
            new_df = new_profile['y_low'].apply(lambda x: x - h_ref)
            new_df = pd.concat([new_df, new_profile['y_mid'].apply(lambda x: x - h_ref)], axis=1)
            new_df = pd.concat([new_df, new_profile['y_sup'].apply(lambda x: x - h_ref)], axis=1)
            new_profile.update(new_df)
        return new_profile

    def drop_empty_property(self):
        empty = [prop for prop in self.get_property() if self[prop].isnull().all()]
        self.variable = ', '.join([prop for prop in self.get_property() if prop not in empty])
        self.drop(columns=empty, axis=1, inplace=True)

    @property
    def _constructor(self):
        return Profile

    # DEPRECATED
    def get_variable(self):
        self.logger = logging.getLogger(__name__)
        self.logger.warning('get_variable is deprecated. Use get_property')
        return self.get_property()


def discretize_profile(profile, y_bins=None, y_mid=None, display_figure=False, fill_gap=False, fill_extremity=False):
    """
    :param profile:
    :param y_bins:
    :param y_mid:
    :param display_figure: boolean, default False
    :param fill_gap: boolean, default True

    :param fill_extremity: boolean, default False
    :return:
        profile
    """
    # TODO conductivity cannot be discretized as it's temperature non linearly dependant of the measurement temperature,
    # unless temperature profile of measurement temperature is isotherm.

    logger = logging.getLogger(__name__)

    if profile.empty:
        logger.warning("Discretization impossible, empty profile")
    else:
        if 'name' in profile.keys():
            logger.info("Processing %s" % profile.name.unique()[0])
        else:
            logger.info("Processing core")

    v_ref = profile.v_ref.unique()[0]

    # VARIABLES CHECK
    if y_bins is None and y_mid is None:
        y_bins = pd.Series(profile.y_low.dropna().tolist() + profile.y_sup.dropna().tolist()).sort_values().unique()
        y_mid = profile.y_mid.dropna().sort_values().unique()
        logger.info("y_bins and y_mid are empty, creating from profile")
    elif y_bins is None and y_mid is not None:
            logger.info("y_bins is empty, creating from given y_mid")
            y_mid = y_mid.sort_values().values
            dy = np.diff(y_mid) / 2
            y_bins = np.concatenate([[y_mid[0] - dy[0]], y_mid[:-1] + dy, [y_mid[-1] + dy[-1]]])
            if y_bins[0] < 0:
                y_bins[0] = 0
    else:
            y_mid = np.diff(y_bins) / 2 + y_bins[:-1]
            logger.info("y_mid is empty, creating from given y_bins")

    y_bins = np.array(y_bins)
    y_mid = np.array(y_mid)

    discretized_profile = pd.DataFrame()


    #TODO : discretization for temperature by interpolation
    for variable in profile.variable.unique():
        # select variable
        _profile = seaice.core.profile.Profile(profile[profile.variable == variable])
        _variables = []
        _del_variables = []
        for _variable in _profile.get_variable():
            # remove properties not linearly dependant of temperature
            if not _variable in ['conductivity']:
                logger.info('%s will be discretized' % _variable)
                if not _variable in _variables:
                    _variables.append(_variable)
                # add other variable dependant
                if _variable in subvariable_dict:
                    for _subvar in subvariable_dict[_variable]:
                        _variables.append(_subvar)
            else:
                logger.warning('%s variable cannot be discretized' % _variable)
                _del_variables.append(_variable)
                # add other variable dependant
                if _variable in subvariable_dict:
                    for _subvar in subvariable_dict[_variable]:
                        _del_variables.append(_subvar)

        # index of variables
        n_var = _variables.__len__()

        #TODO switch between continuous or not continuous is evidence of continuous profile like temperature
        # continuous profile (temperature-like)
        if is_continuous(_profile):
            yx = _profile[['y_mid'] + _variables].set_index('y_mid').sort_index()
            y2 = y_mid
            x2 = np.array([np.interp(y2, yx.index, yx[_var], left=np.nan, right=np.nan) for _var in _variables])

            y2x = pd.DataFrame(x2.transpose(), columns=_variables, index=y2)
            for index in yx.index:
                y2x.loc[abs(y2x.index - index) < 1e-6, _variables] = yx.loc[yx.index == index, _variables].values

            # compute weight, if y_mid is in min(yx) < y_mid < max(yx)
            w = [1 if yx.index[0] - TOL <= y <= yx.index[-1] + TOL else 0 for y in y_mid ]

            # add the temperature profile extremum value
            if not any(abs(yx.index[0]-y2) < TOL):
                y2x.loc[yx.index[0], _variables] = yx.loc[yx.index == yx.index[0], _variables].values
                w = w + [0]
            if not any(abs(yx.index[-1]-y2) < TOL):
                y2x.loc[yx.index[-1], _variables] = yx.loc[yx.index == yx.index[-1], _variables].values
                w = w + [0]

            temp = pd.DataFrame(columns=profile.columns.tolist(), index=range(y2x.__len__()))
            temp.update(y2x.reset_index().rename(columns={'index': 'y_mid'}))
            temp['weight'] = pd.Series(w, index=temp.index)
            temp = temp.sort_values('y_mid').reset_index(drop=True)
            profile_prop = profile.loc[profile.variable == variable].head(1)
            profile_prop = profile_prop.drop(_variables+_del_variables, 1)
            profile_prop['variable'] = ', '.join(_variables)
            if 'y_low' in profile_prop:
                profile_prop = profile_prop.drop('y_low', 1)
            profile_prop = profile_prop.drop('y_mid', 1)
            if 'y_sup' in profile_prop:
                profile_prop = profile_prop.drop('y_sup', 1)

            temp.update(pd.DataFrame([profile_prop.iloc[0].tolist()], columns=profile_prop.columns.tolist(),
                                     index=temp.index.tolist()))
            if 'date' in temp:
                temp['date'] = temp['date'].astype('datetime64[ns]')

            if display_figure:
                for _var in _variables:
                    plt.figure()
                    yx = yx.reset_index()
                    plt.plot(yx[_var], yx['y_mid'], 'k')
                    plt.plot(temp[_var], temp['y_mid'], 'xr')
                    if 'name' in profile_prop.keys():
                        plt.title(profile_prop.name.unique()[0] + ' - ' + _var)
                    plt.show()
        # step profile (salinity-like)
        else:
            n_s0 = 2
            n_s1 = n_s0 + n_var

            if v_ref == 'bottom':
                yx = _profile[['y_sup', 'y_low'] + _variables].sort_values(by='y_low')
                if (yx.y_sup.head(1) > yx.y_low.head(1)).all():
                    yx = _profile[['y_low', 'y_sup'] + _variables].sort_values(by='y_low')
            else:
                yx = _profile[['y_low', 'y_sup'] + _variables ].sort_values(by='y_low').astype(float)

            # drop all np.nan value
            # yx = yx.dropna(axis=0, subset=['y_low', 'y_sup'], thresh=2).values
            yx = yx.values

            # if missing section, add an emtpy section with np.nan as property value
            yx_new = []
            for row in range(yx[:, 0].__len__()-1):
                yx_new.append(yx[row])
                if abs(yx[row, 1]-yx[row+1, 0]) > TOL:
                    yx_new.append([yx[row, 1], yx[row+1, 0]]+  [np.nan]*_variables.__len__())
            yx_new.append(yx[row+1, :])
            yx = np.array(yx_new)
            del yx_new

            if fill_gap:
                value = pd.Series(yx[:, 2])
                value_low = value.fillna(method='ffill')
                value_sup = value.fillna(method='bfill')

                ymid = pd.Series(yx[:, 0]+(yx[:, 1]-yx[:, 0])/2)
                ymid2 = pd.Series(None, index=value.index)
                ymid2[np.isnan(value)] = ymid[np.isnan(value)]

                dy = pd.DataFrame(yx[:, 0:2], columns=['y_low', 'y_sup'])
                dy2 = pd.DataFrame([[None, None]], index=value.index, columns=['y_low', 'y_sup'])
                dy2[~np.isnan(value)] = dy[~np.isnan(value)]
                dy2w = dy2['y_low'].fillna(method='bfill') - dy2['y_sup'].fillna(method='ffill')
                new_value = value_low + (ymid2 - dy2['y_sup'].fillna(method='ffill'))*(value_sup-value_low)/dy2w
                value.update(new_value)

                yx[:, 2] = value

            x_step = []
            y_step = []
            w_step = []  # weight of the bin, defined as the portion on which the property is define
            # yx and y_bins should be ascendent suit
            if (np.diff(y_bins) < 0).all():
                logger.info("y_bins is descending reverting the list")
                y_bins = y_bins[::-1]
            elif (np.diff(y_bins) > 0).all():
                logger.debug("y_bins is ascending")
            else:
                logger.info("y_bins is not sorted")
            if (np.diff(yx[:, 0]) < 0).all():
                logger.info("yx is descending reverting the list")
                yx = yx[::-1, :]
            elif (np.diff(yx[:, 0]) > 0).all():
                logger.debug("yx is ascending")
            else:
                logger.info("yx is not sorted")


            for ii_bin in range(y_bins.__len__()-1):
                a = np.flatnonzero((yx[:, 0] - y_bins[ii_bin] < -TOL) & ( y_bins[ii_bin] - yx[:, 1] < -TOL))
                a = np.concatenate((a, np.flatnonzero((y_bins[ii_bin] - yx[:, 0] <= TOL) & (yx[:, 1] - y_bins[ii_bin+1] <= TOL))))
                a = np.concatenate((a, np.flatnonzero((yx[:, 0] - y_bins[ii_bin+1] < -TOL) & ( y_bins[ii_bin+1] - yx[:, 1] < -TOL))))
                a = np.unique(a)

                # print('section %.4f - %.4f' %(y_bins[ii_bin], y_bins[ii_bin+1]))
                # print('- original section %s' % ', '.join(a.astype(str)))
                # for yx_a in a:
                #     print('\t %.4f - %.4f' % (yx[yx_a][0], yx[yx_a][1]))

                if a.size != 0:
                    S = [np.nan]*n_var
                    L = np.zeros_like(S)
                    L_nan = np.zeros_like(S)
                    a_ii = 0
                    if yx[a[a_ii], 0] - y_bins[ii_bin] < -TOL:
                        S_temp = yx[a[a_ii], n_s0:n_s1]*(yx[a[a_ii], 1] - y_bins[ii_bin])
                        S = np.nansum([S, S_temp], axis=0)

                        l = yx[a[a_ii], 1] - y_bins[ii_bin]
                        L = np.nansum([L, l * ~np.isnan(S_temp)], axis=0)
                        L_nan = np.nansum([L, l * np.isnan(S_temp)], axis=0)
                        # print(y_bins[ii_bin], yx[a[a_ii], 1], S_temp)
                        a_ii += 1
                    while ii_bin+1 <= y_bins.shape[0]-1 and a_ii < a.shape[0]-1 and yx[a[a_ii], 1] - y_bins[ii_bin+1] < -TOL:
                        S_temp = yx[a[a_ii], n_s0:n_s1] * (yx[a[a_ii], 1]-yx[a[a_ii], 0])
                        S = np.nansum([S, S_temp], axis=0)
                        l = yx[a[a_ii], 1]-yx[a[a_ii], 0]
                        L = np.nansum([L, l * ~np.isnan(S_temp)], axis=0)
                        L_nan = np.nansum([L_nan, l * np.isnan(S_temp)], axis=0)
                        # print(yx[a[a_ii], 0], yx[a[a_ii], 1], S_temp)
                        a_ii += 1

                    # check if a_ii-1 was not the last element of a
                    if a_ii < a.size:
                        if yx[a[a_ii], 1] - y_bins[ii_bin+1] > -TOL:
                            S_temp = yx[a[a_ii], n_s0:n_s1] * (y_bins[ii_bin+1] -yx[a[a_ii], 0])
                            S = np.nansum([S, S_temp], axis=0)
                            l = y_bins[ii_bin+1] - yx[a[a_ii], 0]
                            L = np.nansum([L, l * ~np.isnan(S_temp)], axis=0)
                            L_nan = np.nansum([L_nan, l * np.isnan(S_temp)], axis=0)
                            # print(yx[a[a_ii], 0], y_bins[ii_bin+1], S_temp)
                        elif yx[a[a_ii], 1] - y_bins[ii_bin + 1] < -TOL:
                            S_temp = yx[a[a_ii], n_s0:n_s1] * (yx[a[a_ii], 1] -yx[a[a_ii], 0])
                            S = np.nansum([S, S_temp], axis=0)
                            l = yx[a[a_ii], 1] -yx[a[a_ii], 0]
                            L = np.nansum([L, l * ~np.isnan(S_temp)], axis=0)
                            L_nan = np.nansum([L_nan, l * np.isnan(S_temp)], axis=0)
                            # print(yx[a[a_ii], 0], yx[a[a_ii], 1], S_temp)

                    w = L / (y_bins[ii_bin + 1]-y_bins[ii_bin])
                    L[L == 0] = np.nan
                    S = S / L

                    if yx[a[0], 0] - y_bins[ii_bin] > TOL and not fill_extremity:
                        y_step.append(yx[a[0], 0])
                        y_step.append(y_bins[ii_bin + 1])
                    elif yx[a[-1], 1] - y_bins[ii_bin + 1] < -TOL and not fill_extremity:
                        y_step.append(y_bins[ii_bin])
                        y_step.append(yx[a[-1], 1])
                    else:
                        y_step.append(y_bins[ii_bin])
                        y_step.append(y_bins[ii_bin + 1])
                    x_step.append(S)
                    w_step.append(w)

            x_step = np.array(x_step).transpose()
            w_step = np.array(w_step).transpose()
            w_variables = ['w_'+ _var for _var in _variables]
            temp = pd.DataFrame(columns=profile.columns.tolist(), index=range(np.unique(y_step).__len__() - 1))
            for w in w_variables:
                temp[w] = [np.nan]*temp.__len__()
            temp.update(pd.DataFrame(np.vstack((np.unique(y_step)[:-1],
                                                np.unique(y_step)[:-1] + np.diff(np.unique(y_step)) / 2,
                                                np.unique(y_step)[1:],
                                                w_step, x_step)).transpose(),
                                     columns=['y_low', 'y_mid', 'y_sup'] + w_variables + _variables,
                                     index=temp.index[0:np.unique(y_step).__len__() - 1]))

            # core attribute
            profile_prop = _profile.head(1).copy()
            profile_prop['variable'] = (', ').join(_variables)
            profile_prop = profile_prop.drop('y_low', 1)
            profile_prop = profile_prop.drop('y_mid', 1)
            profile_prop = profile_prop.drop('y_sup', 1)
            profile_prop = profile_prop.drop(_variables+_del_variables, axis=1)
            temp.update(pd.DataFrame([profile_prop.iloc[0].tolist()], columns=profile_prop.columns.tolist(),
                                     index=temp.index.tolist()))
            if 'date' in temp:
                temp['date'] = temp['date'].astype('datetime64[ns]')

            if display_figure:
                for n in range(0, n_var):
                    plt.figure()
                    x = []
                    y = []
                    for ii in range(yx[:, 0].__len__()):
                        y.append(yx[ii, 0])
                        y.append(yx[ii, 1])
                        x.append(yx[ii, 2+n])
                        x.append(yx[ii, 2+n])
                    plt.step(x, y, 'bx', label='original')
                    plt.step([x for x in x_step[n] for _ in (0, 1)], y_step, 'ro', linestyle='--', label='discretized')
                    if 'name' in _profile.keys():
                        plt.title(_profile.name.unique()[0] + ' - ' + _variables[n])
                    else:
                        plt.title(_variables[n])
                    plt.legend()
                    plt.show()

        temp = temp.apply(pd.to_numeric, errors='ignore')

        discretized_profile = discretized_profile.append(temp, sort=False)
    return discretized_profile


def set_profile_orientation(profile, v_ref):
    """

    :param profile:
    :param v_ref: new reference 'top', 'bottom'
    :return:
    """
    logger = logging.getLogger(__name__)

    for variable in profile.variable.unique():
        # look for ice thickness:
        if profile[profile.variable == variable].v_ref.unique().__len__() > 1:
            logger.error("vertical reference for profile are not consistent")
        if not profile[profile.variable == variable].v_ref.unique().tolist()[0] == v_ref:
            # search ice core length, or ice thickness
            if 'ice_thickness' in profile.keys() and \
                    not np.isnan(profile[profile.variable == variable].ice_thickness.astype(float)).all():
                    lc = profile[profile.variable == variable].ice_thickness.astype(float).dropna().unique()[0]
            elif 'length' in profile.keys() and \
                    not np.isnan(profile[profile.variable == variable].length.astype(float)).all():
                    lc = profile[profile.variable == variable].length.astype(float).dropna().unique()[0]
            else:
                lc = None

            if lc is None:
                if 'name' in profile.keys():
                    logger.warning("Mising core length or ice thickness, impossible to set profile orientation to %s.\
                    Deleting profile (%s)" %(v_ref, profile.name.unique()[0]))
                else:
                    logger.warning("Mising core length or ice thickness, impossible to set profile orientation to %s.\
                    Deleting profile" % v_ref)
                profile = delete_profile(profile, {'variable': variable})
            else:
                new_df = profile.loc[profile.variable == variable, 'y_low'].apply(lambda x: lc - x)
                new_df = pd.concat([new_df, profile.loc[profile.variable == variable, 'y_mid'].apply(lambda x: lc - x)], axis = 1)
                new_df = pd.concat([new_df, profile.loc[profile.variable == variable, 'y_sup'].apply(lambda x: lc - x)], axis = 1)
                new_df['v_ref'] = 'bottom'
                profile.update(new_df)
        else:
            logger.info('profile orientiation already set')

    return profile



def delete_variables(ics_stack, variables2del):
    if not isinstance(variables2del, list):
        variables2del = [variables2del]
    for variable in variables2del:
        if variable in ics_stack.keys():
            if variable in ics_stack.get_variable():
                # delete variable column
                ics_stack.drop(variable, axis=1, inplace=True)

                # delete associated subvariable column
                if variable in subvariable_dict:
                    for subvariable in subvariable_dict[variable]:
                        ics_stack.drop(subvariable, axis=1, inplace=True)

        # delete variable from variable column
        for group in ics_stack.variable.unique():
            new_group = group.split(', ')
            if variable in new_group:
                new_group.remove(variable)
                ics_stack['variable'] = ', '.join(new_group)
    # delete empty column
    ics_stack.dropna(axis=1, how='all')
    return ics_stack


def select_variable(ics_stack, variable):
    for group in ics_stack.variable.unique():
        variable_group = group.split(', ')
        if variable in variable_group:
            # TODO: convert data to Profile rather than CoreStack, REQUIRE: Profile should inherit Profile
            # property (@property _constructor)
            ics_stack = ics_stack[ics_stack.variable == group]

            # delete other variable
            variables2del = [_var for _var in ics_stack.get_variable() if not _var == variable]
            ics_stack = delete_variables(ics_stack, variables2del)
    return ics_stack


def select_profile(ics_stack, variable_dict):
    """

    :param ics_stack:
    :param variable_dict:
    :return:
    """
    str_select = '('
    ii_var = []
    ii = 0
    for ii_key in variable_dict.keys():
        if ii_key is 'variable':
            if variable_dict[ii_key] in ics_stack.get_variable():
                ics_stack = select_variable(ics_stack, variable_dict[ii_key])
        elif ii_key in ics_stack.keys():
            ics_stack = ics_stack[ics_stack[ii_key] == variable_dict[ii_key]]
    return ics_stack


def delete_profile(ics_stack, variable_dict):
    """
    :param ics_stack:
    :param variable_dict:
    :return:
    """
    str_select = '('
    ii_var = []
    ii = 0
    for ii_key in variable_dict.keys():
        if ii_key in ics_stack.keys():
            ii_var.append(variable_dict[ii_key])
            str_select = str_select + 'ics_stack.' + ii_key + '!=ii_var[' + str('%d' % ii) + ']) | ('
            ii += 1
    str_select = str_select[:-4]
    return ics_stack.loc[eval(str_select)]


# s_nan is deprecated function
def s_nan(yx, ii_yx, fill_gap=True):
    """
    :param yx:
    :param ii_yx:
    :param fill_gap:
    :return:
    """
    if np.isnan(yx[ii_yx, 2]) and fill_gap:
        ii_yx_l = ii_yx - 1
        while ii_yx_l > 0 and np.isnan(yx[ii_yx_l, 2]):
            ii_yx_l -= 1
        if ii_yx_l > 0:
            s_l = yx[ii_yx_l, 2]
        else:
            s_l = np.nan

        ii_yx_s = ii_yx
        while ii_yx_s < yx.shape[0] - 1 and np.isnan(yx[ii_yx_s, 2]):
            ii_yx_s += 1
        s_s = yx[ii_yx_s, 2]

        s = (s_s + s_l) / 2
    else:
        s = yx[ii_yx, 2]
    return s


def is_continuous(profile):
    if ('y_low' in profile and profile.y_low.isnull().all() and not profile.y_low.empty):
        return 1
    elif 'y_low' not in profile:
        return 1

    else:
        return 0


def uniformize_section(profile, profile_target):
    """

    :param profile: seaice.core.profile
        Profile with section bin to be match to target profile
    :param profile_target: seaice.core.profile
        Profile with section bin to match
    :return: seaice.core.profile
        Profile with section bin matched to target profile
    """

    if not is_continuous(profile_target):
        if not profile_target.y_mid.isna().all():
            y_mid = profile_target.y_mid.dropna().values
        else:
            y_mid = (profile_target.y_low +profile_target.y_sup/2).dropna().values

    else:
        y_mid = profile_target.y_mid.dropna().values

    if is_continuous(profile):
        profile = profile.sort_values(by='y_mid').reindex()
    else:
        profile = profile.sort_values(by='y_low')
        if profile.y_mid.isna().any():
            profile['y_mid'] = (profile.y_low +profile.y_sup/2).dropna().values


    # replace the 2 following lines
    variable = profile.variable.unique()[0]
    interp_data = np.interp(y_mid, profile['y_mid'].values, profile[variable].values, left=np.nan, right=np.nan)
    profile_new = pd.DataFrame(np.transpose([interp_data, y_mid, [variable]*y_mid.__len__()]), columns=[variable, 'y_mid', 'variable'])

    # copy attribute from profile to new_profile:
    not_target_attribute = list(profile.variable.unique()) + ['y_mid']
    attribute = [atr for atr in profile.keys() if atr not in not_target_attribute]
    _attribute = profile_target[attribute].head(1)
    profile_new[attribute] = _attribute
    profile_new[variable] = profile_new[variable].astype(float)
    return profile_new