def get_common_dates_safe(df1, df2):
    """用日期字串比對，確保萬無一失"""
    # 建立副本
    d1 = df1[['日期', '收市']].copy()
    d2 = df2[['日期', '收市']].copy()
    
    # 統一轉成 YYYY-MM-DD 字串
    d1['key'] = d1['日期'].apply(lambda x: f"{x.year}-{x.month:02d}-{x.day:02d}")
    d2['key'] = d2['日期'].apply(lambda x: f"{x.year}-{x.month:02d}-{x.day:02d}")
    
    # 用字串取交集
    common_keys = set(d1['key']) & set(d2['key'])
    
    # 建立結果 Series
    s1_dict = d1.set_index('key')['收市'].to_dict()
    s2_dict = d2.set_index('key')['收市'].to_dict()
    
    s1 = pd.Series({k: s1_dict[k] for k in common_keys})
    s2 = pd.Series({k: s2_dict[k] for k in common_keys})
    
    return s1, s2
