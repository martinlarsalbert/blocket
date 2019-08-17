import numpy as np
import logging

def decode_miltal(s_miltal):
    if not isinstance(s_miltal,str):
        return np.nan

    parts = s_miltal.split('-')

    if len(parts) == 1:
        try:
            value = float(parts[0])
        except ValueError:
            value = np.nan

        return value

    elif len(parts) == 2:
        return np.mean([float(parts[0]), float(parts[1])])
    else:
        raise ValueError()

def clean(df_cars):

    try:
        index = df_cars['Tillverkningsår'] == '-'
        df_cars.loc[index, 'Tillverkningsår'] = df_cars.loc[index, 'Modellår']
    except:
        pass


    df_cars['Miltal'] = df_cars['Miltal'].apply(func=decode_miltal)
    index = df_cars['Miltal'].isnull()
    if index.sum() > 0:
       logging.warning('Missing "Miltal" removing cars: %s' % df_cars.loc[index]['header'])
       df_cars = df_cars.loc[~index]
    float_cols = ['Miltal', 'Modellår', 'Tillverkningsår']
    df_cars[float_cols] = df_cars[float_cols].astype(float)

    return df_cars