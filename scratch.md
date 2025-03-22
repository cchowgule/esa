<!--LTeX: enabled=false-->

66/4: lc = pd.read_feather('feathers/landcover_types.feather')
66/5: lc
66/6: lc.dtypes
66/7: lc = lc.reset_index()
66/8: lc
66/9: df
66/10: lc
66/11: df.dtypes
66/12: df = df.drop(columns=['area', 'area_lc'])
66/13: df
66/14: df.dtypes
66/15: lst = df.index.names
66/16: lst
66/17: lst = list(lst)
66/18: lst
66/19: lst = lst + ['name']
66/20: lst
66/21: df = df.reset_index()
66/22: df.set_index(lst)
66/23: df = df.set_index(lst)
66/24: df
66/25: df.dtypes
66/26: lc
66/27: list(lc.itertuples(index=False))
66/28: list(lc.itertuples(index=False, name=None))
66/29: lc.dtypes
66/30: lst = list(lc[['basic_id', 'level_1_id', 'fine_id']].itertuples(index=False, name=None))
66/31: lst
66/32: df1 = df.copy()
66/33: df.columns = pd.MultiIndex.from_tuples(lst)
66/34: lst
66/35: df.columns
66/36: lst1 = list(df.columns)
66/37: lst1
66/38: len(lst1)
66/39: len(lst)
66/40: df = df.dropna(axis=1, how='all')
66/41: df.shape
66/42: df1.shape
66/43: df
66/44: df.dropna(axis=1, how='all')
66/45: lst2 = [x if x in lst1 for x in lst]
66/46: lst2 = [x for x in lst of x[2] in lst1]
66/47: lst2 = [x for x in lst if x[2] in lst1]
66/48: lst2
66/49: lst2 = [x[2] for x in lst]
66/50: lst2
66/51: lst1
66/52: cols = [int(x) for x in lst1]
66/53: cols
66/54: lst
66/55: lc_types = lst1
66/56: cols
66/57: lc_types = lc_types + [('XXX', 'XXX', 0)]
66/58: lc_types
66/59: lc_types = lst
66/60: lc_types
66/61: lc_types = lc_types + [('XXX', 'XXX', 0)]
66/62: lc_types
66/63: cols1 = [x for x in lc_types if x[2] in cols]
66/64: cols1
66/65: df.columns = pd.MultiIndex.from_tuples(cols1)
66/66: df
66/67: df.dtypes
66/68: df.index.dtypes
66/69: df.columns
66/70: df.to_feather('feathers/final_data.feather')

df['area_lc'] = df.sum(axis=1, numeric_only=True)
64/133: df['area_lc']
64/134: df['area'] = gdf['area']
