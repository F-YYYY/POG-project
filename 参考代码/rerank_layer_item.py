# 原始层的block的排序
def rerank_block(layer_sku,result,item_detail,pog_config_org):
    layer_sku_tmp = layer_sku.copy()
    layer_sku_tmp['brand'] = layer_sku_tmp['item_code'].apply(lambda x: item_detail[x]['brand'])
    layer_sku_tmp['series'] = layer_sku_tmp['item_code'].apply(lambda x: item_detail[x]['series'])
    layer_sku_tmp['segment'] = layer_sku_tmp['item_code'].apply(lambda x: item_detail[x]['segment'])
    brand_rk = list(layer_sku_tmp[['brand','position']].groupby('brand').position.min().sort_values().index)
    #原始系列的排序
    tmp = list(layer_sku_tmp[['brand','series','position']].groupby(['brand','series']).position.min().sort_values().index)
    series_rk = {}
    for i in tmp:
        series_rk.setdefault(i[0],[])
        series_rk[i[0]].append(i[1])
    tmp = list(layer_sku_tmp[['brand','series','segment','position']].groupby(['brand','series','segment']).position.min().sort_values().index)
    segment_rk = {}
    for i in tmp:
        segment_rk.setdefault((i[0],i[1]),[])
        segment_rk[(i[0],i[1])].append(i[2])
    # 添加补位的品，重排品牌和系列的排序
    for item_code in result:
        item_brand = item_detail[item_code]['brand']
        item_series = item_detail[item_code]['series']
        item_segment = item_detail[item_code]['segment']
        segment_rank_config = pog_config_org['segment']['assign_brand_rank']
        if item_series not in series_rk[item_brand]:
            series_rk[item_brand].append(item_series)
            segment_rk[(item_brand,item_series)] = [item_segment]
        series_segment_rk = segment_rk[(item_brand,item_series)]
        if item_segment in series_segment_rk:
            continue
        # 对segment进行重排
        series_segment_rk.append(item_segment)
        series_segment_rk = [i for i in segment_rank_config if i in series_segment_rk]
        segment_rk[(item_brand,item_series)] = series_segment_rk
    return brand_rk,series_rk,segment_rk

# 根据重排的本层block，得到商品摆放顺序
def get_item_rk(layer_sku,result,brand_rk,series_rk,segment_rk,item_detail):
    layer_sku_tmp = layer_sku.copy()
    layer_sku_tmp['brand'] = layer_sku_tmp['item_code'].apply(lambda x: item_detail[x]['brand'])
    layer_sku_tmp['series'] = layer_sku_tmp['item_code'].apply(lambda x: item_detail[x]['series'])
    layer_sku_tmp['segment'] = layer_sku_tmp['item_code'].apply(lambda x: item_detail[x]['segment'])
    sku_in_layer = pd.DataFrame(list(layer_sku_tmp['item_code']) + result,columns=['item_code'])
    sku_in_layer['brand'] = sku_in_layer['item_code'].apply(lambda x: item_detail[x]['brand'])
    sku_in_layer['series'] = sku_in_layer['item_code'].apply(lambda x: item_detail[x]['series'])
    sku_in_layer['segment'] = sku_in_layer['item_code'].apply(lambda x: item_detail[x]['segment'])
    sku_in_layer['height'] = sku_in_layer['item_code'].apply(lambda x: item_detail[x]['height'])
    # 确定层中从左到右的商品顺序
    item_rk = []
    for brand in brand_rk:
        for series in series_rk[brand]:
            for segment in segment_rk[(brand,series)]:
                # print(brand,series,segment)
                filter = sku_in_layer['brand'] == brand
                filter &= sku_in_layer['series'] == series
                filter &= sku_in_layer['segment'] == segment
                items = list(sku_in_layer[filter].sort_values(by='height')['item_code'])
                item_rk += items
    return item_rk
# 重排本层的block
# layer_sku 为本层的原始商品（从pog_data中筛选module_id和层id而来）
# result 为要增加的商品list
# item_detail 为商品属性的dict，key为item_code，值为商品各种属性的dict
# pog_config_org POG的生图参数

brand_rk,series_rk,segment_rk = rerank_block(layer_sku,result,item_detail,pog_config_org)
# 根据重排的本层block，得到顺排摆放顺序
item_rk = get_item_rk(layer_sku,result,brand_rk,series_rk,segment_rk,item_detail)